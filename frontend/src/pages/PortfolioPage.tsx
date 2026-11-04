import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import HoldingsTable from "../components/HoldingsTable";
import PortfolioSummary from "../components/PortfolioSummary";
import RecommendationsList from "../components/RecommendationsList";
import SectorChart from "../components/SectorChart";
import TransactionForm from "../components/TransactionForm";
import type { Instrument, PortfolioDetail, RecommendationsResponse } from "../types";

export default function PortfolioPage() {
  const { id = "" } = useParams();
  const [detail, setDetail] = useState<PortfolioDetail | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationsResponse | null>(null);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Stan portfela i rekomendacje pobieramy razem - po każdej transakcji odświeżamy oba
  const load = useCallback(async () => {
    try {
      const [d, r] = await Promise.all([
        api<PortfolioDetail>(`/portfolios/${id}`),
        api<RecommendationsResponse>(`/portfolios/${id}/recommendations`),
      ]);
      setDetail(d);
      setRecommendations(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się wczytać portfela");
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    api<Instrument[]>("/instruments").then(setInstruments).catch(() => setInstruments([]));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!detail) return <p className="muted">Ładowanie…</p>;

  return (
    <>
      <Link to="/" className="back-link">← Moje portfele</Link>
      <h1>{detail.name}</h1>

      <PortfolioSummary detail={detail} />

      <div className="grid-2">
        <SectorChart holdings={detail.holdings} />
        <TransactionForm portfolioId={id} instruments={instruments} onAdded={load} />
      </div>

      <HoldingsTable holdings={detail.holdings} />
      <RecommendationsList data={recommendations} />
    </>
  );
}