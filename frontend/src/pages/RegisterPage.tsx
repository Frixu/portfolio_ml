import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { RISK_PROFILE_LABELS, type RiskProfile } from "../types";

const PROFILE_DESCRIPTIONS: Record<RiskProfile, string> = {
  conservative: "Tylko największe spółki (WIG20), bez najbardziej zmiennych, niskie limity koncentracji.",
  balanced: "Spółki z WIG20 i mWIG40, umiarkowane limity koncentracji.",
  dynamic: "Spółki z WIG20 i mWIG40, wyższe limity koncentracji.",
};

export default function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [riskProfile, setRiskProfile] = useState<RiskProfile>("balanced");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(email, password, riskProfile);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się utworzyć konta");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-form" onSubmit={handleSubmit}>
        <h1>Rejestracja</h1>
        <label>
          E-mail
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </label>
        <label>
          Hasło (min. 8 znaków)
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
        </label>
        <label>
          Profil ryzyka
          <select value={riskProfile} onChange={(e) => setRiskProfile(e.target.value as RiskProfile)}>
            {(Object.keys(RISK_PROFILE_LABELS) as RiskProfile[]).map((p) => (
              <option key={p} value={p}>{RISK_PROFILE_LABELS[p]}</option>
            ))}
          </select>
        </label>
        <p className="muted">{PROFILE_DESCRIPTIONS[riskProfile]}</p>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "Tworzenie konta…" : "Utwórz konto"}
        </button>
        <p className="muted">
          Masz już konto? <Link to="/login">Zaloguj się</Link>
        </p>
      </form>
    </div>
  );
}