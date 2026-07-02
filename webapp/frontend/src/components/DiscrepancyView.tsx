import type { CalcResponse, Parcel, ParcelSummary } from "../types";

function num(value: string): number {
  const n = Number(value.replace(",", "."));
  return Number.isFinite(n) ? n : 0;
}

/** ‰ colour thresholds (desktop): |v|≥3 red, 2≤|v|<3 orange, else green/neutral. */
function permilleClass(v: number, greenOk: boolean): string {
  const a = Math.abs(v);
  if (a >= 3) return "pm-red";
  if (a >= 2) return "pm-orange";
  return greenOk ? "pm-green" : "";
}

function Row({
  n,
  label,
  value,
  bold,
  cls,
  input,
}: {
  n: number;
  label: string;
  value?: number;
  bold?: boolean;
  cls?: string;
  input?: { value: number; onChange: (v: number) => void };
}) {
  return (
    <div className="disc-row">
      <span className="disc-label">{n}. {label}</span>
      {input ? (
        <input
          inputMode="decimal"
          value={input.value || ""}
          placeholder="0.000"
          onChange={(e) => input.onChange(num(e.target.value))}
        />
      ) : (
        <span className={`disc-value ${bold ? "bold" : ""} ${cls || ""}`}>
          {(value ?? 0).toFixed(3)}
        </span>
      )}
    </div>
  );
}

function LoadingCard({
  parcel,
  summary,
  onUpdate,
  onProtest,
  canProtest,
}: {
  parcel: Parcel;
  summary?: ParcelSummary;
  onUpdate: (patch: Partial<Parcel>) => void;
  onProtest: () => void;
  canProtest: boolean;
}) {
  const s = summary;
  return (
    <div className="disc-card">
      <div className="disc-head" style={{ background: parcel.color }}>
        <span>{parcel.id} {parcel.name} {parcel.receiver && `(${parcel.receiver})`}</span>
      </div>
      <Row n={1} label="B/L Figure" input={{ value: parcel.bl_loading, onChange: (v) => onUpdate({ bl_loading: v }) }} />
      <Row n={2} label="Ship Figure W/O VEF" value={s?.mt_air} />
      <Row n={3} label="Quantity Difference W/O VEF" value={s?.diff_wo_vef} />
      <Row n={4} label="Difference W/O VEF ‰" value={s?.diff_permille_wo_vef} bold cls={permilleClass(s?.diff_permille_wo_vef ?? 0, false)} />
      <Row n={5} label="Ship Figure with VEF" value={s?.ship_with_vef} />
      <Row n={6} label="Quantity Difference with VEF" value={s?.diff_with_vef} />
      <Row n={7} label="Difference with VEF ‰" value={s?.diff_permille_with_vef} bold cls={permilleClass(s?.diff_permille_with_vef ?? 0, false)} />
      <button className="small disc-protest" onClick={onProtest} disabled={!canProtest} title={canProtest ? "" : "Önce seferi kaydedin"}>
        📄 Protest
      </button>
    </div>
  );
}

