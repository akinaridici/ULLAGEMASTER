import { useState } from "react";
import { hasToken, setToken } from "./api";
import LoginPage from "./pages/LoginPage";
import ShipsPage from "./pages/ShipsPage";
import ShipDetailPage from "./pages/ShipDetailPage";
import VoyagePage from "./pages/VoyagePage";

type View =
  | { name: "ships" }
  | { name: "ship"; shipId: number }
  | { name: "voyage"; shipId: number; voyageId: number | null };

export default function App() {
  const [authed, setAuthed] = useState(hasToken());
  const [view, setView] = useState<View>({ name: "ships" });

  if (!authed) return <LoginPage onLogin={() => setAuthed(true)} />;

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand" onClick={() => setView({ name: "ships" })}>⚓ UllageMaster</span>
        <button
          className="small"
          onClick={() => {
            setToken(null);
            setAuthed(false);
            setView({ name: "ships" });
          }}
        >
          Sign out
        </button>
      </header>
      {view.name === "ships" && (
        <ShipsPage onOpenShip={(shipId) => setView({ name: "ship", shipId })} />
      )}
      {view.name === "ship" && (
        <ShipDetailPage
          shipId={view.shipId}
          onBack={() => setView({ name: "ships" })}
          onOpenVoyage={(voyageId) => setView({ name: "voyage", shipId: view.shipId, voyageId })}
        />
      )}
      {view.name === "voyage" && (
        <VoyagePage
          shipId={view.shipId}
          voyageId={view.voyageId}
          onBack={() => setView({ name: "ship", shipId: view.shipId })}
        />
      )}
    </div>
  );
}
