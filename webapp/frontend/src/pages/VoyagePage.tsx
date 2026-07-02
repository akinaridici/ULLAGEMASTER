import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, downloadFile, get, post, put } from "../api";
import DiscrepancyView from "../components/DiscrepancyView";
import StowagePlanView from "../components/StowagePlanView";
import StowagePlannerView from "../components/StowagePlannerView";
import { emptyPlan, normalizePlan } from "../stowage";
import type { CalcResponse, Parcel, Reading, Ship, StowageCargo, StowagePlanData, Voyage, VoyageData } from "../types";

const PARCEL_COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6"];

function emptyReading(): Reading {
  return { parcel_id: "", ullage: null, fill_percent: null, temp_celsius: null, density_vac: null };
}

function fmt(v: number | null | undefined, digits: number): string {
  return v === null || v === undefined ? "" : v.toFixed(digits);
}

function num(value: string): number | null {
  if (value.trim() === "") return null;
  const n = Number(value.replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

const WARNING_LABELS: Record<string, string> = {
  high_high: "≥98% STOP",
  high: ">95%",
  low: "<65% slosh",
};

export default function VoyagePage({
  shipId,
  voyageId: initialVoyageId,
  onBack,
}: {
  shipId: number;
  voyageId: number | null;
  onBack: () => void;
}) {
  const [ship, setShip] = useState<Ship | null>(null);
  const [voyageId, setVoyageId] = useState<number | null>(initialVoyageId);
  const [voyage, setVoyage] = useState<VoyageData | null>(null);
  const [calc, setCalc] = useState<CalcResponse | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [batch, setBatch] = useState({ ullage: "", fill: "", temp: "" });
  const [tab, setTab] = useState<"planner" | "grid" | "stowage" | "disc">("grid");

  // ---- load ----
  useEffect(() => {
    (async () => {
      try {
        const s = await get<Ship>(`/api/ships/${shipId}`);
        setShip(s);
        if (initialVoyageId) {
          const v = await get<Voyage>(`/api/ships/${shipId}/voyages/${initialVoyageId}`);
          setVoyage({ ...v, stowage_plan: normalizePlan(v.stowage_plan) });
        } else {
          setVoyage({
            voyage_number: "",
            date: new Date().toISOString().slice(0, 10),
            port: "",
            terminal: "",
            vef: s.default_vef,
            draft_aft: 0,
            draft_fwd: 0,
            chief_officer: s.chief_officer,
            master: s.master,
            notes: "",
            parcels: [],
            readings: {},
            stowage_plan: emptyPlan(),
          });
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Connection error");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shipId, initialVoyageId]);

  // ---- debounced calculation ----
  const calcSeq = useRef(0);
  useEffect(() => {
    if (!voyage) return;
    const seq = ++calcSeq.current;
    const timer = setTimeout(async () => {
      try {
        const result = await post<CalcResponse>(`/api/ships/${shipId}/calculate`, {
          vef: voyage.vef,
          draft_aft: voyage.draft_aft,
          draft_fwd: voyage.draft_fwd,
          parcels: voyage.parcels,
          readings: voyage.readings,
        });
        if (seq === calcSeq.current) setCalc(result);
      } catch (err) {
        if (seq === calcSeq.current) setError(err instanceof ApiError ? err.message : "Calculation error");
      }
    }, 350);
    return () => clearTimeout(timer);
  }, [shipId, voyage]);

  const update = useCallback((patch: Partial<VoyageData>) => {
    setVoyage((v) => (v ? { ...v, ...patch } : v));
    setDirty(true);
    setError("");
  }, []);

  function updateReading(tankCode: string, patch: Partial<Reading>) {
    setVoyage((v) => {
      if (!v) return v;
      const current = v.readings[tankCode] || emptyReading();
      const next = { ...current, ...patch };
      // Dual input: entering one clears the other (desktop behaviour)
      if ("ullage" in patch && patch.ullage !== null) next.fill_percent = null;
      if ("fill_percent" in patch && patch.fill_percent !== null) next.ullage = null;
      return { ...v, readings: { ...v.readings, [tankCode]: next } };
    });
    setDirty(true);
  }

  function applyBatch() {
    if (!ship || !voyage) return;
    const ullage = num(batch.ullage);
    const fill = num(batch.fill);
    const temp = num(batch.temp);
    setVoyage((v) => {
      if (!v) return v;
      const readings = { ...v.readings };
      for (const t of ship.tanks) {
        const r = { ...(readings[t.tank_code] || emptyReading()) };
        if (ullage !== null) { r.ullage = ullage; r.fill_percent = null; }
        else if (fill !== null) { r.fill_percent = fill; r.ullage = null; }
        if (temp !== null) r.temp_celsius = temp;
        readings[t.tank_code] = r;
      }
      return { ...v, readings };
    });
    setDirty(true);
    setBatch({ ullage: "", fill: "", temp: "" });
  }

  // ---- parcels ----
  function addParcel(slop = false) {
    if (!voyage) return;
    const cargoIds = voyage.parcels.filter((p) => p.id !== "0").length;
    const parcel: Parcel = slop
      ? { id: "0", name: "SLOP", receiver: "", density_vac: ship?.slop_density ?? 0.9, color: "#6B7280", bl_loading: 0, ship_figure_loading: 0, outturn_figure: 0 }
      : {
          id: String(cargoIds + 1),
          name: "",
          receiver: "",
          density_vac: 0,
          color: PARCEL_COLORS[cargoIds % PARCEL_COLORS.length],
          bl_loading: 0,
          ship_figure_loading: 0,
          outturn_figure: 0,
        };
    if (voyage.parcels.some((p) => p.id === parcel.id)) return;
    update({ parcels: [...voyage.parcels, parcel] });
  }

  function updateParcel(id: string, patch: Partial<Parcel>) {
    if (!voyage) return;
    update({ parcels: voyage.parcels.map((p) => (p.id === id ? { ...p, ...patch } : p)) });
  }

  function removeParcel(id: string) {
    if (!voyage) return;
    const readings = Object.fromEntries(
      Object.entries(voyage.readings).map(([k, r]) => [k, r.parcel_id === id ? { ...r, parcel_id: "" } : r])
    );
    update({ parcels: voyage.parcels.filter((p) => p.id !== id), readings });
  }

  // ---- stowage transfers (desktop Ctrl+Shift+T / Ctrl+Shift+U) ----

  function transferStowageToUllage() {
    if (!voyage) return;
    const plan = voyage.stowage_plan;
    if (plan.cargo_requests.length === 0) {
      alert("Önce stowage planına kargo ekleyin.");
      return;
    }
    if (
      !confirm(
        "Bu işlem Ullage sekmesindeki mevcut parselleri değiştirecek.\nTank atamaları da uygulanacak (SLOP dışı tanklar %97.7 / 20°C başlar).\n\nDevam edilsin mi?"
      )
    )
      return;

    const cargoToParcel: Record<string, string> = {};
    let nextId = 1;
    const parcels: Parcel[] = plan.cargo_requests.map((c) => {
      const isSlop = c.cargo_type.toLowerCase().includes("slop");
      const pid = isSlop ? "0" : String(nextId++);
      cargoToParcel[c.id] = pid;
      return {
        id: pid,
        name: c.cargo_type,
        receiver: c.receivers.join(", ") || (isSlop ? "" : "Genel"),
        density_vac: c.density,
        color: isSlop ? "#9CA3AF" : c.color,
        bl_loading: 0,
        ship_figure_loading: 0,
        outturn_figure: 0,
      };
    });

    const readings: Record<string, Reading> = { ...voyage.readings };
    for (const [tankId, a] of Object.entries(plan.assignments)) {
      const cargo = plan.cargo_requests.find((c) => c.id === a.cargo_id);
      const pid = cargoToParcel[a.cargo_id];
      if (!cargo || !pid) continue;
      const prev = readings[tankId] || emptyReading();
      if (cargo.cargo_type.toLowerCase().includes("slop")) {
        // SLOP: keep existing temp/ullage untouched (desktop behaviour)
        readings[tankId] = { ...prev, parcel_id: pid, density_vac: cargo.density };
      } else {
        readings[tankId] = {
          ...prev,
          parcel_id: pid,
          density_vac: cargo.density,
          temp_celsius: 20.0,
          fill_percent: 97.7,
          ullage: null,
        };
      }
    }
    update({ parcels, readings });
    setTab("grid");
  }

  function transferUllageToStowage() {
    if (!voyage || !calc) return;
    if (voyage.parcels.length === 0) {
      alert("Önce Ullage sekmesinde parsel tanımlayın.");
      return;
    }
    const assignedRows = calc.rows.filter((r) => r.parcel_id);
    if (assignedRows.length === 0) {
      alert("Hiçbir tanka parsel atanmamış.");
      return;
    }
    if (!confirm("Bu işlem mevcut stowage planını değiştirecek (GOV değerleri plana yazılır). Devam edilsin mi?")) return;

    const cargos: StowageCargo[] = [];
    const byParcel: Record<string, StowageCargo> = {};
    for (const p of voyage.parcels) {
      const rows = assignedRows.filter((r) => r.parcel_id === p.id);
      if (rows.length === 0) continue;
      const totalGov = rows.reduce((s, r) => s + (r.gov || 0), 0);
      const cargo: StowageCargo =
        p.id === "0"
          ? { id: "p0", cargo_type: "SLOP", quantity: totalGov, density: 0.85, receivers: [], color: "#9CA3AF" }
          : {
              id: `p${p.id}`,
              cargo_type: p.name || `Parcel ${p.id}`,
              quantity: totalGov,
              density: p.density_vac || 0.85,
              receivers: p.receiver ? [p.receiver] : [],
              color: p.color,
            };
      byParcel[p.id] = cargo;
      cargos.push(cargo);
    }
    const assignments: StowagePlanData["assignments"] = {};
    for (const r of assignedRows) {
      const cargo = byParcel[r.parcel_id];
      if (cargo) assignments[r.tank_id] = { cargo_id: cargo.id, quantity_loaded: r.gov || 0 };
    }
    update({ stowage_plan: { ...voyage.stowage_plan, cargo_requests: cargos, assignments } });
    setTab("planner");
  }

  // ---- save & export ----
  async function save() {
    if (!voyage) return;
    setSaving(true);
    setError("");
    try {
      if (voyageId) {
        await put(`/api/ships/${shipId}/voyages/${voyageId}`, voyage);
      } else {
        const created = await post<Voyage>(`/api/ships/${shipId}/voyages`, voyage);
        setVoyageId(created.id);
      }
      setDirty(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function exportAs(fmt: "xlsx" | "pdf" | "stowage") {
    if (!voyageId) return;
    const no = voyage?.voyage_number.replace(/[^\w-]/g, "_") || "voyage";
    const prefix = fmt === "stowage" ? "stowage_plan" : "ullage_report";
    const ext = fmt === "stowage" ? "pdf" : fmt;
    await downloadFile(`/api/ships/${shipId}/voyages/${voyageId}/export/${fmt}`, `${prefix}_${no}.${ext}`);
  }

  async function exportProtest(operation: "loading" | "discharging", parcelId: string | null) {
    if (!voyageId) return;
    const no = voyage?.voyage_number.replace(/[^\w-]/g, "_") || "voyage";
    const qs = `operation=${operation}${parcelId ? `&parcel_id=${encodeURIComponent(parcelId)}` : ""}`;
    try {
      await downloadFile(
        `/api/ships/${shipId}/voyages/${voyageId}/export/protest?${qs}`,
        `protest_${operation}_${no}_${parcelId || "all"}.pdf`
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Protest export failed");
    }
  }

  const rowsByTank = useMemo(() => {
    const map: Record<string, CalcResponse["rows"][number]> = {};
    calc?.rows.forEach((r) => (map[r.tank_id] = r));
    return map;
  }, [calc]);

  const parcelById = useMemo(() => {
    const map: Record<string, Parcel> = {};
    voyage?.parcels.forEach((p) => (map[p.id] = p));
    return map;
  }, [voyage?.parcels]);

  if (!ship || !voyage) {
    return <div className="page">{error ? <div className="error">{error}</div> : "Loading..."}</div>;
  }

  const trim = voyage.draft_aft - voyage.draft_fwd;

  return (
    <div className="page wide">
      <div className="page-head">
        <h2>
          <a onClick={onBack}>{ship.name}</a> / Voyage {voyage.voyage_number || "(new)"}
          {dirty && <span className="dirty"> ●</span>}
        </h2>
        <div className="btn-row">
          <button className="primary" onClick={save} disabled={saving}>
            {saving ? "Saving..." : voyageId ? "Save" : "Save voyage"}
          </button>
          <button onClick={() => exportAs("xlsx")} disabled={!voyageId || dirty} title={dirty ? "Save first" : ""}>
            Excel
          </button>
          <button onClick={() => exportAs("pdf")} disabled={!voyageId || dirty} title={dirty ? "Save first" : ""}>
            PDF
          </button>
          <button onClick={() => exportAs("stowage")} disabled={!voyageId || dirty} title={dirty ? "Save first" : ""}>
            Stowage PDF
          </button>
        </div>
      </div>
      {error && <div className="error">{error}</div>}

      {/* Header */}
      <div className="header-form">
        <label>Voyage No<input value={voyage.voyage_number} onChange={(e) => update({ voyage_number: e.target.value })} /></label>
        <label>Date<input type="date" value={voyage.date} onChange={(e) => update({ date: e.target.value })} /></label>
        <label>Port<input value={voyage.port} onChange={(e) => update({ port: e.target.value })} /></label>
        <label>Terminal<input value={voyage.terminal} onChange={(e) => update({ terminal: e.target.value })} /></label>
        <label>V.E.F.<input type="number" step="0.00001" value={voyage.vef} onChange={(e) => update({ vef: num(e.target.value) ?? 1 })} /></label>
        <label>Draft AFT<input type="number" step="0.01" value={voyage.draft_aft} onChange={(e) => update({ draft_aft: num(e.target.value) ?? 0 })} /></label>
        <label>Draft FWD<input type="number" step="0.01" value={voyage.draft_fwd} onChange={(e) => update({ draft_fwd: num(e.target.value) ?? 0 })} /></label>
        <label>Trim<input readOnly className="calc" value={trim.toFixed(2)} /></label>
      </div>

      {/* Parcels */}
      <div className="section-head">
        <h3>Parcels</h3>
        <div className="btn-row">
          <button className="small" onClick={() => addParcel(false)}>+ Parcel</button>
          <button className="small" onClick={() => addParcel(true)} disabled={voyage.parcels.some((p) => p.id === "0")}>
            + SLOP
          </button>
        </div>
      </div>
      {voyage.parcels.length > 0 && (
        <table className="grid parcels">
          <thead>
            <tr><th>#</th><th>Grade</th><th>Receiver</th><th>Density (Vac)</th><th>Color</th><th>B/L (MT)</th><th></th></tr>
          </thead>
          <tbody>
            {voyage.parcels.map((p) => (
              <tr key={p.id}>
                <td className="center"><b>{p.id === "0" ? "SLOP" : p.id}</b></td>
                <td><input value={p.name} onChange={(e) => updateParcel(p.id, { name: e.target.value })} /></td>
                <td><input value={p.receiver} onChange={(e) => updateParcel(p.id, { receiver: e.target.value })} /></td>
                <td><input type="number" step="0.0001" value={p.density_vac || ""} onChange={(e) => updateParcel(p.id, { density_vac: num(e.target.value) ?? 0 })} /></td>
                <td className="center"><input type="color" value={p.color} onChange={(e) => updateParcel(p.id, { color: e.target.value })} /></td>
                <td><input type="number" step="0.001" value={p.bl_loading || ""} onChange={(e) => updateParcel(p.id, { bl_loading: num(e.target.value) ?? 0 })} /></td>
                <td><button className="danger small" onClick={() => removeParcel(p.id)}>✕</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Tank grid / stowage planner / ship view */}
      <div className="section-head">
        <h3>Tanks</h3>
        <div className="tabs">
          <button className={`tab ${tab === "planner" ? "active" : ""}`} onClick={() => setTab("planner")}>
            📋 Stowage Planner
          </button>
          <button className={`tab ${tab === "grid" ? "active" : ""}`} onClick={() => setTab("grid")}>
            📊 Ullage Grid
          </button>
          <button className={`tab ${tab === "stowage" ? "active" : ""}`} onClick={() => setTab("stowage")}>
            🚢 Ship View
          </button>
          <button className={`tab ${tab === "disc" ? "active" : ""}`} onClick={() => setTab("disc")}>
            ⚖️ Discrepancy
          </button>
        </div>
        {tab === "grid" && (
          <button className="small" onClick={transferUllageToStowage} title="Parcel atamalarını ve GOV değerlerini stowage planına aktar">
            ⬅️ Stowage'a Aktar
          </button>
        )}
      </div>
      {tab === "planner" && (
        <StowagePlannerView
          ship={ship}
          plan={voyage.stowage_plan}
          onChange={(stowage_plan) => update({ stowage_plan })}
          onTransferToUllage={transferStowageToUllage}
        />
      )}
      {tab === "stowage" && <StowagePlanView calc={calc} parcels={voyage.parcels} />}
      {tab === "disc" && (
        <DiscrepancyView
          parcels={voyage.parcels}
          calc={calc}
          vef={voyage.vef}
          canProtest={!!voyageId && !dirty}
          onUpdateParcel={updateParcel}
          onProtest={exportProtest}
        />
      )}
      <div className="grid-scroll" style={tab !== "grid" ? { display: "none" } : undefined}>
        <table className="grid tanks">
          <thead>
            <tr>
              <th>Tank</th><th>Parcel</th>
              <th className="input-col">Ullage (cm)</th><th className="input-col">Fill %</th>
              <th>Trim Corr</th><th>Corr Ullage</th><th>TOV (m³)</th>
              <th className="input-col">Temp °C</th><th>Therm</th><th>GOV (m³)</th>
              <th>Dens Vac</th><th>Dens Air</th><th>VCF</th>
              <th>GSV (m³)</th><th>MT (Air)</th><th>MT (Vac)</th><th>Status</th>
            </tr>
            <tr className="batch-row">
              <td colSpan={2} className="right">Set all →</td>
              <td><input placeholder="all" value={batch.ullage} onChange={(e) => setBatch({ ...batch, ullage: e.target.value, fill: "" })} /></td>
              <td><input placeholder="all" value={batch.fill} onChange={(e) => setBatch({ ...batch, fill: e.target.value, ullage: "" })} /></td>
              <td colSpan={3} />
              <td><input placeholder="all" value={batch.temp} onChange={(e) => setBatch({ ...batch, temp: e.target.value })} /></td>
              <td colSpan={8}><button className="small" onClick={applyBatch}>Apply to all tanks</button></td>
            </tr>
          </thead>
          <tbody>
            {ship.tanks.map((t) => {
              const reading = voyage.readings[t.tank_code] || emptyReading();
              const row = rowsByTank[t.tank_code];
              const parcel = parcelById[reading.parcel_id];
              const warning = row?.warning || "normal";
              return (
                <tr key={t.tank_code} style={parcel ? { boxShadow: `inset 4px 0 0 ${parcel.color}` } : undefined}>
                  <td className="center"><b>{t.tank_code}</b></td>
                  <td>
                    <select value={reading.parcel_id} onChange={(e) => updateReading(t.tank_code, { parcel_id: e.target.value })}>
                      <option value="">—</option>
                      {voyage.parcels.map((p) => (
                        <option key={p.id} value={p.id}>{p.id === "0" ? "SLOP" : `${p.id} ${p.name}`}</option>
                      ))}
                    </select>
                  </td>
                  <td className="input-col">
                    <input inputMode="decimal" value={reading.ullage ?? ""} onChange={(e) => updateReading(t.tank_code, { ullage: num(e.target.value) })} />
                  </td>
                  <td className={`input-col warn-${warning}`}>
                    <input inputMode="decimal" value={reading.fill_percent ?? fmt(row?.fill_percent, 1)} onChange={(e) => updateReading(t.tank_code, { fill_percent: num(e.target.value) })} />
                  </td>
                  <td className="calc">{fmt(row?.trim_correction, 1)}</td>
                  <td className="calc">{fmt(row?.corrected_ullage, 1)}</td>
                  <td className="calc">{fmt(row?.tov, 3)}</td>
                  <td className="input-col">
                    <input inputMode="decimal" value={reading.temp_celsius ?? ""} onChange={(e) => updateReading(t.tank_code, { temp_celsius: num(e.target.value) })} />
                  </td>
                  <td className="calc">{fmt(row?.therm_corr, 6)}</td>
                  <td className="calc">{fmt(row?.gov, 3)}</td>
                  <td className="calc">{fmt(row?.density_vac, 4)}</td>
                  <td className="calc">{fmt(row?.density_air, 4)}</td>
                  <td className="calc">{fmt(row?.vcf, 5)}</td>
                  <td className="calc"><b>{fmt(row?.gsv, 3)}</b></td>
                  <td className="calc"><b>{fmt(row?.mt_air, 3)}</b></td>
                  <td className="calc">{fmt(row?.mt_vac, 3)}</td>
                  <td className={`status warn-${warning}`}>
                    {row?.error === "no_ullage_table" ? "no table" : row?.error ? "range!" : WARNING_LABELS[warning] || ""}
                  </td>
                </tr>
              );
            })}
          </tbody>
          {calc && (
            <tfoot>
              <tr>
                <td colSpan={13} className="right"><b>TOTALS (excl. SLOP)</b></td>
                <td className="calc"><b>{calc.totals.gsv.toFixed(3)}</b></td>
                <td className="calc"><b>{calc.totals.mt_air.toFixed(3)}</b></td>
                <td colSpan={2} />
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      {/* Parcel summary / discrepancy */}
      {calc && calc.parcels.length > 0 && (
        <>
          <h3>Parcel Summary &amp; Discrepancy</h3>
          <table className="grid summary">
            <thead>
              <tr>
                <th>Parcel</th><th>Receiver</th><th>GSV (m³)</th><th>MT (Air)</th>
                <th>Ship w/ VEF</th><th>B/L (MT)</th><th>Diff (MT)</th><th>Diff ‰</th>
              </tr>
            </thead>
            <tbody>
              {calc.parcels.map((p) => (
                <tr key={p.parcel_id}>
                  <td><span className="swatch" style={{ background: p.color }} /> {p.parcel_id} {p.name}</td>
                  <td>{p.receiver}</td>
                  <td className="calc">{p.gsv.toFixed(3)}</td>
                  <td className="calc">{p.mt_air.toFixed(3)}</td>
                  <td className="calc">{p.ship_with_vef.toFixed(3)}</td>
                  <td className="calc">{p.bl_figure.toFixed(3)}</td>
                  <td className="calc">{p.diff_with_vef.toFixed(3)}</td>
                  <td className={`calc ${Math.abs(p.diff_permille_with_vef) > 3 ? "warn-high_high" : ""}`}>
                    {p.diff_permille_with_vef.toFixed(3)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <label className="notes">
        Notes
        <textarea maxLength={1000} value={voyage.notes} onChange={(e) => update({ notes: e.target.value })} />
      </label>
    </div>
  );
}
