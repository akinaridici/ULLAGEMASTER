"""
Calculation engine for the web app.

Replicates the desktop app's MainWindow._recalculate_tank flow exactly:
  1. Dual input: ullage (cm) or fill % -> ullage via reverse interpolation
  2. Trim correction table stores corrections in mm, applied to the ULLAGE
     (not the volume). Trim for table lookup = draft_fwd - draft_aft.
  3. TOV interpolated from the ullage table at the corrected ullage (cm).
  4. GOV = TOV * thermal factor (per-tank thermal table, default 1.0)
  5. VCF via ASTM 54B; GSV = round(GOV, 3) * round(VCF, 5)
  6. density_air = density_vac - 0.0011 (g/cm3) or - 1.1 (kg/m3)
  7. Totals exclude SLOP tanks (parcel_id == "0").
"""

from typing import Optional

import pandas as pd

from .interpolation import linear_interpolate, reverse_interpolate, bilinear_interpolate
from .astm_54b import calculate_vcf

THRESHOLD_LOW = 65.0
THRESHOLD_HIGH = 95.0
THRESHOLD_HIGH_HIGH = 98.0
SLOP_PARCEL_ID = "0"


def get_level_warning(fill_percent: Optional[float]) -> str:
    if fill_percent is None:
        return "normal"
    if fill_percent >= THRESHOLD_HIGH_HIGH:
        return "high_high"
    if fill_percent > THRESHOLD_HIGH:
        return "high"
    if fill_percent < THRESHOLD_LOW:
        return "low"
    return "normal"


def _ullage_df(table: list) -> Optional[pd.DataFrame]:
    """Build the ullage DataFrame the way models.Tank.set_ullage_table does."""
    if not table:
        return None
    df = pd.DataFrame(table)
    if "ullage_cm" not in df.columns and "ullage_mm" in df.columns:
        df["ullage_cm"] = df["ullage_mm"] / 10.0
    if "ullage_cm" not in df.columns:
        return None
    return df.sort_values("ullage_cm").reset_index(drop=True)


def _trim_correction_mm(ullage_mm: float, trim: float, trim_table: list) -> float:
    """Desktop core.calculations.get_trim_correction: values stored in mm."""
    df = pd.DataFrame(trim_table)
    if "ullage_mm" in df.columns:
        ullage_col, ullage_value = "ullage_mm", ullage_mm
    else:
        ullage_col, ullage_value = "ullage_cm", ullage_mm / 10.0
    if "correction_mm" in df.columns:
        corr_col = "correction_mm"
    elif "correction_m3" in df.columns:
        corr_col = "correction_m3"
    else:
        corr_col = [c for c in df.columns if c not in [ullage_col, "trim_m"]][0]
    return bilinear_interpolate(df, ullage_col, "trim_m", corr_col, ullage_value, trim)


def _thermal_factor(temp_c: float, thermal_table: list) -> float:
    """Desktop models.Tank.get_thermal_factor: linear interp, clamped at edges."""
    if not thermal_table:
        return 1.0
    df = pd.DataFrame(thermal_table)
    if "temp_c" not in df.columns or "corr_factor" not in df.columns:
        return 1.0
    match = df[df["temp_c"] == temp_c]
    if not match.empty:
        return float(match.iloc[0]["corr_factor"])
    df = df.sort_values("temp_c")
    lower = df[df["temp_c"] < temp_c]
    upper = df[df["temp_c"] > temp_c]
    if lower.empty:
        return float(df.iloc[0]["corr_factor"])
    if upper.empty:
        return float(df.iloc[-1]["corr_factor"])
    x1, y1 = float(lower.iloc[-1]["temp_c"]), float(lower.iloc[-1]["corr_factor"])
    x2, y2 = float(upper.iloc[0]["temp_c"]), float(upper.iloc[0]["corr_factor"])
    return y1 + (temp_c - x1) * (y2 - y1) / (x2 - x1)


