import { formatPLN, formatSignedPLN, formatSignedPct, pnlClass } from "../format";
import type { PortfolioDetail } from "../types";

function Stat({ label, value, sub, className = "" }: {
  label: string; value: string; sub?: string; className?: string;
}) {
  return (
    <div className="card stat">
      <span className="muted">{label}</span>
      <strong className={className}>{value}</strong>
      {sub && <span className={className}>{sub}</span>}
    </div>
  );
}

export default function PortfolioSummary({ detail }: { detail: PortfolioDetail }) {
  const unrealizedPct = detail.total_cost ? detail.unrealized_pnl / detail.total_cost : null;

  return (
    <div className="summary">
      <Stat label="Wartość portfela" value={formatPLN(detail.total_value)} />
      <Stat label="Koszt zakupu" value={formatPLN(detail.total_cost)} />
      <Stat
        label="Zysk niezrealizowany"
        value={formatSignedPLN(detail.unrealized_pnl)}
        sub={formatSignedPct(unrealizedPct)}
        className={pnlClass(detail.unrealized_pnl)}
      />
      <Stat
        label="Zysk zrealizowany"
        value={formatSignedPLN(detail.realized_pnl)}
        className={pnlClass(detail.realized_pnl)}
      />
    </div>
  );
}