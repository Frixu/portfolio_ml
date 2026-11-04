import { Bar, BarChart, LabelList, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { formatPct } from "../format";
import type { Holding } from "../types";

export default function SectorChart({ holdings }: { holdings: Holding[] }) {
  const bySector = new Map<string, number>();
  for (const h of holdings) {
    if (h.weight === null) continue;
    const sector = h.sector ?? "Inne";
    bySector.set(sector, (bySector.get(sector) ?? 0) + h.weight);
  }
  const data = [...bySector]
    .map(([sector, weight]) => ({ sector, weight }))
    .sort((a, b) => b.weight - a.weight);

  return (
    <div className="card">
      <h2>Struktura według sektorów</h2>
      {data.length === 0 ? (
        <p className="muted">Brak pozycji w portfelu.</p>
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(80, data.length * 40)}>
          <BarChart data={data} layout="vertical" margin={{ left: 0, right: 64, top: 0, bottom: 0 }}>
            <XAxis type="number" domain={[0, 1]} hide />
            <YAxis type="category" dataKey="sector" width={150} tickLine={false} axisLine={false} />
            <Bar dataKey="weight" fill="#2563eb" radius={[0, 4, 4, 0]} barSize={22} isAnimationActive={false}>
              <LabelList dataKey="weight" position="right" formatter={(v) => formatPct(Number(v))} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}