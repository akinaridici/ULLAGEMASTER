# UllageMaster Web

Web version of the UllageMaster desktop app: multi-user cargo (ullage) calculation
for oil tankers. FastAPI + SQLite backend, React frontend, packaged with Docker for
offline use on board or cloud deployment.

The calculation engine is copied verbatim from the desktop app (`src/core`) and covered
by parity tests, so web results match the desktop exactly (ASTM 54B VCF, mm-based trim
correction applied to ullage, per-tank thermal factor, GSV = GOV(3dp) × VCF(5dp)).

## Quick start (Docker — recommended)

```bash
cd webapp
ULLAGEMASTER_SECRET_KEY="$(openssl rand -hex 32)" docker compose up --build -d
```

Open http://localhost:8080 — register an account, then click
**Import ship_config.json** and pick the desktop app's `data/config/ship_config.json`.
All tanks, ullage/trim/thermal tables, V.E.F. and officers are imported in one click.

Data (users, ships, voyages) lives in the `ullagemaster-data` Docker volume and
survives restarts. For a cloud deployment, run the same compose file on any VPS and
put a TLS proxy (e.g. Caddy) in front of port 8080.

## Development

Backend (Python 3.12):

```bash
cd webapp/backend
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt pytest httpx
.venv/bin/uvicorn app.main:app --reload           # http://localhost:8000
.venv/bin/python -m pytest tests/                  # parity + API tests
```

Frontend:

```bash
cd webapp/frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to :8000
```

## API overview

- `POST /api/auth/register`, `POST /api/auth/login` (OAuth2 form), `GET /api/auth/me`
- `GET/POST /api/ships`, `POST /api/ships/import-config` (desktop JSON),
  `GET/PUT/DELETE /api/ships/{id}`
- `POST /api/ships/{id}/tanks/{code}/tables/{ullage|trim|thermal}` — CSV upload
- `GET/POST /api/ships/{id}/voyages`, `GET/PUT/DELETE .../voyages/{vid}`
- `POST /api/ships/{id}/calculate` — stateless: inputs in, all derived figures out
- `GET .../voyages/{vid}/export/{xlsx|pdf|stowage}` (`stowage` = visual stowage plan PDF)

Interactive docs at `/docs` (Swagger UI) when the backend is running.

## MVP scope

Included: auth, multi-ship, config import, CSV table upload, voyage CRUD, full
calculation grid (dual ullage↔fill% input, batch fill, trim/thermal/VCF, level
warnings, SLOP exclusion), parcel discrepancy (with/without VEF, ‰), Excel + PDF
export, visual stowage plan (ship view tab + PDF export, DejaVu fonts for
Turkish characters), and the **drag-and-drop stowage planner** (desktop parity:
charterer order with ton/density→volume, draggable cargo cards with remaining
badges, tank cards with fill bars, 97.7% max-fill rule, tank↔tank swap,
lock/exclude tanks, %97.7 and hold-to-Colorize tools, requested-vs-loaded plan
viewer, and two-way Stowage↔Ullage transfer; the plan is saved inside the
voyage). See FEATURES.md for the full desktop parity checklist.

Deferred (next phases): protest PDF + discharging discrepancy, formal ullage
report (CBO 07), report functions tab, i18n (TR/EN), dark theme, imperial units,
XLSM/ASCII exports, setup wizard, roles/fleet management.
