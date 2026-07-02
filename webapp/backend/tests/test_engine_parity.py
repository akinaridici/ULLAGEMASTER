"""
Parity tests: the web engine must reproduce the desktop app's calculation
flow (MainWindow._recalculate_tank) exactly, using the real ship config.
"""

import json
import math
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.engine import calculate_tank, calculate_voyage, get_level_warning
from app.core.astm_54b import calculate_vcf
from app.core.interpolation import linear_interpolate, reverse_interpolate

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "config", "ship_config.json")


@pytest.fixture(scope="module")
def ship_config():
    if not os.path.exists(CONFIG_PATH):
        pytest.skip("real ship_config.json not available")
    with open(CONFIG_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def tank_1p(ship_config):
    t = ship_config["tanks"][0]
    return {
        "tank_code": t["id"],
        "capacity_m3": t["capacity_m3"],
        "ullage_table": t["ullage_table"],
        "trim_table": t["trim_table"],
        "thermal_table": t["thermal_table"],
    }


def _desktop_get_trim_correction(ullage_mm, trim, trim_table):
    """Copied verbatim from desktop src/core/calculations.py:get_trim_correction."""
    from app.core.interpolation import bilinear_interpolate

    if "ullage_mm" in trim_table.columns:
        ullage_col = "ullage_mm"
        ullage_value = ullage_mm
    else:
        ullage_col = "ullage_cm"
        ullage_value = ullage_mm / 10.0
    if "correction_mm" in trim_table.columns:
        corr_col = "correction_mm"
    elif "correction_m3" in trim_table.columns:
        corr_col = "correction_m3"
    else:
        corr_col = [c for c in trim_table.columns if c not in [ullage_col, "trim_m"]][0]
    return bilinear_interpolate(trim_table, ullage_col, "trim_m", corr_col, ullage_value, trim)


def desktop_reference(tank, ullage_cm, temp, density_vac, draft_aft, draft_fwd):
    """Reimplementation of MainWindow._recalculate_tank, straight from the desktop code."""
    df = pd.DataFrame(tank["ullage_table"])
    df["ullage_cm"] = df["ullage_mm"] / 10.0
    df = df.sort_values("ullage_cm").reset_index(drop=True)

    ullage_mm = ullage_cm * 10.0
    trim = draft_fwd - draft_aft

    trim_corr_mm = _desktop_get_trim_correction(ullage_mm, trim, pd.DataFrame(tank["trim_table"]))
    corrected_ullage_mm = ullage_mm + trim_corr_mm

    tov = linear_interpolate(df, "ullage_cm", "volume_m3", corrected_ullage_mm / 10.0)

    tdf = pd.DataFrame(tank["thermal_table"]).sort_values("temp_c")
    match = tdf[tdf["temp_c"] == temp]
    if not match.empty:
        therm = float(match.iloc[0]["corr_factor"])
    else:
        lower, upper = tdf[tdf["temp_c"] < temp], tdf[tdf["temp_c"] > temp]
        x1, y1 = float(lower.iloc[-1]["temp_c"]), float(lower.iloc[-1]["corr_factor"])
        x2, y2 = float(upper.iloc[0]["temp_c"]), float(upper.iloc[0]["corr_factor"])
        therm = y1 + (temp - x1) * (y2 - y1) / (x2 - x1)

    gov = tov * therm
    vcf = calculate_vcf(temp, density_vac)
    gsv = round(gov, 3) * round(vcf, 5)
    density_air = density_vac - 0.0011 if density_vac < 10 else density_vac - 1.1
    mt_air = gsv * density_air if density_air < 10 else gsv * density_air / 1000.0
    return {"tov": tov, "gov": gov, "vcf": vcf, "gsv": gsv, "mt_air": mt_air,
            "trim_corr_cm": trim_corr_mm / 10.0}


def test_full_tank_parity(tank_1p):
    result = calculate_tank(
        tank_1p,
        {"parcel_id": "1", "ullage": 150.0, "temp_celsius": 22.5, "density_vac": 0.7850},
        draft_aft=8.0, draft_fwd=7.0,
    )
    ref = desktop_reference(tank_1p, 150.0, 22.5, 0.7850, 8.0, 7.0)
    assert result["error"] is None
    assert math.isclose(result["tov"], ref["tov"], rel_tol=1e-12)
    assert math.isclose(result["gov"], ref["gov"], rel_tol=1e-12)
    assert math.isclose(result["vcf"], ref["vcf"], rel_tol=1e-12)
    assert math.isclose(result["gsv"], ref["gsv"], rel_tol=1e-12)
    assert math.isclose(result["mt_air"], ref["mt_air"], rel_tol=1e-12)
    assert math.isclose(result["trim_correction"], ref["trim_corr_cm"], rel_tol=1e-12)


def test_fill_percent_input_derives_ullage(tank_1p):
    """Entering fill % must reverse-interpolate the same ullage the desktop derives."""
    result = calculate_tank(
        tank_1p,
        {"parcel_id": "1", "fill_percent": 90.0, "temp_celsius": 20.0, "density_vac": 0.8300},
        draft_aft=8.0, draft_fwd=8.0,
    )
    assert result["error"] is None
    df = pd.DataFrame(tank_1p["ullage_table"])
    df["ullage_cm"] = df["ullage_mm"] / 10.0
    expected_ullage = reverse_interpolate(
        df.sort_values("ullage_cm").reset_index(drop=True),
        "ullage_cm", "volume_m3", 0.90 * tank_1p["capacity_m3"],
    )
    assert math.isclose(result["ullage"], round(expected_ullage, 1), abs_tol=0.051)
    # fill % entered by the user is preserved, not recomputed
    assert result["fill_percent"] == 90.0
    assert result["warning"] == "normal"


def test_warnings():
    assert get_level_warning(98.5) == "high_high"
    assert get_level_warning(96.0) == "high"
    assert get_level_warning(50.0) == "low"
    assert get_level_warning(80.0) == "normal"


def test_voyage_totals_exclude_slop(tank_1p, ship_config):
    t2 = dict(tank_1p, tank_code="1S")
    voyage = {
        "vef": 0.9998, "draft_aft": 8.0, "draft_fwd": 8.0,
        "parcels": [
            {"id": "1", "name": "MOTORIN", "receiver": "X", "density_vac": 0.8300,
             "color": "#f00", "bl_loading": 1000.0},
            {"id": "0", "name": "SLOP", "receiver": "", "density_vac": 0.9,
             "color": "#999", "bl_loading": 0.0},
        ],
        "readings": {
            "1P": {"parcel_id": "1", "ullage": 150.0, "temp_celsius": 20.0},
            "1S": {"parcel_id": "0", "ullage": 150.0, "temp_celsius": 20.0},
        },
    }
    calc = calculate_voyage([tank_1p, t2], voyage)
    slop_row = next(r for r in calc["rows"] if r["tank_id"] == "1S")
    cargo_row = next(r for r in calc["rows"] if r["tank_id"] == "1P")
    # SLOP excluded from totals
    assert math.isclose(calc["totals"]["gsv"], cargo_row["gsv"], rel_tol=1e-12)
    assert slop_row["gsv"] is not None
    # density pulled from parcel
    assert cargo_row["density_vac"] == 0.8300
    # parcel summary: ship_with_vef = mt / vef
    p = calc["parcels"][0]
    assert math.isclose(p["ship_with_vef"], p["mt_air"] / 0.9998, rel_tol=1e-12)
    assert not any(s["parcel_id"] == "0" for s in calc["parcels"])
