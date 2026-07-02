from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..core.engine import calculate_voyage
from ..database import get_db
from ..models import User
from ..security import get_current_user
from ..services.exporter import export_pdf, export_xlsx
from ..services.protest_pdf import export_protest_pdf
from ..services.stowage_pdf import export_stowage_pdf
from .voyages import get_owned_voyage

router = APIRouter(prefix="/api/ships/{ship_id}/voyages/{voyage_id}/export", tags=["export"])

MEDIA_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "stowage": "application/pdf",
}


@router.get("/protest")
def export_protest(
    ship_id: int,
    voyage_id: int,
    operation: str = "loading",
    parcel_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Letter of Protest PDF — one parcel, or every non-SLOP parcel (one page each)."""
    if operation not in ("loading", "discharging"):
        raise HTTPException(status_code=400, detail="operation must be loading or discharging")
    voyage = get_owned_voyage(ship_id, voyage_id, db, user)
    ship = voyage.ship

    calc = calculate_voyage(
        [t.as_calc_dict() for t in ship.tanks],
        {"vef": voyage.vef, "draft_aft": voyage.draft_aft, "draft_fwd": voyage.draft_fwd,
         "parcels": voyage.parcels, "readings": voyage.readings},
    )
    summaries = {s["parcel_id"]: s for s in calc["parcels"]}
    vef = voyage.vef or 1.0

    parcels_data = []
    for p in voyage.parcels:
        pid = str(p.get("id"))
        if pid == "0":
            continue  # SLOP never gets a protest letter
        if parcel_id is not None and pid != parcel_id:
            continue
        s = summaries.get(pid)
        if not s:
            continue
        bl = float(p.get("bl_loading") or 0.0)
        if operation == "loading":
            parcels_data.append({
                "name": p.get("name") or "", "receiver": p.get("receiver") or "",
                "bl_figure": bl,
                "ship_wo_vef": s["mt_air"],
                "diff_wo_vef": s["diff_wo_vef"],
                "diff_pct_wo_vef": s["diff_permille_wo_vef"],
                "ship_with_vef": s["ship_with_vef"],
                "diff_with_vef": s["diff_with_vef"],
                "diff_pct_with_vef": s["diff_permille_with_vef"],
            })
        else:
            arrival = s["mt_air"]
            arrival_vef = arrival / vef if vef else arrival
            outturn = float(p.get("outturn_figure") or 0.0)
            parcels_data.append({
                "name": p.get("name") or "", "receiver": p.get("receiver") or "",
                "bl_figure": bl,
                "ship_arrival": arrival,
                "arrival_bl_wo_pct": ((arrival - bl) / bl) * 1000 if bl else 0.0,
                "ship_arrival_vef": arrival_vef,
                "arrival_bl_vef_pct": ((arrival_vef - bl) / bl) * 1000 if bl else 0.0,
                "outturn": outturn,
                "outturn_bl_diff": outturn - bl,
                "outturn_bl_pct": ((outturn - bl) / bl) * 1000 if bl else 0.0,
            })

    if not parcels_data:
        raise HTTPException(status_code=404, detail="No matching parcel for protest")

    content = export_protest_pdf(
        ship.name, parcels_data, operation,
        {"date": voyage.date, "port": voyage.port, "terminal": voyage.terminal},
        logo=ship.logo_png,
    )
    safe_no = "".join(c if c.isalnum() or c in "-_" else "_" for c in voyage.voyage_number) or "voyage"
    suffix = parcel_id or "all"
    filename = f"protest_{operation}_{safe_no}_{suffix}.pdf"
    return Response(
        content=content, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{fmt}")
def export_voyage(
    ship_id: int,
    voyage_id: int,
    fmt: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if fmt not in MEDIA_TYPES:
        raise HTTPException(status_code=400, detail="Format must be xlsx, pdf or stowage")
    voyage = get_owned_voyage(ship_id, voyage_id, db, user)
    ship = voyage.ship

    voyage_data = {
        "voyage_number": voyage.voyage_number,
        "date": voyage.date,
        "port": voyage.port,
        "terminal": voyage.terminal,
        "vef": voyage.vef,
        "draft_aft": voyage.draft_aft,
        "draft_fwd": voyage.draft_fwd,
        "chief_officer": voyage.chief_officer,
        "master": voyage.master,
        "parcels": voyage.parcels,
        "readings": voyage.readings,
    }
    calc = calculate_voyage([t.as_calc_dict() for t in ship.tanks], voyage_data)

    if fmt == "xlsx":
        content = export_xlsx(ship.name, voyage_data, calc)
    elif fmt == "stowage":
        content = export_stowage_pdf(ship.name, voyage_data, calc)
    else:
        content = export_pdf(ship.name, voyage_data, calc)

    safe_no = "".join(c if c.isalnum() or c in "-_" else "_" for c in voyage.voyage_number) or "voyage"
    prefix = "stowage_plan" if fmt == "stowage" else "ullage_report"
    filename = f"{prefix}_{safe_no}.{'pdf' if fmt == 'stowage' else fmt}"
    return Response(
        content=content,
        media_type=MEDIA_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
