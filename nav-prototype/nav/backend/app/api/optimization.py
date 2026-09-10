from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Approval, OptimizationOption, OptimizationRun, Recommendation, Voyage
from ..schemas import (
    ApprovalOut,
    ApprovalRequest,
    ModifyRequest,
    OptimizationRequest,
    OptimizationRunOut,
    RecommendationOut,
)
from ..services.optimizer import Constraints, run_optimization
from .serializers import recommendation_out, run_out

router = APIRouter(tags=["optimization"])


@router.post("/optimization", response_model=OptimizationRunOut)
def create_optimization(payload: OptimizationRequest, db: Session = Depends(get_db)):
    voyage = db.get(Voyage, payload.voyage_id)
    if not voyage:
        raise HTTPException(status_code=404, detail=f"Voyage {payload.voyage_id} not found")
    if voyage.status == "COMPLETED":
        raise HTTPException(
            status_code=400, detail="This voyage is completed and cannot be optimized"
        )

    c = payload.constraints
    if c.min_speed_kn and c.max_speed_kn and c.min_speed_kn > c.max_speed_kn:
        raise HTTPException(
            status_code=400, detail="Minimum speed cannot be greater than maximum speed"
        )

    constraints = Constraints(
        max_speed_kn=c.max_speed_kn,
        min_speed_kn=c.min_speed_kn,
        required_arrival_utc=c.required_arrival_utc or voyage.required_arrival_utc,
        max_weather_risk=c.max_weather_risk,
    )
    run = run_optimization(db, voyage, payload.objective, constraints)
    return run_out(db, run)


@router.get("/optimization", response_model=list[OptimizationRunOut])
def list_optimizations(voyage_id: int | None = None, limit: int = 20, db: Session = Depends(get_db)):
    query = db.query(OptimizationRun)
    if voyage_id:
        query = query.filter(OptimizationRun.voyage_id == voyage_id)
    runs = query.order_by(desc(OptimizationRun.id)).limit(limit).all()
    return [run_out(db, r) for r in runs]


@router.get("/optimization/{run_id}", response_model=OptimizationRunOut)
def get_optimization(run_id: int, db: Session = Depends(get_db)):
    run = db.get(OptimizationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Optimization run {run_id} not found")
    return run_out(db, run)


# --- recommendations -------------------------------------------------------


@router.get("/recommendations", response_model=list[RecommendationOut])
def list_recommendations(status: str | None = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(Recommendation)
    if status:
        query = query.filter(Recommendation.status == status.upper())
    rows = query.order_by(desc(Recommendation.id)).limit(limit).all()
    return [recommendation_out(db, r) for r in rows]


@router.get("/recommendations/{rec_id}", response_model=RecommendationOut)
def get_recommendation(rec_id: int, db: Session = Depends(get_db)):
    return recommendation_out(db, _get(db, rec_id))


@router.post("/recommendations/{rec_id}/approve", response_model=RecommendationOut)
def approve(rec_id: int, payload: ApprovalRequest, db: Session = Depends(get_db)):
    rec = _get(db, rec_id)
    _guard_decided(rec)
    _decide(db, rec, "APPROVED", payload.decided_by, payload.comment)
    _apply_to_voyage(db, rec, rec.option_id)
    db.commit()
    db.refresh(rec)
    return recommendation_out(db, rec)


@router.post("/recommendations/{rec_id}/reject", response_model=RecommendationOut)
def reject(rec_id: int, payload: ApprovalRequest, db: Session = Depends(get_db)):
    rec = _get(db, rec_id)
    _guard_decided(rec)
    _decide(db, rec, "REJECTED", payload.decided_by, payload.comment)
    db.commit()
    db.refresh(rec)
    return recommendation_out(db, rec)


@router.post("/recommendations/{rec_id}/modify", response_model=RecommendationOut)
def modify(rec_id: int, payload: ModifyRequest, db: Session = Depends(get_db)):
    rec = _get(db, rec_id)
    _guard_decided(rec)
    option = db.get(OptimizationOption, payload.option_id)
    if not option or option.run_id != rec.run_id:
        raise HTTPException(
            status_code=400, detail="That option does not belong to this optimization run"
        )
    if not option.feasible:
        raise HTTPException(
            status_code=400,
            detail=f"Option '{option.label}' is not feasible: {option.infeasible_reason}",
        )
    baseline = db.get(OptimizationOption, rec.run.baseline_option_id) if rec.run.baseline_option_id else None
    rec.option_id = option.id
    rec.headline = (
        f"{option.label} — {option.fuel_mt:.0f} MT, ETA {option.eta_utc:%d %b %H:%M} UTC"
    )
    if baseline:
        rec.fuel_saving_mt = round(max(0.0, baseline.fuel_mt - option.fuel_mt), 2)
        rec.co2_saving_mt = round(max(0.0, baseline.co2_mt - option.co2_mt), 2)
        rec.eta_delta_hours = round(option.duration_hours - baseline.duration_hours, 2)
    rec.rationale = (
        f"Operator override: {option.label} selected instead of the scored recommendation. "
        f"{option.fuel_mt:.0f} MT, ETA {option.eta_utc:%d %b %H:%M} UTC, "
        f"weather risk {option.weather_risk.replace('_', ' ').lower()}."
    )
    _decide(db, rec, "MODIFIED", payload.decided_by, payload.comment, option.id)
    _apply_to_voyage(db, rec, option.id)
    db.commit()
    db.refresh(rec)
    return recommendation_out(db, rec)


@router.get("/recommendations/{rec_id}/approvals", response_model=list[ApprovalOut])
def approval_log(rec_id: int, db: Session = Depends(get_db)):
    _get(db, rec_id)
    return (
        db.query(Approval)
        .filter(Approval.recommendation_id == rec_id)
        .order_by(desc(Approval.id))
        .all()
    )


# --- helpers ---------------------------------------------------------------


def _get(db: Session, rec_id: int) -> Recommendation:
    rec = db.get(Recommendation, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation {rec_id} not found")
    return rec


def _guard_decided(rec: Recommendation) -> None:
    if rec.status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail=f"Recommendation {rec.id} has already been {rec.status.lower()}",
        )


def _decide(
    db: Session,
    rec: Recommendation,
    decision: str,
    decided_by: str,
    comment: str | None,
    option_id: int | None = None,
) -> None:
    rec.status = decision
    db.add(
        Approval(
            recommendation_id=rec.id,
            decision=decision,
            decided_by=decided_by or "Operations",
            comment=comment,
            modified_option_id=option_id,
        )
    )


def _apply_to_voyage(db: Session, rec: Recommendation, option_id: int) -> None:
    """Update the voyage plan. N.A.V. never controls the vessel itself."""
    option = db.get(OptimizationOption, option_id)
    voyage = db.get(Voyage, rec.voyage_id)
    if not option or not voyage:
        return
    voyage.planned_speed_kn = option.average_speed_kn
    # The option covers the leg still to run, so the voyage plan becomes what
    # has already been burned plus the approved plan for the rest.
    voyage.planned_fuel_mt = round(voyage.consumed_fuel_mt + option.fuel_mt, 2)
    voyage.expected_arrival_utc = option.eta_utc
