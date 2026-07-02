import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Ship, Tank, User
from ..schemas import ShipIn, ShipListItem, ShipOut, TankIn, TankOut
from ..security import get_current_user

router = APIRouter(prefix="/api/ships", tags=["ships"])


def get_owned_ship(ship_id: int, db: Session, user: User) -> Ship:
    ship = db.get(Ship, ship_id)
    if not ship or ship.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Ship not found")
    return ship


def _tank_out(tank: Tank) -> TankOut:
    return TankOut(
        tank_code=tank.tank_code,
        name=tank.name,
        capacity_m3=tank.capacity_m3,
        has_ullage_table=tank.ullage_table_json not in ("", "[]"),
        has_trim_table=tank.trim_table_json not in ("", "[]"),
        has_thermal_table=tank.thermal_table_json not in ("", "[]"),
    )


def _ship_out(ship: Ship) -> ShipOut:
    return ShipOut(
        id=ship.id,
        name=ship.name,
        default_vef=ship.default_vef,
        slop_density=ship.slop_density,
        chief_officer=ship.chief_officer,
        master=ship.master,
        trim_values=ship.trim_values,
        tanks=[_tank_out(t) for t in ship.tanks],
        has_logo=ship.logo_png is not None,
    )


def _apply_tanks(ship: Ship, tanks: list[TankIn]):
    ship.tanks.clear()
    for i, t in enumerate(tanks):
        ship.tanks.append(
            Tank(
                tank_code=t.tank_code,
                name=t.name,
                capacity_m3=t.capacity_m3,
                position=i,
                ullage_table_json=json.dumps(t.ullage_table),
                trim_table_json=json.dumps(t.trim_table),
                thermal_table_json=json.dumps(t.thermal_table),
            )
        )


