from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..clock import utc_now
from ..database import get_db
from ..models import HistoricalVoyage, Recommendation, Vessel, Voyage
from ..schemas import FleetAnalytics, VoyageAlert
from ..services import weather as weather_service
from ..services.emissions import calculate_emissions
from ..services.eta import calculate_eta

router = APIRouter(tags=["analytics"])

# A voyage is flagged when the projected arrival slips more than this.
ETA_SLIP_HOURS = 12.0
# ...or when consumption runs this far ahead of the pro-rata plan.
FUEL_OVERRUN_PCT = 8.0


def _alerts(db: Session) -> list[VoyageAlert]:
    alerts: list[VoyageAlert] = []
    now = utc_now().replace(microsecond=0)
    active = db.query(Voyage).filter(Voyage.status == "ACTIVE").all()

    pending_by_voyage = {
        r.voyage_id: r
        for r in db.query(Recommendation).filter(Recommendation.status == "PENDING").all()
    }

    for voyage in active:
        vessel_name = voyage.vessel.name if voyage.vessel else "Unknown"
        if voyage.current_speed_kn <= 0.5:
            alerts.append(
                VoyageAlert(
                    voyage_id=voyage.id,
                    reference=voyage.reference,
                    vessel_name=vessel_name,
                    severity="ACTION",
                    message="Reported speed is zero — position feed may be stale.",
                )
            )
            continue

        projected = calculate_eta(
            voyage.distance_remaining_nm, voyage.current_speed_kn, now
        ).eta_utc
        slip = (projected - voyage.expected_arrival_utc).total_seconds() / 3600.0
        if slip > ETA_SLIP_HOURS:
            alerts.append(
                VoyageAlert(
                    voyage_id=voyage.id,
                    reference=voyage.reference,
                    vessel_name=vessel_name,
                    severity="ACTION",
                    message=f"Projected arrival is {slip:.0f} h behind schedule at {voyage.current_speed_kn:.1f} kn.",
                )
            )

        sailed = max(0.0, voyage.distance_nm - voyage.distance_remaining_nm)
        if sailed > 100 and voyage.planned_fuel_mt > 0:
            expected = voyage.planned_fuel_mt * (sailed / voyage.distance_nm)
            if expected > 0:
                overrun = (voyage.consumed_fuel_mt - expected) / expected * 100
                if overrun > FUEL_OVERRUN_PCT:
                    alerts.append(
                        VoyageAlert(
                            voyage_id=voyage.id,
                            reference=voyage.reference,
                            vessel_name=vessel_name,
                            severity="WATCH",
                            message=f"Consumption is {overrun:.0f}% above the pro-rata plan.",
                        )
                    )

        rec = pending_by_voyage.get(voyage.id)
        if rec and rec.fuel_saving_mt > 0:
            alerts.append(
                VoyageAlert(
                    voyage_id=voyage.id,
                    reference=voyage.reference,
                    vessel_name=vessel_name,
                    severity="INFO",
                    message=f"Optimization available: {rec.fuel_saving_mt:.0f} MT of fuel.",
                )
            )
    return alerts


@router.get("/analytics/alerts", response_model=list[VoyageAlert])
def alerts(db: Session = Depends(get_db)):
    order = {"ACTION": 0, "WATCH": 1, "INFO": 2}
    return sorted(_alerts(db), key=lambda a: order[a.severity])


@router.get("/analytics/fleet", response_model=FleetAnalytics)
def fleet(db: Session = Depends(get_db)):
    voyages = db.query(Voyage).all()
    active = [v for v in voyages if v.status == "ACTIVE"]
    planned = [v for v in voyages if v.status == "PLANNED"]
    completed = [v for v in voyages if v.status == "COMPLETED"]

    pending = db.query(Recommendation).filter(Recommendation.status == "PENDING").all()
    approved = (
        db.query(Recommendation).filter(Recommendation.status.in_(["APPROVED", "MODIFIED"])).all()
    )
    alert_rows = _alerts(db)
    attention = {a.voyage_id for a in alert_rows if a.severity in ("ACTION", "WATCH")}

    fleet_fuel = sum(v.planned_fuel_mt for v in active)
    fuel_by_vessel = []
    fleet_co2 = 0.0
    for voyage in active:
        vessel = voyage.vessel
        co2 = calculate_emissions(voyage.planned_fuel_mt, vessel.fuel_type).co2_mt
        fleet_co2 += co2
        fuel_by_vessel.append(
            {
                "vessel": vessel.name,
                "voyage": voyage.reference,
                "planned_fuel_mt": round(voyage.planned_fuel_mt, 1),
                "consumed_fuel_mt": round(voyage.consumed_fuel_mt, 1),
                "co2_mt": round(co2, 1),
            }
        )
    fuel_by_vessel.sort(key=lambda r: r["planned_fuel_mt"], reverse=True)

    buckets: dict[str, dict] = defaultdict(
        lambda: {"predicted_fuel_mt": 0.0, "actual_fuel_mt": 0.0, "co2_mt": 0.0, "voyages": 0}
    )
    for row in db.query(HistoricalVoyage).all():
        key = row.departure_utc.strftime("%Y-%m")
        b = buckets[key]
        b["predicted_fuel_mt"] += row.predicted_fuel_mt
        b["actual_fuel_mt"] += row.actual_fuel_mt
        b["co2_mt"] += row.co2_mt
        b["voyages"] += 1
    monthly = [
        {
            "month": month,
            "predicted_fuel_mt": round(v["predicted_fuel_mt"], 1),
            "actual_fuel_mt": round(v["actual_fuel_mt"], 1),
            "co2_mt": round(v["co2_mt"], 1),
            "voyages": v["voyages"],
        }
        for month, v in sorted(buckets.items())
    ]

    return FleetAnalytics(
        active_vessels=db.query(Vessel).filter(Vessel.status != "IN_PORT").count(),
        active_voyages=len(active),
        planned_voyages=len(planned),
        completed_voyages=len(completed),
        attention_required=len(attention),
        optimization_opportunities=len({r.voyage_id for r in pending if r.fuel_saving_mt > 0}),
        pending_approvals=len(pending),
        potential_fuel_saving_mt=round(sum(r.fuel_saving_mt for r in pending), 1),
        potential_co2_saving_mt=round(sum(r.co2_saving_mt for r in pending), 1),
        approved_fuel_saving_mt=round(sum(r.fuel_saving_mt for r in approved), 1),
        fleet_fuel_mt=round(fleet_fuel, 1),
        fleet_co2_mt=round(fleet_co2, 1),
        weather_source=weather_service.get_provider().name,
        fuel_by_vessel=fuel_by_vessel[:10],
        monthly_performance=monthly,
    )
