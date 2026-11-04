import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Portfolio } from "../types";

export default function PortfoliosPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[] | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Portfolio[]>("/portfolios")
      .then(setPortfolios)
      .catch((err) => setError(err.message));
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const created = await api<Portfolio>("/portfolios", { method: "POST", body: JSON.stringify({ name }) });
      setPortfolios((current) => [...(current ?? []), created]);
      setName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się utworzyć portfela");
    }
  }

  return (
    <>
      <h1>Moje portfele</h1>

      {portfolios === null ? (
        <p className="muted">Ładowanie…</p>
      ) : portfolios.length === 0 ? (
        <p className="muted">Nie masz jeszcze portfela. Utwórz pierwszy poniżej.</p>
      ) : (
        <ul className="portfolio-list">
          {portfolios.map((p) => (
            <li key={p.id}>
              <Link to={`/portfolios/${p.id}`} className="card portfolio-card">
                <strong>{p.name}</strong>
                <span className="muted">utworzony {new Date(p.created_at).toLocaleDateString("pl-PL")}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <form className="card inline-form" onSubmit={handleCreate}>
        <input placeholder="Nazwa nowego portfela" value={name} onChange={(e) => setName(e.target.value)} required maxLength={100} />
        <button type="submit">Utwórz portfel</button>
      </form>
      {error && <p className="error">{error}</p>}
    </>
  );
}