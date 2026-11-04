import { useState, type FormEvent } from "react";
import { api } from "../api";
import type { Instrument } from "../types";

interface Props {
  portfolioId: string;
  instruments: Instrument[];
  onAdded: () => void;
}

const today = () => new Date().toISOString().slice(0, 10);

export default function TransactionForm({ portfolioId, instruments, onAdded }: Props) {
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [fee, setFee] = useState("0");
  const [tradeDate, setTradeDate] = useState(today());
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleTickerChange(value: string) {
    setTicker(value);
    // Podpowiadamy ostatni kurs spółki jako cenę
    const instrument = instruments.find((i) => i.ticker === value);
    if (instrument?.last_close) setPrice(String(instrument.last_close));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api(`/portfolios/${portfolioId}/transactions`, {
        method: "POST",
        body: JSON.stringify({
          ticker, side, quantity: Number(quantity), price: Number(price),
          fee: Number(fee || 0), trade_date: tradeDate,
        }),
      });
      setQuantity("");
      onAdded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nie udało się dodać transakcji");
    } finally {
      setSubmitting(false);
    }
  }

  const groups = ["WIG20", "mWIG40"].map((index) => ({
    index,
    items: instruments.filter((i) => i.index_name === index),
  }));

  return (
    <form className="card tx-form" onSubmit={handleSubmit}>
      <h2 className="full">Nowa transakcja</h2>

      <div className="side-toggle full">
        <button type="button" className={side === "BUY" ? "active" : ""} onClick={() => setSide("BUY")}>Kupno</button>
        <button type="button" className={side === "SELL" ? "active" : ""} onClick={() => setSide("SELL")}>Sprzedaż</button>
      </div>

      <label className="full">
        Spółka
        <select value={ticker} onChange={(e) => handleTickerChange(e.target.value)} required>
          <option value="" disabled>Wybierz spółkę…</option>
          {groups.map((g) => (
            <optgroup key={g.index} label={g.index}>
              {g.items.map((i) => (
                <option key={i.ticker} value={i.ticker}>{i.ticker} – {i.name}</option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>

      <label>
        Liczba akcji
        <input type="number" min="0.0001" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
      </label>
      <label>
        Cena za akcję (zł)
        <input type="number" min="0.0001" step="any" value={price} onChange={(e) => setPrice(e.target.value)} required />
      </label>
      <label>
        Prowizja (zł)
        <input type="number" min="0" step="0.01" value={fee} onChange={(e) => setFee(e.target.value)} />
      </label>
      <label>
        Data
        <input type="date" max={today()} value={tradeDate} onChange={(e) => setTradeDate(e.target.value)} required />
      </label>

      {error && <p className="error full">{error}</p>}
      <button type="submit" className="full" disabled={submitting}>
        {submitting ? "Zapisywanie…" : side === "BUY" ? "Dodaj kupno" : "Dodaj sprzedaż"}
      </button>
    </form>
  );
}