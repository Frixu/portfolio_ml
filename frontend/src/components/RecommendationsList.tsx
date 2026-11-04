import { RISK_PROFILE_LABELS, type RecommendationAction, type RecommendationsResponse } from "../types";

const ACTION_LABELS: Record<RecommendationAction, string> = {
  ADD: "Rozważ dodanie",
  REDUCE: "Zmniejsz udział",
  CONSIDER_SELL: "Rozważ sprzedaż",
};

export default function RecommendationsList({ data }: { data: RecommendationsResponse | null }) {
  if (data === null) return <p className="muted">Ładowanie rekomendacji…</p>;

  return (
    <section>
      <h2>Rekomendacje</h2>
      <p className="muted">
        {data.scores_date
          ? `Profil: ${RISK_PROFILE_LABELS[data.risk_profile]} · model ${data.model_version} · dane na ${new Date(data.scores_date).toLocaleDateString("pl-PL")}`
          : "Brak ocen modelu – uruchom skrypt score.py."}
      </p>

      {data.scores_date && data.recommendations.length === 0 && (
        <p className="card muted">Portfel spełnia wszystkie reguły Twojego profilu – brak propozycji zmian.</p>
      )}

      <div className="recs">
        {data.recommendations.map((r) => (
          <article key={r.ticker} className={`card rec rec-${r.action.toLowerCase()}`}>
            <div className="rec-header">
              <span className="rec-action">{ACTION_LABELS[r.action]}</span>
              <strong>{r.ticker}</strong>
              <span>{r.name}</span>
              {r.sector && <span className="muted">· {r.sector}</span>}
            </div>
            <ul>
              {r.reasons.map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
          </article>
        ))}
      </div>

      <p className="disclaimer">{data.disclaimer}</p>
    </section>
  );
}