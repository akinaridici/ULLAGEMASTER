"""End-to-end API smoke test: register -> login -> import ship -> calculate -> save voyage -> export."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Isolated database for the test run (must be set before importing the app)
_tmpdir = tempfile.mkdtemp()
os.environ["ULLAGEMASTER_DATA_DIR"] = _tmpdir
os.environ["ULLAGEMASTER_DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "config", "ship_config.json")

client = TestClient(app)


@pytest.fixture(scope="module")
def token():
    r = client.post("/api/auth/register", json={
        "email": "test@example.com", "password": "secret123", "full_name": "Test Officer",
    })
    assert r.status_code == 200, r.text
    r = client.post("/api/auth/login", data={"username": "test@example.com", "password": "secret123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def ship_id(auth):
    if not os.path.exists(CONFIG_PATH):
        pytest.skip("real ship_config.json not available")
    with open(CONFIG_PATH, "rb") as f:
        r = client.post("/api/ships/import-config", headers=auth,
                        files={"file": ("ship_config.json", f, "application/json")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"]
    assert len(body["tanks"]) > 0
    assert body["tanks"][0]["has_ullage_table"]
    return body["id"]


def test_login_rejects_bad_password():
    client.post("/api/auth/register", json={"email": "x@y.com", "password": "goodpass"})
    r = client.post("/api/auth/login", data={"username": "x@y.com", "password": "wrong"})
    assert r.status_code == 401


def test_requires_auth():
    assert client.get("/api/ships").status_code == 401


def test_calculate(auth, ship_id):
    payload = {
        "vef": 1.0, "draft_aft": 8.0, "draft_fwd": 7.5,
        "parcels": [{"id": "1", "name": "MOTORIN", "receiver": "ACME",
                     "density_vac": 0.8300, "color": "#ff0000", "bl_loading": 500.0}],
        "readings": {"1P": {"parcel_id": "1", "ullage": 150.0, "temp_celsius": 20.0}},
    }
    r = client.post(f"/api/ships/{ship_id}/calculate", headers=auth, json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    row = next(x for x in body["rows"] if x["tank_id"] == "1P")
    assert row["tov"] and row["gsv"] and row["mt_air"]
    assert body["totals"]["gsv"] > 0
    assert body["totals"]["trim"] == 0.5
    assert body["parcels"][0]["bl_figure"] == 500.0


def test_voyage_crud_and_export(auth, ship_id):
    voyage = {
        "voyage_number": "30/2026", "date": "2026-07-02", "port": "TUTUNCIFTLIK",
        "terminal": "TUPRAS", "vef": 0.9998, "draft_aft": 8.0, "draft_fwd": 8.0,
        "parcels": [{"id": "1", "name": "K.BENZIN", "receiver": "ACME",
                     "density_vac": 0.7450, "color": "#00ff00", "bl_loading": 700.0}],
        "readings": {"1P": {"parcel_id": "1", "ullage": 200.0, "temp_celsius": 18.5}},
    }
    r = client.post(f"/api/ships/{ship_id}/voyages", headers=auth, json=voyage)
    assert r.status_code == 200, r.text
    vid = r.json()["id"]

    r = client.get(f"/api/ships/{ship_id}/voyages/{vid}", headers=auth)
    assert r.json()["readings"]["1P"]["ullage"] == 200.0

    r = client.get(f"/api/ships/{ship_id}/voyages", headers=auth)
    assert any(v["id"] == vid for v in r.json())

    r = client.get(f"/api/ships/{ship_id}/voyages/{vid}/export/xlsx", headers=auth)
    assert r.status_code == 200
    assert r.content[:2] == b"PK"  # xlsx = zip

    r = client.get(f"/api/ships/{ship_id}/voyages/{vid}/export/pdf", headers=auth)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"

    r = client.get(f"/api/ships/{ship_id}/voyages/{vid}/export/stowage", headers=auth)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
    assert "stowage_plan" in r.headers["content-disposition"]


def _make_png() -> bytes:
    import io

    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.new("RGB", (40, 20), (200, 30, 30)).save(buf, "PNG")
    return buf.getvalue()


MINIMAL_PNG = _make_png()


def test_logo_upload_and_protest_pdf(auth, ship_id):
    # upload logo
    r = client.post(f"/api/ships/{ship_id}/logo", headers=auth,
                    files={"file": ("logo.png", MINIMAL_PNG, "image/png")})
    assert r.status_code == 200, r.text
    r = client.get(f"/api/ships/{ship_id}", headers=auth)
    assert r.json()["has_logo"] is True
    r = client.get(f"/api/ships/{ship_id}/logo", headers=auth)
    assert r.status_code == 200 and r.content[:8] == b"\x89PNG\r\n\x1a\n"

    # reject non-image
    r = client.post(f"/api/ships/{ship_id}/logo", headers=auth,
                    files={"file": ("x.png", b"not an image", "image/png")})
    assert r.status_code == 400

    # voyage with discharging figures
    voyage = {
        "voyage_number": "PRT/2026", "date": "02.07.2026", "port": "ALIAGA", "terminal": "TUPRAS",
        "vef": 0.9996,
        "parcels": [
            {"id": "1", "name": "KBZ", "receiver": "MERSIN TUPRAS", "density_vac": 0.7377,
             "color": "#FF6B6B", "bl_loading": 2541.0, "ship_figure_loading": 2554.664,
             "outturn_figure": 2540.0},
            {"id": "0", "name": "SLOP", "receiver": "", "density_vac": 0.9, "color": "#9CA3AF",
             "bl_loading": 0.0},
        ],
        "readings": {"1P": {"parcel_id": "1", "ullage": 150.0, "temp_celsius": 20.0}},
    }
    r = client.post(f"/api/ships/{ship_id}/voyages", headers=auth, json=voyage)
    assert r.status_code == 200, r.text
    vid = r.json()["id"]
    assert r.json()["parcels"][0]["outturn_figure"] == 2540.0

    # single-parcel loading protest
    r = client.get(f"/api/ships/{ship_id}/voyages/{vid}/export/protest?operation=loading&parcel_id=1", headers=auth)
    assert r.status_code == 200 and r.content[:4] == b"%PDF", r.text

    # all-parcels discharging protest (SLOP skipped)
    r = client.get(f"/api/ships/{ship_id}/voyages/{vid}/export/protest?operation=discharging", headers=auth)
    assert r.status_code == 200 and r.content[:4] == b"%PDF"

    # invalid operation
    r = client.get(f"/api/ships/{ship_id}/voyages/{vid}/export/protest?operation=x", headers=auth)
    assert r.status_code == 400


def test_stowage_plan_roundtrip(auth, ship_id):
    plan = {
        "cargo_requests": [
            {"id": "c1", "cargo_type": "GASOIL", "quantity": 1200.0, "density": 0.845,
             "receivers": ["SHELL", "OPET"], "color": "#FF6B6B"},
        ],
        "assignments": {
            "1P": {"cargo_id": "c1", "quantity_loaded": 779.84},
            "1S": {"cargo_id": "c1", "quantity_loaded": 420.16},
        },
        "excluded_tanks": ["8P"],
        "locked_tanks": ["1P"],
    }
    voyage = {"voyage_number": "STW/2026", "stowage_plan": plan}
    r = client.post(f"/api/ships/{ship_id}/voyages", headers=auth, json=voyage)
    assert r.status_code == 200, r.text
    vid = r.json()["id"]
    assert r.json()["stowage_plan"]["assignments"]["1P"]["quantity_loaded"] == 779.84

    r = client.get(f"/api/ships/{ship_id}/voyages/{vid}", headers=auth)
    got = r.json()["stowage_plan"]
    assert got["cargo_requests"][0]["receivers"] == ["SHELL", "OPET"]
    assert got["excluded_tanks"] == ["8P"]
    assert got["locked_tanks"] == ["1P"]

    # Older voyages (created before the column existed) return an empty default plan
    r = client.get(f"/api/ships/{ship_id}/voyages", headers=auth)
    assert r.status_code == 200


def test_csv_table_upload(auth):
    ship = {"name": "TEST SHIP", "tanks": [{"tank_code": "1P", "name": "No.1 Port", "capacity_m3": 100.0}]}
    r = client.post("/api/ships", headers=auth, json=ship)
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    csv_data = "ullage_cm,volume_m3\n0,100\n50,50\n100,0\n"
    r = client.post(f"/api/ships/{sid}/tanks/1P/tables/ullage", headers=auth,
                    files={"file": ("u.csv", csv_data, "text/csv")})
    assert r.status_code == 200, r.text
    assert r.json()["has_ullage_table"]

    r = client.post(f"/api/ships/{sid}/calculate", headers=auth, json={
        "readings": {"1P": {"ullage": 50.0}},
    })
    assert r.status_code == 200
    row = r.json()["rows"][0]
    assert row["tov"] == 50.0
    assert row["fill_percent"] == 50.0

    # Ships are private: another user must not see them
    client.post("/api/auth/register", json={"email": "other@y.com", "password": "otherpass"})
    other = client.post("/api/auth/login", data={"username": "other@y.com", "password": "otherpass"}).json()
    r = client.get(f"/api/ships/{sid}", headers={"Authorization": f"Bearer {other['access_token']}"})
    assert r.status_code == 404
