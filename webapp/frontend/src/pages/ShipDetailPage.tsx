import { useEffect, useState } from "react";
import { ApiError, del, get, upload } from "../api";
import type { Ship, TankOut, VoyageListItem } from "../types";

export default function ShipDetailPage({
  shipId,
  onOpenVoyage,
  onBack,
}: {
  shipId: number;
  onOpenVoyage: (voyageId: number | null) => void;
  onBack: () => void;
}) {
  const [ship, setShip] = useState<Ship | null>(null);
  const [voyages, setVoyages] = useState<VoyageListItem[]>([]);
  const [error, setError] = useState("");

  async function refresh() {
    try {
      setShip(await get<Ship>(`/api/ships/${shipId}`));
      setVoyages(await get<VoyageListItem[]>(`/api/ships/${shipId}/voyages`));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Connection error");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shipId]);

  async function uploadTable(tank: TankOut, type: "ullage" | "trim" | "thermal", file: File) {
    setError("");
    try {
      await upload(`/api/ships/${shipId}/tanks/${encodeURIComponent(tank.tank_code)}/tables/${type}`, file);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    }
  }

  async function removeVoyage(id: number, no: string) {
    if (!confirm(`Delete voyage "${no}"?`)) return;
    await del(`/api/ships/${shipId}/voyages/${id}`);
    refresh();
  }

  if (!ship) return <div className="page">{error ? <div className="error">{error}</div> : "Loading..."}</div>;

  return (
    <div className="page">
      <div className="page-head">
        <h2>
          <a onClick={onBack}>Ships</a> / 🚢 {ship.name}
        </h2>
        <button className="primary" onClick={() => onOpenVoyage(null)}>+ New Voyage</button>
      </div>
      {error && <div className="error">{error}</div>}

      <h3>Voyages</h3>
      {voyages.length === 0 && <div className="empty">No voyages yet.</div>}
      <table className="list-table">
        <tbody>
          {voyages.map((v) => (
            <tr key={v.id}>
              <td><a onClick={() => onOpenVoyage(v.id)}><b>{v.voyage_number || `#${v.id}`}</b></a></td>
              <td>{v.date}</td>
              <td>{v.port} {v.terminal && `/ ${v.terminal}`}</td>
              <td className="right">
                <button className="danger small" onClick={() => removeVoyage(v.id, v.voyage_number)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Company Logo</h3>
      <p className="hint">
        Resmi raporlarda (Letter of Protest vb.) kullanılır. PNG veya JPEG, en fazla 2 MB.{" "}
        <label className={`table-chip ${ship.has_logo ? "ok" : "missing"}`}>
          {ship.has_logo ? "✓ yüklü — değiştir" : "logo yükle"}
          <input
            type="file" accept=".png,.jpg,.jpeg" style={{ display: "none" }}
            onChange={async (e) => {
              const f = e.target.files?.[0];
              if (!f) return;
              try {
                await upload(`/api/ships/${shipId}/logo`, f);
                refresh();
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Logo upload failed");
              }
            }}
          />
        </label>
      </p>

      <h3>Tanks &amp; Tables</h3>
      <p className="hint">
        V.E.F. {ship.default_vef.toFixed(5)} · Master: {ship.master || "—"} · C/O: {ship.chief_officer || "—"}.
        CSV upload: ullage (<code>ullage_mm,volume_m3</code>), trim (<code>ullage_mm,trim_m,correction_m3</code>),
        thermal (<code>temp_c,corr_factor</code>). <code>ullage_cm</code> is accepted too.
      </p>
      <table className="list-table">
        <thead>
          <tr>
            <th>Tank</th><th>Name</th><th className="right">Capacity (m³)</th>
            <th>Ullage</th><th>Trim</th><th>Thermal</th>
          </tr>
        </thead>
        <tbody>
          {ship.tanks.map((t) => (
            <tr key={t.tank_code}>
              <td><b>{t.tank_code}</b></td>
              <td>{t.name}</td>
              <td className="right">{t.capacity_m3.toFixed(1)}</td>
              {(["ullage", "trim", "thermal"] as const).map((type) => {
                const has =
                  type === "ullage" ? t.has_ullage_table :
                  type === "trim" ? t.has_trim_table : t.has_thermal_table;
                return (
                  <td key={type}>
                    <label className={`table-chip ${has ? "ok" : "missing"}`}>
                      {has ? "✓" : "upload"}
                      <input
                        type="file" accept=".csv" style={{ display: "none" }}
                        onChange={(e) => e.target.files?.[0] && uploadTable(t, type, e.target.files[0])}
                      />
                    </label>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
