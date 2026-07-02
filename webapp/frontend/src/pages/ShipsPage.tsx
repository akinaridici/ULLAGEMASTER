import { useEffect, useRef, useState } from "react";
import { ApiError, del, get, upload } from "../api";
import type { Ship, ShipListItem } from "../types";

export default function ShipsPage({
  onOpenShip,
}: {
  onOpenShip: (shipId: number) => void;
}) {
  const [ships, setShips] = useState<ShipListItem[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    try {
      setShips(await get<ShipListItem[]>("/api/ships"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Connection error");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function importConfig(file: File) {
    setBusy(true);
    setError("");
    try {
      const ship = await upload<Ship>("/api/ships/import-config", file);
      await refresh();
      onOpenShip(ship.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  async function removeShip(id: number, name: string) {
    if (!confirm(`Delete ship "${name}" and all its voyages?`)) return;
    await del(`/api/ships/${id}`);
    refresh();
  }

  return (
    <div className="page">
      <div className="page-head">
        <h2>My Ships</h2>
        <div>
          <input
            ref={fileRef} type="file" accept=".json" style={{ display: "none" }}
            onChange={(e) => e.target.files?.[0] && importConfig(e.target.files[0])}
          />
          <button onClick={() => fileRef.current?.click()} disabled={busy}>
            {busy ? "Importing..." : "⬆ Import ship_config.json"}
          </button>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      {ships.length === 0 && !error && (
        <div className="empty">
          No ships yet. Import the <code>ship_config.json</code> from the desktop UllageMaster
          (found in <code>data/config/</code>) to get started with all tables in one click.
        </div>
      )}
      <div className="card-grid">
        {ships.map((s) => (
          <div key={s.id} className="ship-card" onClick={() => onOpenShip(s.id)}>
            <h3>🚢 {s.name}</h3>
            <p>{s.tank_count} tanks · {s.voyage_count} voyages</p>
            <button
              className="danger small"
              onClick={(e) => { e.stopPropagation(); removeShip(s.id, s.name); }}
            >
              Delete
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
