import { useMemo, useState } from "react";
import type { Ship, StowageCargo, StowagePlanData } from "../types";
import {
  CARGO_COLORS,
  assignCargo,
  cargoById,
  clearAll,
  colorizeByReceiver,
  contrastText,
  emptyTank,
  fillTo977,
  loadedTotal,
  remaining,
  removeCargo,
  swapTanks,
  toggleExclude,
  toggleLock,
} from "../stowage";

const MIME_CARGO = "application/x-cargo-id";
const MIME_TANK = "application/x-tank-id";

function num(value: string): number {
  const n = Number(value.replace(",", "."));
  return Number.isFinite(n) ? n : 0;
}

/* ---------------- cargo legend card ---------------- */

function CargoCard({
  cargo,
  rest,
  color,
  onColor,
}: {
  cargo: StowageCargo;
  rest: number;
  color: string;
  onColor: (c: string) => void;
}) {
  const badge =
    rest <= 0.5 && rest >= -0.5
      ? { text: "✓ Tamamlandı", cls: "done" }
      : rest > 0.5
        ? { text: `${rest.toFixed(1)} m³ kaldı`, cls: "left" }
        : { text: `${(-rest).toFixed(1)} m³ fazla`, cls: "over" };
  return (
    <div
      className="cargo-card"
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData(MIME_CARGO, cargo.id);
        e.dataTransfer.effectAllowed = "copy";
      }}
      style={{ background: color, color: contrastText(color) }}
      title="Bir tankın üzerine sürükleyin"
    >
      <div className="cargo-card-name">{cargo.cargo_type}</div>
      <div className="cargo-card-recv">{cargo.receivers.join(", ") || "Genel"}</div>
      <div className={`cargo-card-badge ${badge.cls}`}>{badge.text}</div>
      <input
        type="color"
        className="cargo-card-color"
        value={cargo.color}
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => onColor(e.target.value)}
        title="Renk değiştir"
      />
    </div>
  );
}

/* ---------------- tank card ---------------- */

function TankPlanCard({
  tankCode,
  capacity,
  plan,
  colorOf,
  onDropCargo,
  onDropTank,
  onEmpty,
  onLock,
  onExclude,
}: {
  tankCode: string;
  capacity: number;
  plan: StowagePlanData;
  colorOf: (cargoId: string) => string;
  onDropCargo: (cargoId: string) => void;
  onDropTank: (sourceTank: string) => void;
  onEmpty: () => void;
  onLock: () => void;
  onExclude: () => void;
}) {
  const [hover, setHover] = useState(false);
  const assignment = plan.assignments[tankCode];
  const cargo = assignment ? cargoById(plan, assignment.cargo_id) : undefined;
  const locked = plan.locked_tanks.includes(tankCode);
  const excluded = plan.excluded_tanks.includes(tankCode);
  const pct = assignment && capacity > 0 ? (assignment.quantity_loaded / capacity) * 100 : 0;
  const color = cargo ? colorOf(cargo.id) : "#e2e8f0";
  const acceptsDrop = !locked && !excluded;

  return (
    <div
      className={`tankp-card ${excluded ? "excluded" : ""} ${locked ? "locked" : ""} ${hover ? "drop-hover" : ""}`}
      data-tank={tankCode}
      draggable={!!assignment && !locked}
      onDragStart={(e) => {
        e.dataTransfer.setData(MIME_TANK, tankCode);
        e.dataTransfer.effectAllowed = "move";
      }}
      onDragOver={(e) => {
        if (!acceptsDrop) return;
        e.preventDefault();
        setHover(true);
      }}
      onDragLeave={() => setHover(false)}
      onDrop={(e) => {
        setHover(false);
        if (!acceptsDrop) return;
        e.preventDefault();
        const cargoId = e.dataTransfer.getData(MIME_CARGO);
        const sourceTank = e.dataTransfer.getData(MIME_TANK);
        if (cargoId) onDropCargo(cargoId);
        else if (sourceTank) onDropTank(sourceTank);
      }}
    >
      <div className="tankp-head">
        <b>{tankCode}</b>
        <span>{capacity.toFixed(0)} m³</span>
      </div>
      {cargo ? (
        <>
          <div className="tankp-badge" style={{ background: color, color: contrastText(color) }}>
            <div>{cargo.cargo_type}</div>
            <div className="tankp-recv">{cargo.receivers.join(", ")}</div>
          </div>
          <div className="tankp-qty">{assignment!.quantity_loaded.toFixed(1)} m³</div>
          <div className="tankp-bar" title={`${pct.toFixed(1)}%`}>
            <div className="tankp-bar-fill" style={{ width: `${Math.min(pct, 100)}%`, background: color }} />
            <span style={{ color: pct > 45 ? contrastText(color) : "#0f172a" }}>{pct.toFixed(1)}%</span>
          </div>
        </>
      ) : (
        <div className="tankp-empty">{excluded ? "Planlama Dışı" : "Boş"}</div>
      )}
      {locked && <div className="tankp-flag lock">🔒 Kilitli</div>}
      {excluded && <div className="tankp-flag excl">⚠ Planlama Dışı</div>}
      <div className="tankp-actions">
        <button title={locked ? "Kilidi kaldır" : "Kilitle"} onClick={onLock}>{locked ? "🔓" : "🔒"}</button>
        <button title={excluded ? "Planlamaya dahil et" : "Planlama dışı bırak"} onClick={onExclude}>⚠</button>
        <button title="Boşalt" onClick={onEmpty} disabled={!assignment || locked}>✕</button>
      </div>
    </div>
  );
}

