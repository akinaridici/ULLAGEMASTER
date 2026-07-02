export interface User {
  id: number;
  email: string;
  full_name: string;
}

export interface TankOut {
  tank_code: string;
  name: string;
  capacity_m3: number;
  has_ullage_table: boolean;
  has_trim_table: boolean;
  has_thermal_table: boolean;
}

export interface ShipListItem {
  id: number;
  name: string;
  tank_count: number;
  voyage_count: number;
}

export interface Ship {
  id: number;
  name: string;
  default_vef: number;
  slop_density: number;
  chief_officer: string;
  master: string;
  trim_values: number[];
  tanks: TankOut[];
  has_logo: boolean;
}

export interface Parcel {
  id: string;
  name: string;
  receiver: string;
  density_vac: number;
  color: string;
  bl_loading: number;
  ship_figure_loading: number; // ship figure at loading port (discharging ops)
  outturn_figure: number; // outturn figure (discharging ops)
}

export interface Reading {
  parcel_id: string;
  ullage: number | null;
  fill_percent: number | null;
  temp_celsius: number | null;
  density_vac: number | null;
}

export interface StowageCargo {
  id: string;
  cargo_type: string;
  quantity: number; // m³ (= ton / density)
  density: number;
  receivers: string[];
  color: string;
}

export interface StowageAssignment {
  cargo_id: string;
  quantity_loaded: number; // m³
}

export interface StowagePlanData {
  cargo_requests: StowageCargo[];
  assignments: Record<string, StowageAssignment>;
  excluded_tanks: string[];
  locked_tanks: string[];
}

export interface VoyageData {
  voyage_number: string;
  date: string;
  port: string;
  terminal: string;
  vef: number;
  draft_aft: number;
  draft_fwd: number;
  chief_officer: string;
  master: string;
  notes: string;
  parcels: Parcel[];
  readings: Record<string, Reading>;
  stowage_plan: StowagePlanData;
}

export interface Voyage extends VoyageData {
  id: number;
  ship_id: number;
  updated_at?: string;
}

export interface VoyageListItem {
  id: number;
  voyage_number: string;
  date: string;
  port: string;
  terminal: string;
  updated_at?: string;
}

export interface CalcRow {
  tank_id: string;
  parcel_id: string;
  ullage: number | null;
  fill_percent: number | null;
  temp_celsius: number | null;
  density_vac: number | null;
  trim_correction: number | null;
  corrected_ullage: number | null;
  tov: number | null;
  therm_corr: number | null;
  gov: number | null;
  vcf: number | null;
  gsv: number | null;
  density_air: number | null;
  mt_air: number | null;
  mt_vac: number | null;
  warning: string;
  error: string | null;
}

export interface ParcelSummary {
  parcel_id: string;
  name: string;
  receiver: string;
  color: string;
  gsv: number;
  mt_air: number;
  ship_with_vef: number;
  bl_figure: number;
  diff_wo_vef: number;
  diff_with_vef: number;
  diff_permille_wo_vef: number;
  diff_permille_with_vef: number;
}

export interface CalcResponse {
  rows: CalcRow[];
  totals: { gsv: number; mt_air: number; trim: number };
  parcels: ParcelSummary[];
}
