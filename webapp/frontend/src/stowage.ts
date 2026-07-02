/**
 * Stowage planning logic — a faithful port of the desktop app's rules
 * (main_window.py: handle_cargo_drop, handle_tank_swap, _fill_tanks_to_97_7).
 * All functions are pure: they take a plan and return a new plan.
 */

import type { StowageAssignment, StowageCargo, StowagePlanData } from "./types";

export const MAX_FILL_FACTOR = 0.977;

export const CARGO_COLORS = [
  "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
  "#DDA0DD", "#F7DC6F", "#BB8FCE", "#85C1E9", "#F8B500",
];

export function emptyPlan(): StowagePlanData {
  return { cargo_requests: [], assignments: {}, excluded_tanks: [], locked_tanks: [] };
}

export function normalizePlan(plan?: Partial<StowagePlanData> | null): StowagePlanData {
  return {
    cargo_requests: plan?.cargo_requests ?? [],
    assignments: plan?.assignments ?? {},
    excluded_tanks: plan?.excluded_tanks ?? [],
    locked_tanks: plan?.locked_tanks ?? [],
  };
}

export function isSlopCargo(cargo: StowageCargo | undefined): boolean {
  return !!cargo && cargo.cargo_type.toLowerCase().includes("slop");
}

/** Total m³ of a cargo already assigned across all tanks. */
export function loadedTotal(plan: StowagePlanData, cargoId: string): number {
  return Object.values(plan.assignments)
    .filter((a) => a.cargo_id === cargoId)
    .reduce((sum, a) => sum + a.quantity_loaded, 0);
}

/** Remaining m³ of a cargo request (negative = over-loaded). */
export function remaining(plan: StowagePlanData, cargo: StowageCargo): number {
  return cargo.quantity - loadedTotal(plan, cargo.id);
}

export function cargoById(plan: StowagePlanData, cargoId: string): StowageCargo | undefined {
  return plan.cargo_requests.find((c) => c.id === cargoId);
}

function canAccept(plan: StowagePlanData, tankId: string): boolean {
  return !plan.locked_tanks.includes(tankId) && !plan.excluded_tanks.includes(tankId);
}

/**
 * Drop a cargo onto a tank (desktop handle_cargo_drop):
 * - capacity capped at 97.7%
 * - a different existing cargo is replaced; the same cargo is topped up
 * - loads min(available space, remaining cargo)
 */
export function assignCargo(
  plan: StowagePlanData,
  capacities: Record<string, number>,
  cargoId: string,
  tankId: string,
): StowagePlanData {
  const cargo = cargoById(plan, cargoId);
  const capacity = capacities[tankId] || 0;
  if (!cargo || capacity <= 0 || !canAccept(plan, tankId)) return plan;

  const maxCapacity = capacity * MAX_FILL_FACTOR;
  const assignments = { ...plan.assignments };
  const existing = assignments[tankId];

  let alreadyInTank = 0;
  if (existing && existing.cargo_id === cargoId) {
    alreadyInTank = existing.quantity_loaded;
  } else if (existing) {
    delete assignments[tankId]; // different cargo: clear first
  }

  const loadedElsewhere = loadedTotal({ ...plan, assignments }, cargoId);
  const remainingCargo = cargo.quantity - loadedElsewhere;
  const availableSpace = maxCapacity - alreadyInTank;
  const qtyToLoad = Math.min(availableSpace, remainingCargo);

  if (qtyToLoad <= 0 && alreadyInTank <= 0) return { ...plan, assignments };
  const total = Math.min(alreadyInTank + Math.max(qtyToLoad, 0), maxCapacity);
  if (total <= 0) return { ...plan, assignments };

  assignments[tankId] = { cargo_id: cargoId, quantity_loaded: total };
  return { ...plan, assignments };
}

