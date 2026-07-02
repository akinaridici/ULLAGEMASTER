"""Application settings, overridable via environment variables."""

import os

SECRET_KEY = os.environ.get("ULLAGEMASTER_SECRET_KEY", "dev-secret-change-me-0123456789abcdef")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ULLAGEMASTER_TOKEN_MINUTES", "1440"))

DATA_DIR = os.environ.get("ULLAGEMASTER_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
DATABASE_URL = os.environ.get(
    "ULLAGEMASTER_DATABASE_URL",
    f"sqlite:///{os.path.abspath(os.path.join(DATA_DIR, 'ullagemaster.db'))}",
)

CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("ULLAGEMASTER_CORS_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",")
    if o.strip()
]