def calculate_tank(
    tank: dict,
    reading: dict,
    draft_aft: float,
    draft_fwd: float,
    parcels_by_id: Optional[dict] = None,
) -> dict:
    """
    Calculate one tank row.

    tank: {tank_code, capacity_m3, ullage_table, trim_table, thermal_table}
    reading: {parcel_id, ullage (cm), fill_percent, temp_celsius, density_vac}
    """
    parcels_by_id = parcels_by_id or {}
    result = {
        "tank_id": tank.get("tank_code") or tank.get("id"),
        "parcel_id": reading.get("parcel_id") or "",
        "ullage": reading.get("ullage"),
        "fill_percent": reading.get("fill_percent"),
        "temp_celsius": reading.get("temp_celsius"),
        "density_vac": reading.get("density_vac"),
        "trim_correction": None,
        "corrected_ullage": None,
        "tov": None,
        "therm_corr": None,
        "gov": None,
        "vcf": None,
        "gsv": None,
        "density_air": None,
        "mt_air": None,
        "mt_vac": None,
        "warning": "normal",
        "error": None,
    }

    # Density comes from the parcel when one is assigned (desktop behaviour)
    parcel = parcels_by_id.get(result["parcel_id"])
    if parcel and parcel.get("density_vac") and not result["density_vac"]:
        result["density_vac"] = parcel["density_vac"]

    ullage_df = _ullage_df(tank.get("ullage_table") or [])
    if ullage_df is None or ullage_df.empty:
        result["error"] = "no_ullage_table"
        return result

    capacity = float(tank.get("capacity_m3") or 0.0)
    ullage_cm = reading.get("ullage")
    fill_percent = reading.get("fill_percent")
    user_entered_fill = fill_percent is not None and ullage_cm is None

    try:
        if ullage_cm is None and fill_percent is not None:
            target_volume = (float(fill_percent) / 100.0) * capacity
            ullage_cm = reverse_interpolate(ullage_df, "ullage_cm", "volume_m3", target_volume)
            result["ullage"] = round(float(ullage_cm), 1)

        if ullage_cm is None:
            return result

        ullage_mm = float(ullage_cm) * 10.0

        trim = draft_fwd - draft_aft  # desktop uses fwd - aft for the trim table
        trim_table = tank.get("trim_table") or []
        if trim_table:
            trim_corr_mm = _trim_correction_mm(ullage_mm, trim, trim_table)
            result["trim_correction"] = trim_corr_mm / 10.0  # display in cm
            corrected_ullage_mm = ullage_mm + trim_corr_mm
        else:
            result["trim_correction"] = 0.0
            corrected_ullage_mm = ullage_mm

        result["corrected_ullage"] = corrected_ullage_mm / 10.0

        tov = linear_interpolate(ullage_df, "ullage_cm", "volume_m3", corrected_ullage_mm / 10.0)
        result["tov"] = tov

        temp = reading.get("temp_celsius")
        therm = _thermal_factor(float(temp), tank.get("thermal_table") or []) if temp is not None else 1.0
        result["therm_corr"] = therm
        gov = tov * therm
        result["gov"] = gov

        if not user_entered_fill and capacity > 0:
            result["fill_percent"] = (tov / capacity) * 100.0

        density_vac = result["density_vac"]
        if temp is not None and density_vac:
            vcf = calculate_vcf(float(temp), float(density_vac))
            result["vcf"] = vcf
            # Match desktop display-rounding convention: GSV = GOV(3dp) * VCF(5dp)
            gsv = round(gov, 3) * round(vcf, 5)
            result["gsv"] = gsv
            if density_vac < 10:  # g/cm3
                density_air = float(density_vac) - 0.0011
            else:  # kg/m3
                density_air = float(density_vac) - 1.1
            result["density_air"] = density_air
            result["mt_air"] = gsv * density_air if density_air < 10 else gsv * density_air / 1000.0
            result["mt_vac"] = gsv * float(density_vac) if density_vac < 10 else gsv * float(density_vac) / 1000.0

        result["warning"] = get_level_warning(result["fill_percent"])
    except ValueError as exc:
        result["error"] = str(exc)

    return result


def calculate_voyage(tanks: list, voyage: dict) -> dict:
    """
    Calculate all tank rows plus totals and per-parcel summaries.

    tanks: list of tank dicts (with tables)
    voyage: {vef, draft_aft, draft_fwd, parcels: [...], readings: {tank_code: reading}}
    """
    draft_aft = float(voyage.get("draft_aft") or 0.0)
    draft_fwd = float(voyage.get("draft_fwd") or 0.0)
    vef = float(voyage.get("vef") or 1.0)
    parcels = voyage.get("parcels") or []
    parcels_by_id = {str(p["id"]): p for p in parcels if p.get("id") is not None}
    readings = voyage.get("readings") or {}

    rows = []
    for tank in tanks:
        code = tank.get("tank_code") or tank.get("id")
        reading = readings.get(code) or {}
        rows.append(calculate_tank(tank, reading, draft_aft, draft_fwd, parcels_by_id))

    cargo_rows = [r for r in rows if r["parcel_id"] != SLOP_PARCEL_ID]
    total_gsv = sum(r["gsv"] or 0.0 for r in cargo_rows)
    total_mt = sum(r["mt_air"] or 0.0 for r in cargo_rows)

    parcel_summaries = []
    for parcel in parcels:
        pid = str(parcel.get("id"))
        if pid == SLOP_PARCEL_ID:
            continue
        p_rows = [r for r in rows if r["parcel_id"] == pid]
        ship_wo_vef = sum(r["mt_air"] or 0.0 for r in p_rows)
        ship_with_vef = ship_wo_vef / vef if vef else ship_wo_vef
        bl = float(parcel.get("bl_loading") or 0.0)
        diff_wo = ship_wo_vef - bl
        diff_with = ship_with_vef - bl
        parcel_summaries.append({
            "parcel_id": pid,
            "name": parcel.get("name") or "",
            "receiver": parcel.get("receiver") or "",
            "color": parcel.get("color") or "#3B82F6",
            "gsv": sum(r["gsv"] or 0.0 for r in p_rows),
            "mt_air": ship_wo_vef,
            "ship_with_vef": ship_with_vef,
            "bl_figure": bl,
            "diff_wo_vef": diff_wo,
            "diff_with_vef": diff_with,
            "diff_permille_wo_vef": (diff_wo / bl) * 1000 if bl else 0.0,
            "diff_permille_with_vef": (diff_with / bl) * 1000 if bl else 0.0,
        })

    return {
        "rows": rows,
        "totals": {
            "gsv": total_gsv,
            "mt_air": total_mt,
            "trim": round(draft_aft - draft_fwd, 3),
        },
        "parcels": parcel_summaries,
    }