/** Swap the cargos of two tanks, each capped at 97.7% of its new tank (desktop handle_tank_swap). */
export function swapTanks(
  plan: StowagePlanData,
  capacities: Record<string, number>,
  sourceId: string,
  targetId: string,
): StowagePlanData {
  if (sourceId === targetId) return plan;
  if (!canAccept(plan, targetId) || plan.locked_tanks.includes(sourceId)) return plan;

  const assignments = { ...plan.assignments };
  const src = assignments[sourceId];
  const dst = assignments[targetId];
  if (!src) return plan;

  const cap = (tankId: string, a: StowageAssignment): StowageAssignment => ({
    cargo_id: a.cargo_id,
    quantity_loaded: Math.min(a.quantity_loaded, (capacities[tankId] || 0) * MAX_FILL_FACTOR),
  });

  delete assignments[sourceId];
  delete assignments[targetId];
  assignments[targetId] = cap(targetId, src);
  if (dst) assignments[sourceId] = cap(sourceId, dst);
  return { ...plan, assignments };
}

/** Fill every assigned tank to 97.7% (skips SLOP cargo and excluded tanks). Returns [plan, changedCount]. */
export function fillTo977(
  plan: StowagePlanData,
  capacities: Record<string, number>,
): [StowagePlanData, number] {
  const assignments = { ...plan.assignments };
  let changed = 0;
  for (const [tankId, a] of Object.entries(assignments)) {
    if (plan.excluded_tanks.includes(tankId)) continue;
    if (isSlopCargo(cargoById(plan, a.cargo_id))) continue;
    const target = (capacities[tankId] || 0) * MAX_FILL_FACTOR;
    if (target > 0 && Math.abs(a.quantity_loaded - target) > 1e-9) {
      assignments[tankId] = { ...a, quantity_loaded: target };
      changed++;
    }
  }
  return [{ ...plan, assignments }, changed];
}

export function emptyTank(plan: StowagePlanData, tankId: string): StowagePlanData {
  if (!(tankId in plan.assignments)) return plan;
  const assignments = { ...plan.assignments };
  delete assignments[tankId];
  return { ...plan, assignments };
}

/** Clear all assignments; locked tanks are preserved unless includeLocked. */
export function clearAll(plan: StowagePlanData, includeLocked: boolean): StowagePlanData {
  const assignments: Record<string, StowageAssignment> = {};
  if (!includeLocked) {
    for (const tankId of plan.locked_tanks) {
      if (plan.assignments[tankId]) assignments[tankId] = plan.assignments[tankId];
    }
  }
  return { ...plan, assignments };
}

export function toggleLock(plan: StowagePlanData, tankId: string): StowagePlanData {
  const locked = plan.locked_tanks.includes(tankId)
    ? plan.locked_tanks.filter((t) => t !== tankId)
    : [...plan.locked_tanks, tankId];
  return { ...plan, locked_tanks: locked };
}

export function toggleExclude(plan: StowagePlanData, tankId: string): StowagePlanData {
  if (plan.excluded_tanks.includes(tankId)) {
    return { ...plan, excluded_tanks: plan.excluded_tanks.filter((t) => t !== tankId) };
  }
  // Excluding a tank also empties it
  return { ...emptyTank(plan, tankId), excluded_tanks: [...plan.excluded_tanks, tankId] };
}

export function removeCargo(plan: StowagePlanData, cargoId: string): StowagePlanData {
  const assignments = Object.fromEntries(
    Object.entries(plan.assignments).filter(([, a]) => a.cargo_id !== cargoId)
  );
  return {
    ...plan,
    cargo_requests: plan.cargo_requests.filter((c) => c.id !== cargoId),
    assignments,
  };
}

/**
 * "Colorize" (desktop hold-button): group cargos by the first 4 characters of
 * the first receiver name and assign one bright colour per group.
 */
const COLORIZE_PALETTE = ["#EF4444", "#3B82F6", "#22C55E", "#EAB308", "#F97316", "#8B5CF6", "#14B8A6"];

export function colorizeByReceiver(cargos: StowageCargo[]): Record<string, string> {
  const groups: Record<string, string[]> = {};
  for (const c of cargos) {
    const key = (c.receivers[0] || "").slice(0, 4).toUpperCase() || c.id;
    (groups[key] = groups[key] || []).push(c.id);
  }
  const map: Record<string, string> = {};
  Object.keys(groups).forEach((key, i) => {
    for (const id of groups[key]) map[id] = COLORIZE_PALETTE[i % COLORIZE_PALETTE.length];
  });
  return map;
}

export function contrastText(hex: string): string {
  const h = (hex || "").replace("#", "");
  if (h.length < 6) return "#000";
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.55 ? "#0f172a" : "#fff";
}
