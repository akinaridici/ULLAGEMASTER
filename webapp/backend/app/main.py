"""UllageMaster Web — FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from .config import CORS_ORIGINS
from .database import Base, engine
from .routers import auth, calc, export, ships, voyages

Base.metadata.create_all(bind=engine)


def _migrate():
    """Additive migrations for databases created by older versions."""
    inspector = inspect(engine)
    voyage_cols = {c["name"] for c in inspector.get_columns("voyages")}
    ship_cols = {c["name"] for c in inspector.get_columns("ships")}
    with engine.begin() as conn:
        if "stowage_plan_json" not in voyage_cols:
            conn.execute(text("ALTER TABLE voyages ADD COLUMN stowage_plan_json TEXT DEFAULT '{}'"))
        if "logo_png" not in ship_cols:
            conn.execute(text("ALTER TABLE ships ADD COLUMN logo_png BLOB"))


_migrate()

app = FastAPI(title="UllageMaster Web", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(ships.router)
app.include_router(voyages.router)
app.include_router(calc.router)
app.include_router(export.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
