"""Small helpers shared by the routers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import OptimizationRun, Recommendation, Voyage
from ..schemas import (
    OptimizationOptionOut,
    OptimizationRunOut,
    RecommendationOut,
    VoyageOut,
)
from ..services.optimizer import activity_steps


def voyage_out(voyage: Voyage) -> VoyageOut:
    payload = VoyageOut.model_validate(voyage)
    if voyage.vessel:
        payload.vessel_name = voyage.vessel.name
        payload.vessel_imo = voyage.vessel.imo
    return payload


def option_out(option, recommended_id: int | None) -> OptimizationOptionOut:
    out = OptimizationOptionOut.model_validate(option)
    out.recommended = option.id == recommended_id
    return out


def recommendation_out(db: Session, rec: Recommendation | None) -> RecommendationOut | None:
    if rec is None:
        return None
    out = RecommendationOut.model_validate(rec)
    option = next((o for o in rec.run.options if o.id == rec.option_id), None)
    if option:
        out.option = option_out(option, rec.option_id)
        out.route_label = option.label
    voyage = db.get(Voyage, rec.voyage_id)
    if voyage:
        out.voyage_reference = voyage.reference
        out.vessel_name = voyage.vessel.name if voyage.vessel else None
    return out


def run_out(db: Session, run: OptimizationRun) -> OptimizationRunOut:
    out = OptimizationRunOut.model_validate(run)
    out.options = [option_out(o, run.recommended_option_id) for o in run.options]
    out.options.sort(key=lambda o: (not o.recommended, o.score if o.score is not None else 99))
    out.recommendation = recommendation_out(db, run.recommendation)
    out.activity = activity_steps(run)
    return out
