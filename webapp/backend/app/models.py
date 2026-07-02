"""Database models: User, Ship, Tank, Voyage."""

import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    ships: Mapped[list["Ship"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Ship(Base):
    __tablename__ = "ships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    default_vef: Mapped[float] = mapped_column(Float, default=1.0)
    slop_density: Mapped[float] = mapped_column(Float, default=0.9)
    chief_officer: Mapped[str] = mapped_column(String(255), default="")
    master: Mapped[str] = mapped_column(String(255), default="")
    trim_values_json: Mapped[str] = mapped_column(Text, default="[]")
    logo_png: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    owner: Mapped[User] = relationship(back_populates="ships")
    tanks: Mapped[list["Tank"]] = relationship(
        back_populates="ship", cascade="all, delete-orphan", order_by="Tank.position"
    )
    voyages: Mapped[list["Voyage"]] = relationship(back_populates="ship", cascade="all, delete-orphan")

    @property
    def trim_values(self) -> list:
        return json.loads(self.trim_values_json or "[]")


class Tank(Base):
    __tablename__ = "tanks"
    __table_args__ = (UniqueConstraint("ship_id", "tank_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ship_id: Mapped[int] = mapped_column(ForeignKey("ships.id"), index=True)
    tank_code: Mapped[str] = mapped_column(String(32))  # "1P", "SlopS", ...
    name: Mapped[str] = mapped_column(String(255), default="")
    capacity_m3: Mapped[float] = mapped_column(Float, default=0.0)
    position: Mapped[int] = mapped_column(Integer, default=0)
    ullage_table_json: Mapped[str] = mapped_column(Text, default="[]")
    trim_table_json: Mapped[str] = mapped_column(Text, default="[]")
    thermal_table_json: Mapped[str] = mapped_column(Text, default="[]")

    ship: Mapped[Ship] = relationship(back_populates="tanks")

    def as_calc_dict(self) -> dict:
        return {
            "tank_code": self.tank_code,
            "capacity_m3": self.capacity_m3,
            "ullage_table": json.loads(self.ullage_table_json or "[]"),
            "trim_table": json.loads(self.trim_table_json or "[]"),
            "thermal_table": json.loads(self.thermal_table_json or "[]"),
        }


class Voyage(Base):
    __tablename__ = "voyages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ship_id: Mapped[int] = mapped_column(ForeignKey("ships.id"), index=True)
    voyage_number: Mapped[str] = mapped_column(String(64), default="")
    date: Mapped[str] = mapped_column(String(32), default="")
    port: Mapped[str] = mapped_column(String(255), default="")
    terminal: Mapped[str] = mapped_column(String(255), default="")
    vef: Mapped[float] = mapped_column(Float, default=1.0)
    draft_aft: Mapped[float] = mapped_column(Float, default=0.0)
    draft_fwd: Mapped[float] = mapped_column(Float, default=0.0)
    chief_officer: Mapped[str] = mapped_column(String(255), default="")
    master: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    parcels_json: Mapped[str] = mapped_column(Text, default="[]")
    readings_json: Mapped[str] = mapped_column(Text, default="{}")  # inputs only
    stowage_plan_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    ship: Mapped[Ship] = relationship(back_populates="voyages")

    @property
    def parcels(self) -> list:
        return json.loads(self.parcels_json or "[]")

    @property
    def readings(self) -> dict:
        return json.loads(self.readings_json or "{}")

    @property
    def stowage_plan(self) -> dict:
        return json.loads(self.stowage_plan_json or "{}")
