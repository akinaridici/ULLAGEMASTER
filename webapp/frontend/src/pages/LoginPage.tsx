import { useState } from "react";
import { ApiError, login, post } from "../api";

export default function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "register") {
        await post("/api/auth/register", { email, password, full_name: fullName });
      }
      await login(email, password);
      onLogin();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Connection error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <h1>⚓ UllageMaster</h1>
        <p className="subtitle">Cargo calculation for oil tankers</p>
        {mode === "register" && (
          <input placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
        )}
        <input
          type="email" placeholder="Email" required value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password" placeholder="Password (min 6 chars)" required minLength={6}
          value={password} onChange={(e) => setPassword(e.target.value)}
        />
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={busy}>
          {busy ? "..." : mode === "login" ? "Sign in" : "Create account"}
        </button>
        <a onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
          {mode === "login" ? "No account? Register" : "Have an account? Sign in"}
        </a>
      </form>
    </div>
  );
}
