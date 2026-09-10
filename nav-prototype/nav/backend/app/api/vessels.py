from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Company, HistoricalVoyage, Vessel, VesselPosition, Voyage
from ..schemas import (
    CompanyOut,
    HistoricalVoyageOut,
    PositionOut,
    VesselCreate,
    VesselDetail,
    VesselOut,
)
from .serializers import voyage_out

router = APIRouter(tags=["vessels"])


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).order_by(Company.name).all()


@router.get("/vessels", response_model=list[VesselOut])
def list_vessels(
    db: Session = Depends(get_db),
    search: str | None = Query(default=None),
    company_id: int | None = None,
    status: str | None = None,
):
    query = db.query(Vessel)
    if search:
        like = f"%{search}%"
        query = query.filter(Vessel.name.ilike(like) | Vessel.imo.ilike(like))
    if company_id:
        query = query.filter(Vessel.company_id == company_id)
    if status:
        query = query.filter(Vessel.status == status.upper())
    return query.order_by(Vessel.name).all()


@router.get("/vessels/{vessel_id}", response_model=VesselDetail)
def get_vessel(vessel_id: int, db: Session = Depends(get_db)):
    vessel = db.get(Vessel, vessel_id)
    if not vessel:
        raise HTTPException(status_code=404, detail=f"Vessel {vessel_id} not found")

    detail = VesselDetail.model_validate(vessel)
    voyages = (
        db.query(Voyage)
        .filter(Voyage.vessel_id == vessel_id)
        .order_by(desc(Voyage.departure_utc))
        .limit(8)
        .all()
    )
    detail.recent_voyages = [voyage_out(v) for v in voyages]
    current = next((v for v in voyages if v.status == "ACTIVE"), None)
    detail.current_voyage = voyage_out(current) if current else None
    detail.historical = [
        HistoricalVoyageOut.model_validate(h)
        for h in db.query(HistoricalVoyage)
        .filter(HistoricalVoyage.vessel_id == vessel_id)
        .order_by(desc(HistoricalVoyage.departure_utc))
        .limit(10)
        .all()
    ]
    return detail


@router.post("/vessels", response_model=VesselOut, status_code=201)
def create_vessel(payload: VesselCreate, db: Session = Depends(get_db)):
    if not db.get(Company, payload.company_id):
        raise HTTPException(status_code=400, detail=f"Company {payload.company_id} does not exist")
    if db.query(Vessel).filter(Vessel.imo == payload.imo).first():
        raise HTTPException(status_code=409, detail=f"IMO {payload.imo} already exists")
    vessel = Vessel(**payload.model_dump(), data_source="USER")
    db.add(vessel)
    db.commit()
    db.refresh(vessel)
    return vessel


@router.get("/vessels/{vessel_id}/positions", response_model=list[PositionOut])
def vessel_positions(vessel_id: int, limit: int = 50, db: Session = Depends(get_db)):
    if not db.get(Vessel, vessel_id):
        raise HTTPException(status_code=404, detail=f"Vessel {vessel_id} not found")
    return (
        db.query(VesselPosition)
        .filter(VesselPosition.vessel_id == vessel_id)
        .order_by(desc(VesselPosition.recorded_at))
        .limit(limit)
        .all()
    )
