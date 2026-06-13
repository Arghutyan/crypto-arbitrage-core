import { Activity, Gauge, TrendingUp, Layers } from "lucide-react";
import type { SpreadRow } from "@/lib/types";
import { formatPercent } from "@/lib/format";

function computeStats(rows: SpreadRow[]) {
  const spreads = rows
    .map((r) => r.spreadPct)
    .filter((v): v is number => v != null);

  const best = spreads.length ? Math.max(...spreads) : null;
  const avg = spreads.length
    ? spreads.reduce((a, b) => a + b, 0) / spreads.length
    : null;
  const opportunities = spreads.filter((v) => v > 1).length;
  const pairs = new Set(rows.map((r) => r.pair)).size;

  return { best, avg, opportunities, pairs };
}

export default function StatCards({ rows }: { rows: SpreadRow[] }) {
  const { best, avg, opportunities, pairs } = computeStats(rows);

  const cards = [
    {
      label: "Best Spread",
      value: formatPercent(best),
      icon: TrendingUp,
      accent: "text-positive",
    },
    {
      label: "Avg Spread",
      value: formatPercent(avg),
      icon: Gauge,
      accent: "text-accent",
    },
    {
      label: "Opportunities > 1%",
      value: opportunities.toString(),
      icon: Activity,
      accent: "text-emerald-300",
    },
    {
      label: "Tracked Pairs",
      value: pairs.toString(),
      icon: Layers,
      accent: "text-slate-200",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {cards.map(({ label, value, icon: Icon, accent }) => (
        <div
          key={label}
          className="rounded-2xl border border-white/10 bg-base-850/60 p-4 backdrop-blur transition-colors hover:border-white/20"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
              {label}
            </span>
            <Icon className={`h-4 w-4 ${accent}`} />
          </div>
          <p className={`mt-2 font-mono text-2xl font-semibold ${accent}`}>
            {value}
          </p>
        </div>
      ))}
    </div>
  );
}
