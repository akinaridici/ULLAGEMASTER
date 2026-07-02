import { useMemo } from "react";
import type { CalcResponse, CalcRow, Parcel } from "../types";

function contrast(hex: string): string {
  const h = (hex || "").replace("#", "");
  if (h.length < 6) return "#000";
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.5 ? "#000" : "#fff";
}

function fmt(v: number | null | undefined, digits: number): string {
  return v === null || v === undefined ? "—" : v.toFixed(digits);
}

interface Column {
  key: string;
  port?: CalcRow;
  starboard?: CalcRow;
  isSlop: boolean;
}

function TankCell({
  row,
  parcel,
  side,
}: {
  row?: CalcRow;
  parcel?: Parcel;
  side: "P" | "S";
}) {
  if (!row) return <div className="stow-cell empty" />;
  const isSlop = row.parcel_id === "0";
  const bandColor = parcel?.color || (isSlop ? "#9CA3AF" : "#e2e8f0");
  const bandText = contrast(bandColor);
  const grade = parcel?.name || (isSlop ? "SLOP" : "");
  const receiver = parcel?.receiver || "";

  const idBox = <div className="stow-id">{row.tank_id}</div>;
  const band = (
    <div className="stow-band" style={{ background: bandColor, color: bandText }}>
      {grade || " "}
    </div>
  );
  const body = (
    <>
      <div className="stow-receiver">{receiver || " "}</div>
      <div className={`stow-data ${side === "P" ? "port" : "stbd"}`}>
        <div><span>ULL</span><span>{fmt(row.ullage, 0)}</span></div>
        <div><span>MT</span><span>{fmt(row.mt_air, 0)}</span></div>
        <div><span>CBM</span><span>{fmt(row.gov, 0)}</span></div>
        <div><span>%</span><span className={row.warning !== "normal" ? `warn-${row.warning}` : ""}>{fmt(row.fill_percent, 1)}</span></div>
      </div>
    </>
  );

  // Port: id on deck edge, colour band touching the centre line. Starboard mirrored.
  return side === "P" ? (
    <div className="stow-cell">{idBox}{body}{band}</div>
  ) : (
    <div className="stow-cell">{band}{body}{idBox}</div>
  );
}

export default function StowagePlanView({
  calc,
  parcels,
}: {
  calc: CalcResponse | null;
  parcels: Parcel[];
}) {
  const parcelById = useMemo(() => {
    const map: Record<string, Parcel> = {};
    parcels.forEach((p) => (map[p.id] = p));
    return map;
  }, [parcels]);

  const columns = useMemo<Column[]>(() => {
    if (!calc) return [];
    const groups: Record<number, Column> = {};
    const slop: Column = { key: "slop", isSlop: true };
    for (const row of calc.rows) {
      const upper = row.tank_id.toUpperCase();
      if (upper.includes("SLOP")) {
        if (upper.replace("SLOP", "").includes("P")) slop.port = row;
        else slop.starboard = row;
        continue;
      }
      const digits = row.tank_id.replace(/\D/g, "");
      if (!digits) continue;
      const num = parseInt(digits, 10);
      groups[num] = groups[num] || { key: String(num), isSlop: false };
      if (upper.endsWith("S")) groups[num].starboard = row;
      else groups[num].port = row;
    }
    const sorted = Object.keys(groups).map(Number).sort((a, b) => b - a).map((n) => groups[n]);
    return slop.port || slop.starboard ? [slop, ...sorted] : sorted;
  }, [calc]);

  if (!calc || columns.length === 0) {
    return <div className="empty">No tank data yet — enter readings in the Ullage Grid first.</div>;
  }

  return (
    <div className="stow-wrap">
      <div className="stow-scroll">
        <div className="stow-strip">
          <div className="stow-stern">◀ STERN</div>
          {columns.map((col) => (
            <div key={col.key} className="stow-column">
              <TankCell row={col.port} parcel={col.port ? parcelById[col.port.parcel_id] : undefined} side="P" />
              <div className="stow-centerline" />
              <TankCell row={col.starboard} parcel={col.starboard ? parcelById[col.starboard.parcel_id] : undefined} side="S" />
            </div>
          ))}
          <div className="stow-bow">BOW ▶</div>
        </div>
      </div>
      <div className="stow-legend">
        <span className="stow-side-label">↑ PORT (iskele)</span>
        <span className="stow-side-label">↓ STARBOARD (sancak)</span>
      </div>
    </div>
  );
}