/* ---------------- main planner ---------------- */

export default function StowagePlannerView({
  ship,
  plan: rawPlan,
  onChange,
  onTransferToUllage,
}: {
  ship: Ship;
  plan: StowagePlanData;
  onChange: (plan: StowagePlanData) => void;
  onTransferToUllage: () => void;
}) {
  const plan = rawPlan;
  const [form, setForm] = useState({ type: "", ton: "", density: "0.8500", receivers: "" });
  const [colorized, setColorized] = useState<Record<string, string> | null>(null);

  const capacities = useMemo(() => {
    const map: Record<string, number> = {};
    ship.tanks.forEach((t) => (map[t.tank_code] = t.capacity_m3));
    return map;
  }, [ship.tanks]);

  const columns = useMemo(() => {
    const groups: Record<number, { key: string; port?: string; stbd?: string }> = {};
    const slop: { key: string; port?: string; stbd?: string } = { key: "slop" };
    for (const t of ship.tanks) {
      const upper = t.tank_code.toUpperCase();
      if (upper.includes("SLOP")) {
        if (upper.replace("SLOP", "").includes("P")) slop.port = t.tank_code;
        else slop.stbd = t.tank_code;
        continue;
      }
      const digits = t.tank_code.replace(/\D/g, "");
      if (!digits) continue;
      const n = parseInt(digits, 10);
      groups[n] = groups[n] || { key: String(n) };
      if (upper.endsWith("S")) groups[n].stbd = t.tank_code;
      else groups[n].port = t.tank_code;
    }
    const sorted = Object.keys(groups).map(Number).sort((a, b) => b - a).map((n) => groups[n]);
    return slop.port || slop.stbd ? [slop, ...sorted] : sorted;
  }, [ship.tanks]);

  const colorOf = (cargoId: string): string =>
    colorized?.[cargoId] ?? (cargoById(plan, cargoId)?.color || "#3B82F6");

  /* ---- cargo management ---- */

  function addCargo() {
    const ton = num(form.ton);
    const density = num(form.density);
    if (!form.type.trim() || ton <= 0 || density <= 0) return;
    const cargo: StowageCargo = {
      id: crypto.randomUUID(),
      cargo_type: form.type.trim(),
      quantity: ton / density,
      density,
      receivers: form.receivers.split(",").map((r) => r.trim()).filter(Boolean),
      color: CARGO_COLORS[plan.cargo_requests.length % CARGO_COLORS.length],
    };
    onChange({ ...plan, cargo_requests: [...plan.cargo_requests, cargo] });
    setForm({ type: "", ton: "", density: form.density, receivers: "" });
  }

  function updateCargo(id: string, patch: Partial<StowageCargo>) {
    onChange({
      ...plan,
      cargo_requests: plan.cargo_requests.map((c) => (c.id === id ? { ...c, ...patch } : c)),
    });
  }

  /* ---- toolbar actions ---- */

  function doFill977() {
    const [next, changed] = fillTo977(plan, capacities);
    if (changed === 0) {
      alert("Doldurulacak uygun tank yok (SLOP ve planlama dışı tanklar atlanır).");
      return;
    }
    if (confirm(`${changed} tank %97.7 seviyesine doldurulacak. Devam edilsin mi?`)) onChange(next);
  }

  function doClearAll() {
    const lockedCount = plan.locked_tanks.filter((t) => plan.assignments[t]).length;
    const msg =
      lockedCount > 0
        ? `Tüm tank atamaları temizlensin mi?\n(${lockedCount} kilitli tank korunacak — boşaltmak için önce kilidini kaldırın.)`
        : "Tüm tank atamaları temizlensin mi?";
    if (confirm(msg)) onChange(clearAll(plan, false));
  }

  /* ---- plan viewer figures ---- */

  const totalCapacity = ship.tanks
    .filter((t) => !plan.excluded_tanks.includes(t.tank_code))
    .reduce((s, t) => s + t.capacity_m3, 0);
  const totalLoaded = Object.values(plan.assignments).reduce((s, a) => s + a.quantity_loaded, 0);
  const totalRequested = plan.cargo_requests.reduce((s, c) => s + c.quantity, 0);

  return (
    <div className="planner">
      {/* toolbar */}
      <div className="planner-toolbar">
        <button className="small" onClick={doFill977} title="Dolu tankları %97.7'ye tamamla (SLOP hariç)">%97.7</button>
        <button
          className="small"
          onMouseDown={() => setColorized(colorizeByReceiver(plan.cargo_requests))}
          onMouseUp={() => setColorized(null)}
          onMouseLeave={() => setColorized(null)}
          title="Basılı tutun: parcelleri alıcıya göre grupla ve renklendir"
        >
          🎨 Colorize
        </button>
        <button className="small" onClick={doClearAll} title="Tüm tankları boşalt (Ctrl+E)">Tümünü Boşalt</button>
        <span className="planner-spacer" />
        <button className="primary small" onClick={onTransferToUllage} title="Planı Ullage sekmesine parcel olarak aktar">
          ➡️ Ullage'a Aktar
        </button>
      </div>

      {/* cargo legend */}
      <div className="cargo-legend">
        {plan.cargo_requests.length === 0 && (
          <div className="empty" style={{ margin: 0, flex: 1 }}>
            Aşağıdaki "Charterer Order" tablosundan kargo ekleyin, sonra kartları tanklara sürükleyin.
          </div>
        )}
        {plan.cargo_requests.map((c) => (
          <CargoCard
            key={c.id}
            cargo={c}
            rest={remaining(plan, c)}
            color={colorOf(c.id)}
            onColor={(color) => updateCargo(c.id, { color })}
          />
        ))}
      </div>

      {/* ship schematic */}
      <div className="stow-scroll">
        <div className="stow-strip planner-strip">
          <div className="stow-stern">◀ STERN</div>
          {columns.map((col) => (
            <div key={col.key} className="planner-column">
              {(["port", "stbd"] as const).map((side) => {
                const code = col[side];
                return code ? (
                  <TankPlanCard
                    key={code}
                    tankCode={code}
                    capacity={capacities[code] || 0}
                    plan={plan}
                    colorOf={colorOf}
                    onDropCargo={(cargoId) => onChange(assignCargo(plan, capacities, cargoId, code))}
                    onDropTank={(src) => onChange(swapTanks(plan, capacities, src, code))}
                    onEmpty={() => onChange(emptyTank(plan, code))}
                    onLock={() => onChange(toggleLock(plan, code))}
                    onExclude={() => onChange(toggleExclude(plan, code))}
                  />
                ) : (
                  <div key={side} className="tankp-card ghost" />
                );
              })}
            </div>
          ))}
          <div className="stow-bow">BOW ▶</div>
        </div>
      </div>

      <div className="planner-bottom">
        {/* charterer order */}
        <div className="planner-panel">
          <h4>Charterer Order</h4>
          <table className="grid parcels">
            <thead>
              <tr><th>Yük Tipi</th><th>Ton</th><th>Density</th><th>Hacim (m³)</th><th>Alıcı(lar)</th><th></th></tr>
            </thead>
            <tbody>
              {plan.cargo_requests.map((c) => (
                <tr key={c.id}>
                  <td><input value={c.cargo_type} onChange={(e) => updateCargo(c.id, { cargo_type: e.target.value })} /></td>
                  <td>
                    <input
                      inputMode="decimal"
                      value={(c.quantity * c.density).toFixed(2)}
                      onChange={(e) => {
                        const ton = num(e.target.value);
                        if (ton > 0 && c.density > 0) updateCargo(c.id, { quantity: ton / c.density });
                      }}
                    />
                  </td>
                  <td>
                    <input
                      inputMode="decimal"
                      value={c.density}
                      onChange={(e) => {
                        const d = num(e.target.value);
                        if (d > 0) {
                          const ton = c.quantity * c.density;
                          updateCargo(c.id, { density: d, quantity: ton / d });
                        }
                      }}
                    />
                  </td>
                  <td className="calc">{c.quantity.toFixed(3)}</td>
                  <td>
                    <input
                      value={c.receivers.join(", ")}
                      onChange={(e) =>
                        updateCargo(c.id, {
                          receivers: e.target.value.split(",").map((r) => r.trim()).filter(Boolean),
                        })
                      }
                    />
                  </td>
                  <td>
                    <button
                      className="danger small"
                      onClick={() => confirm(`"${c.cargo_type}" ve tüm atamaları silinsin mi?`) && onChange(removeCargo(plan, c.id))}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
              <tr className="cargo-add-row">
                <td><input placeholder="Yük tipi (örn: Gasoil)" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} /></td>
                <td><input placeholder="ton" inputMode="decimal" value={form.ton} onChange={(e) => setForm({ ...form, ton: e.target.value })} /></td>
                <td><input inputMode="decimal" value={form.density} onChange={(e) => setForm({ ...form, density: e.target.value })} /></td>
                <td className="calc">
                  {num(form.ton) > 0 && num(form.density) > 0 ? (num(form.ton) / num(form.density)).toFixed(3) : "—"}
                </td>
                <td><input placeholder="Alıcı, Alıcı2" value={form.receivers} onChange={(e) => setForm({ ...form, receivers: e.target.value })} /></td>
                <td><button className="small primary" onClick={addCargo}>Ekle</button></td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* loading plan viewer */}
        <div className="planner-panel">
          <h4>Loading Plan</h4>
          <table className="grid summary">
            <thead>
              <tr><th>Yük</th><th>Alıcı</th><th>İstenen</th><th>Yüklenen</th><th>Fark</th><th>Durum</th></tr>
            </thead>
            <tbody>
              {plan.cargo_requests.map((c) => {
                const loaded = loadedTotal(plan, c.id);
                const diff = loaded - c.quantity;
                const status =
                  Math.abs(diff) < 0.01
                    ? { text: "✓ Tamamlandı", cls: "st-done" }
                    : diff < 0
                      ? { text: `Eksik ${((-diff / c.quantity) * 100).toFixed(1)}%`, cls: "st-under" }
                      : { text: `Fazla ${((diff / c.quantity) * 100).toFixed(1)}%`, cls: "st-over" };
                return (
                  <tr key={c.id}>
                    <td><span className="swatch" style={{ background: colorOf(c.id) }} /> {c.cargo_type}</td>
                    <td>{c.receivers.join(", ")}</td>
                    <td className="calc">{c.quantity.toFixed(3)}</td>
                    <td className="calc">{loaded.toFixed(3)}</td>
                    <td className="calc">{diff.toFixed(3)}</td>
                    <td className={`center ${status.cls}`}>{status.text}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="hint planner-summary">
            Kapasite: <b>{totalCapacity.toFixed(0)} m³</b> · Yüklenen: <b>{totalLoaded.toFixed(1)} m³</b> · Oran:{" "}
            <b>{totalCapacity > 0 ? ((totalLoaded / totalCapacity) * 100).toFixed(1) : "0"}%</b> · Talep Karşılama:{" "}
            <b>{totalRequested > 0 ? ((totalLoaded / totalRequested) * 100).toFixed(1) : "0"}%</b>
          </p>
        </div>
      </div>
    </div>
  );
}