function DischargingCard({
  parcel,
  summary,
  vef,
  onUpdate,
  onProtest,
  canProtest,
}: {
  parcel: Parcel;
  summary?: ParcelSummary;
  vef: number;
  onUpdate: (patch: Partial<Parcel>) => void;
  onProtest: () => void;
  canProtest: boolean;
}) {
  const bl = parcel.bl_loading || 0;
  const arrival = summary?.mt_air ?? 0;
  const arrivalVef = vef ? arrival / vef : arrival;
  const transitLoss = arrival - (parcel.ship_figure_loading || 0);
  const outturn = parcel.outturn_figure || 0;
  const pm = (a: number, b: number) => (b ? ((a - b) / b) * 1000 : 0);
  return (
    <div className="disc-card">
      <div className="disc-head" style={{ background: parcel.color }}>
        <span>{parcel.id} {parcel.name} {parcel.receiver && `(${parcel.receiver})`}</span>
      </div>
      <Row n={1} label="B/L Figure" value={bl} />
      <Row n={2} label="Ship Figure Loading Port" input={{ value: parcel.ship_figure_loading, onChange: (v) => onUpdate({ ship_figure_loading: v }) }} />
      <Row n={3} label="Ship Arrival Figure" value={arrival} />
      <Row n={4} label="Ship Arrival with VEF" value={arrivalVef} />
      <Row n={5} label="Transit Loss" value={transitLoss} />
      <Row n={6} label="Arrival-BL diff W/O VEF ‰" value={pm(arrival, bl)} bold cls={permilleClass(pm(arrival, bl), true)} />
      <Row n={7} label="Arrival-BL diff VEF ‰" value={pm(arrivalVef, bl)} bold cls={permilleClass(pm(arrivalVef, bl), true)} />
      <Row n={8} label="OUTTURN FIGURE" input={{ value: parcel.outturn_figure, onChange: (v) => onUpdate({ outturn_figure: v }) }} />
      <Row n={9} label="OUTTURN-BL DIFF" value={outturn - bl} />
      <Row n={10} label="OUTTURN-BL DIFF ‰" value={pm(outturn, bl)} bold cls={permilleClass(pm(outturn, bl), true)} />
      <Row n={11} label="OUTTURN-SHIP ARRIVAL DIFF" value={outturn - arrivalVef} />
      <Row n={12} label="OUTTURN-ARRIVAL DIFF ‰" value={pm(outturn, arrivalVef)} bold cls={permilleClass(pm(outturn, arrivalVef), true)} />
      <button className="small disc-protest" onClick={onProtest} disabled={!canProtest} title={canProtest ? "" : "Önce seferi kaydedin"}>
        📄 Protest
      </button>
    </div>
  );
}

export default function DiscrepancyView({
  parcels,
  calc,
  vef,
  canProtest,
  onUpdateParcel,
  onProtest,
}: {
  parcels: Parcel[];
  calc: CalcResponse | null;
  vef: number;
  canProtest: boolean;
  onUpdateParcel: (id: string, patch: Partial<Parcel>) => void;
  onProtest: (operation: "loading" | "discharging", parcelId: string | null) => void;
}) {
  const cargoParcels = parcels.filter((p) => p.id !== "0");
  const summaryOf = (pid: string) => calc?.parcels.find((s) => s.parcel_id === pid);

  if (cargoParcels.length === 0) {
    return <div className="empty">Ayrışım analizi için önce parcel tanımlayın (SLOP hariç).</div>;
  }

  return (
    <div className="disc-wrap">
      <div className="disc-section loading">
        <div className="disc-section-head">
          <h4>⬇️ LOADING OPS</h4>
          <button className="small" disabled={!canProtest} onClick={() => onProtest("loading", null)} title={canProtest ? "Tüm parceller için tek PDF" : "Önce seferi kaydedin"}>
            📄 Protest All
          </button>
        </div>
        <div className="disc-cards">
          {cargoParcels.map((p) => (
            <LoadingCard
              key={p.id}
              parcel={p}
              summary={summaryOf(p.id)}
              onUpdate={(patch) => onUpdateParcel(p.id, patch)}
              onProtest={() => onProtest("loading", p.id)}
              canProtest={canProtest}
            />
          ))}
        </div>
      </div>
      <div className="disc-section discharging">
        <div className="disc-section-head">
          <h4>⬆️ DISCHARGING OPS</h4>
          <button className="small" disabled={!canProtest} onClick={() => onProtest("discharging", null)} title={canProtest ? "Tüm parceller için tek PDF" : "Önce seferi kaydedin"}>
            📄 Protest All
          </button>
        </div>
        <div className="disc-cards">
          {cargoParcels.map((p) => (
            <DischargingCard
              key={p.id}
              parcel={p}
              summary={summaryOf(p.id)}
              vef={vef}
              onUpdate={(patch) => onUpdateParcel(p.id, patch)}
              onProtest={() => onProtest("discharging", p.id)}
              canProtest={canProtest}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
