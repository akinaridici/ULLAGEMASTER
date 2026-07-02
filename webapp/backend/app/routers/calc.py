from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.engine import calculate_voyage
from ..database import get_db
from ..models import User
from ..schemas import CalcRequest, CalcResponse
from ..security import get_current_user
from .ships import get_owned_ship

router = APIRouter(prefix="/api/ships/{ship_id}", tags=["calculation"])


@router.post("/calculate", response_model=CalcResponse)
def calculate(
    ship_id: int,
    payload: CalcRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stateless calculation: current inputs in, all derived figures out."""
    ship = get_owned_ship(ship_id, db, user)
    tanks = [t.as_calc_dict() for t in ship.tanks]
    voyage_data = {
        "vef": payload.vef,
        "draft_aft": payload.draft_aft,
        "draft_fwd": payload.draft_fwd,
        "parcels": [p.model_dump() for p in payload.parcels],
        "readings": {k: r.model_dump() for k, r in payload.readings.items()},
    }
    return calculate_voyage(tanks, voyage_data)
