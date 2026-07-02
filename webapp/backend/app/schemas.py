"""Pydantic request/response schemas."""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ---- Auth ----

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str

    model_config = {"from_attributes": True}


# ---- Ships & tanks ----

class TankIn(BaseModel):
    tank_code: str
    name: str = ""
    capacity_m3: float = 0.0
    ullage_table: list[dict] = []
    trim_table: list[dict] = []
    thermal_table: list[dict] = []


class TankOut(BaseModel):
    tank_code: str
    name: str
    capacity_m3: float
    has_ullage_table: bool
    has_trim_table: bool
    has_thermal_table: bool


class ShipIn(BaseModel):
    name: str
    default_vef: float = 1.0
    slop_density: float = 0.9
    chief_officer: str = ""
    master: str = ""
    trim_values: list[float] = []
    tanks: list[TankIn] = []


class ShipOut(BaseModel):
    id: int
    name: str
    default_vef: float
    slop_density: float
    chief_officer: str
    master: str
    trim_values: list[float]
    tanks: list[TankOut]
    has_logo: bool = False


class ShipListItem(BaseModel):
    id: int
    name: str
    tank_count: int
    voyage_count: int


# ---- Parcels / readings / voyages ----

class ParcelIn(BaseModel):
    id: str
    name: str = ""
    receiver: str = ""
    density_vac: float = 0.0
    color: str = "#3B82F6"
    bl_loading: float = 0.0
    ship_figure_loading: float = 0.0  # ship figure at loading port (discharging ops)
    outturn_figure: float = 0.0       # outturn figure (discharging ops)


class ReadingIn(BaseModel):
    parcel_id: str = ""
    ullage: Optional[float] = None          # cm
    fill_percent: Optional[float] = None
    temp_celsius: Optional[float] = None
    density_vac: Optional[float] = None


class StowageCargoIn(BaseModel):
    id: str
    cargo_type: str = ""
    quantity: float = 0.0  # m³ (= ton / density)
    density: float = 0.85
    receivers: list[str] = []
    color: str = "#3B82F6"


class StowageAssignmentIn(BaseModel):
    cargo_id: str
    quantity_loaded: float = 0.0  # m³


class StowagePlanIn(BaseModel):
    cargo_requests: list[StowageCargoIn] = []
    assignments: dict[str, StowageAssignmentIn] = {}
    excluded_tanks: list[str] = []
    locked_tanks: list[str] = []


class VoyageIn(BaseModel):
    voyage_number: str = ""
    date: str = ""
    port: str = ""
    terminal: str = ""
    vef: float = 1.0
    draft_aft: float = 0.0
    draft_fwd: float = 0.0
    chief_officer: str = ""
    master: str = ""
    notes: str = ""
    parcels: list[ParcelIn] = []
    readings: dict[str, ReadingIn] = {}
    stowage_plan: StowagePlanIn = StowagePlanIn()


class VoyageOut(VoyageIn):
    id: int
    ship_id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class VoyageListItem(BaseModel):
    id: int
    voyage_number: str
    date: str
    port: str
    terminal: str
    updated_at: Optional[str] = None


# ---- Calculation ----

class CalcRequest(BaseModel):
    vef: float = 1.0
    draft_aft: float = 0.0
    draft_fwd: float = 0.0
    parcels: list[ParcelIn] = []
    readings: dict[str, ReadingIn] = {}


class CalcRow(BaseModel):
    tank_id: str
    parcel_id: str
    ullage: Optional[float] = None
    fill_percent: Optional[float] = None
    temp_celsius: Optional[float] = None
    density_vac: Optional[float] = None
    trim_correction: Optional[float] = None
    corrected_ullage: Optional[float] = None
    tov: Optional[float] = None
    therm_corr: Optional[float] = None
    gov: Optional[float] = None
    vcf: Optional[float] = None
    gsv: Optional[float] = None
    density_air: Optional[float] = None
    mt_air: Optional[float] = None
    mt_vac: Optional[float] = None
    warning: str = "normal"
    error: Optional[str] = None


class ParcelSummary(BaseModel):
    parcel_id: str
    name: str
    receiver: str
    color: str
    gsv: float
    mt_air: float
    ship_with_vef: float
    bl_figure: float
    diff_wo_vef: float
    diff_with_vef: float
    diff_permille_wo_vef: float
    diff_permille_with_vef: float


class CalcTotals(BaseModel):
    gsv: float
    mt_air: float
    trim: float


class CalcResponse(BaseModel):
    rows: list[CalcRow]
    totals: CalcTotals
    parcels: list[ParcelSummary]
