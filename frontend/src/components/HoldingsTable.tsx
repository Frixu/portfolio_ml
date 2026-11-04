import { formatNumber, formatPLN, formatPct, formatSignedPLN, formatSignedPct, pnlClass } from "../format";
import type { Holding } from "../types";

export default function HoldingsTable({ holdings }: { holdings: Holding[] }) {
  if (holdings.length === 0) {
    return <p className="card muted">Portfel jest pusty – dodaj pierwszą transakcję.</p>;
  }

  return (
    <div className="card table-wrap">
      <h2>Pozycje</h2>
      <table>
        <thead>
          <tr>
            <th>Spółka</th>
            <th>Sektor</th>
            <th>Liczba akcji</th>
            <th>Śr. koszt</th>
            <th>Kurs</th>
            <th>Wartość</th>
            <th>Zysk</th>
            <th>Udział</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => (
            <tr key={h.ticker}>
              <td><strong>{h.ticker}</strong> <span className="muted">{h.name}</span></td>
              <td>{h.sector ?? "–"}</td>
              <td>{formatNumber(h.quantity)}</td>
              <td>{formatPLN(h.avg_cost)}</td>
              <td>{formatPLN(h.last_close)}</td>
              <td>{formatPLN(h.market_value)}</td>
              <td className={pnlClass(h.unrealized_pnl)}>
                {formatSignedPLN(h.unrealized_pnl)} ({formatSignedPct(h.unrealized_pnl_pct)})
              </td>
              <td>{formatPct(h.weight)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}