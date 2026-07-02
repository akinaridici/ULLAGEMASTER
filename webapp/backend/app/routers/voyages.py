import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Voyage
from ..schemas import VoyageIn, VoyageListItem, VoyageOut
from ..security import get_current_user
from .ships import get_owned_ship

router = APIRouter(prefix="/api/ships/{ship_id}/voyages", tags=["voyages"])


def _voyage_out(v: Voyage) -> VoyageOut:
    return VoyageOut(
        id=v.id,
        ship_id=v.ship_id,
        voyage_number=v.voyage_number,
        date=v.date,
        port=v.port,
        terminal=v.terminal,
        vef=v.vef,
        draft_aft=v.draft_aft,
        draft_fwd=v.draft_fwd,
        chief_officer=v.chief_officer,
        master=v.master,
        notes=v.notes,
        parcels=v.parcels,
        readings=v.readings,
        stowage_plan=v.stowage_plan or {},
        created_at=v.created_at.isoformat() if v.created_at else None,
        updated_at=v.updated_at.isoformat() if v.updated_at else None,
    )


def get_owned_voyage(ship_id: int, voyage_id: int, db: Session, user: User) -> Voyage:
    ship = get_owned_ship(ship_id, db, user)
    voyage = db.get(Voyage, voyage_id)
    if not voyage or voyage.ship_id != ship.id:
        raise HTTPException(status_code=404, detail="Voyage not found")
    return voyage


def _apply(v: Voyage, payload: VoyageIn):
    v.voyage_number = payload.voyage_number
    v.date = payload.date
    v.port = payload.port
    v.terminal = payload.terminal
    v.vef = payload.vef
    v.draft_aft = payload.draft_aft
    v.draft_fwd = payload.draft_fwd
    v.chief_officer = payload.chief_officer
    v.master = payload.master
    v.notes = payload.notes[:1000]
    v.parcels_json = json.dumps([p.model_dump() for p in payload.parcels])
    v.readings_json = json.dumps({k: r.model_dump() for k, r in payload.readings.items()})
    v.stowage_plan_json = json.dumps(payload.stowage_plan.model_dump())


@router.get("", response_model=list[VoyageListItem])
def list_voyages(ship_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ship = get_owned_ship(ship_id, db, user)
    voyages = sorted(ship.voyages, key=lambda v: v.updated_at or v.created_at, reverse=True)
    return [
        VoyageListItem(
            id=v.id,
            voyage_number=v.voyage_number,
            date=v.date,
            port=v.port,
            terminal=v.terminal,
            updated_at=v.updated_at.isoformat() if v.updated_at else None,
        )
        for v in voyages
    ]


@router.post("", response_model=VoyageOut)
def create_voyage(
    ship_id: int, payload: VoyageIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    ship = get_owned_ship(ship_id, db, user)
    voyage = Voyage(ship_id=ship.id)
    _apply(voyage, payload)
    db.add(voyage)
    db.commit()
    db.refresh(voyage)
    return _voyage_out(voyage)


@router.get("/{voyage_id}", response_model=VoyageOut)
def get_voyage(
    ship_id: int, voyage_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _voyage_out(get_owned_voyage(ship_id, voyage_id, db, user))


@router.put("/{voyage_id}", response_model=VoyageOut)
def update_voyage(
    ship_id: int,
    voyage_id: int,
    payload: VoyageIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    voyage = get_owned_voyage(ship_id, voyage_id, db, user)
    _apply(voyage, payload)
    db.commit()
    db.refresh(voyage)
    return _voyage_out(voyage)


@router.delete("/{voyage_id}")
def delete_voyage(
    ship_id: int, voyage_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    voyage = get_owned_voyage(ship_id, voyage_id, db, user)
    db.delete(voyage)
    db.commit()
    return {"ok": True}