@router.get("", response_model=list[ShipListItem])
def list_ships(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [
        ShipListItem(id=s.id, name=s.name, tank_count=len(s.tanks), voyage_count=len(s.voyages))
        for s in user.ships
    ]


@router.post("", response_model=ShipOut)
def create_ship(payload: ShipIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ship = Ship(
        owner_id=user.id,
        name=payload.name,
        default_vef=payload.default_vef,
        slop_density=payload.slop_density,
        chief_officer=payload.chief_officer,
        master=payload.master,
        trim_values_json=json.dumps(payload.trim_values),
    )
    _apply_tanks(ship, payload.tanks)
    db.add(ship)
    db.commit()
    db.refresh(ship)
    return _ship_out(ship)


@router.post("/import-config", response_model=ShipOut)
async def import_desktop_config(
    file: UploadFile, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Import a ship_config.json exported by the desktop UllageMaster app."""
    try:
        config = json.loads((await file.read()).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="File is not valid JSON")
    if "ship_name" not in config or "tanks" not in config:
        raise HTTPException(status_code=400, detail="Not a UllageMaster ship config (missing ship_name/tanks)")

    ship = Ship(
        owner_id=user.id,
        name=config.get("ship_name", "Unnamed ship"),
        default_vef=float(config.get("default_vef", 1.0)),
        slop_density=float(config.get("slop_density", 0.9)),
        chief_officer=config.get("chief_officer", ""),
        master=config.get("master", ""),
        trim_values_json=json.dumps(config.get("trim_values", [])),
    )
    for i, t in enumerate(config["tanks"]):
        ship.tanks.append(
            Tank(
                tank_code=t.get("id", f"T{i+1}"),
                name=t.get("name", ""),
                capacity_m3=float(t.get("capacity_m3", 0.0)),
                position=i,
                ullage_table_json=json.dumps(t.get("ullage_table", [])),
                trim_table_json=json.dumps(t.get("trim_table", [])),
                thermal_table_json=json.dumps(t.get("thermal_table", [])),
            )
        )
    db.add(ship)
    db.commit()
    db.refresh(ship)
    return _ship_out(ship)


@router.get("/{ship_id}", response_model=ShipOut)
def get_ship(ship_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _ship_out(get_owned_ship(ship_id, db, user))


@router.put("/{ship_id}", response_model=ShipOut)
def update_ship(
    ship_id: int, payload: ShipIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    ship = get_owned_ship(ship_id, db, user)
    ship.name = payload.name
    ship.default_vef = payload.default_vef
    ship.slop_density = payload.slop_density
    ship.chief_officer = payload.chief_officer
    ship.master = payload.master
    ship.trim_values_json = json.dumps(payload.trim_values)
    if payload.tanks:
        _apply_tanks(ship, payload.tanks)
    db.commit()
    db.refresh(ship)
    return _ship_out(ship)


@router.delete("/{ship_id}")
def delete_ship(ship_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ship = get_owned_ship(ship_id, db, user)
    db.delete(ship)
    db.commit()
    return {"ok": True}


@router.post("/{ship_id}/logo")
async def upload_logo(
    ship_id: int, file: UploadFile, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Upload the company logo (PNG/JPEG) used on official PDF reports."""
    ship = get_owned_ship(ship_id, db, user)
    data = await file.read()
    if len(data) > 2_000_000:
        raise HTTPException(status_code=400, detail="Logo must be under 2 MB")
    if not (data[:8] == b"\x89PNG\r\n\x1a\n" or data[:2] == b"\xff\xd8"):
        raise HTTPException(status_code=400, detail="Logo must be a PNG or JPEG image")
    ship.logo_png = data
    db.commit()
    return {"ok": True, "size": len(data)}


@router.get("/{ship_id}/logo")
def get_logo(ship_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from fastapi.responses import Response

    ship = get_owned_ship(ship_id, db, user)
    if not ship.logo_png:
        raise HTTPException(status_code=404, detail="No logo uploaded")
    media = "image/png" if ship.logo_png[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    return Response(content=ship.logo_png, media_type=media)


@router.delete("/{ship_id}/logo")
def delete_logo(ship_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ship = get_owned_ship(ship_id, db, user)
    ship.logo_png = None
    db.commit()
    return {"ok": True}


TABLE_COLUMNS = {
    "ullage": ["ullage_mm", "volume_m3"],
    "trim": ["ullage_mm", "trim_m", "correction_m3"],
    "thermal": ["temp_c", "corr_factor"],
}


@router.post("/{ship_id}/tanks/{tank_code}/tables/{table_type}", response_model=TankOut)
async def upload_tank_table(
    ship_id: int,
    tank_code: str,
    table_type: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a CSV table for one tank. table_type: ullage | trim | thermal."""
    if table_type not in TABLE_COLUMNS:
        raise HTTPException(status_code=400, detail="table_type must be ullage, trim or thermal")
    ship = get_owned_ship(ship_id, db, user)
    tank = next((t for t in ship.tanks if t.tank_code == tank_code), None)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")

    try:
        text = (await file.read()).decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 CSV")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Empty CSV")

    expected = TABLE_COLUMNS[table_type]
    fieldnames = [f.strip() for f in reader.fieldnames]
    # Accept ullage_cm as an alternative to ullage_mm
    alias = {"ullage_cm": "ullage_mm"}
    rows = []
    try:
        for raw in reader:
            row = {}
            for col in fieldnames:
                key = col.strip()
                value = float(str(raw[col]).strip().replace(",", "."))
                if key == "ullage_cm":
                    key, value = "ullage_mm", value * 10.0
                row[key] = value
            missing = [c for c in expected if c not in row]
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"CSV must have columns {expected} (or ullage_cm); missing {missing}",
                )
            rows.append({c: row[c] for c in expected})
    except (ValueError, KeyError):
        raise HTTPException(status_code=400, detail="CSV contains non-numeric values")
    if not rows:
        raise HTTPException(status_code=400, detail="CSV has no data rows")

    setattr(tank, f"{table_type}_table_json", json.dumps(rows))
    db.commit()
    db.refresh(tank)
    return _tank_out(tank)
