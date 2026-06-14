"use client";

import { ArrowRight, LineChart } from "lucide-react";
import type { LiveSpread } from "@/lib/types";
import {
  formatFunding,
  formatPercent,
  formatPrice,
  opportunityKey,
  spreadColorClass,
} from "@/lib/format";
import { flashClass, useFlash } from "@/lib/useFlash";
import CountdownTimer from "./CountdownTimer";
import ExchangeBadge from "./ExchangeBadge";

interface OpportunityTableProps {
  rows: LiveSpread[];
  onViewChart: (row: LiveSpread) => void;
}

const COLUMNS = [
  "Asset",
  "Route",
  "Real Spread",
  "Funding 24h",
  "Farm 24h / 72h",
  "Next Funding",
  "",
];

function Row({
  row,
  onViewChart,
}: {
  row: LiveSpread;
  onViewChart: (row: LiveSpread) => void;
}) {
  const spread = row.real_spread_pct ?? row.raw_spread_pct;
  const flash = useFlash(spread);

  return (
    <tr
      className={[
        "border-b border-white/[0.04] last:border-0 hover:bg-white/[0.025]",
        flashClass(flash),
      ].join(" ")}
    >
      <td className="px-5 py-4">
        <div className="flex flex-col">
          <span className="font-mono text-sm font-semibold text-slate-100">
            {row.asset}
          </span>
          <span className="font-mono text-[11px] text-slate-600">
            {formatPrice(row.long_price)} → {formatPrice(row.short_price)}
          </span>
        </div>
      </td>
      <td className="px-5 py-4">
        <div className="flex items-center gap-1.5">
          <ExchangeBadge name={row.long_exchange} tone="buy" />
          <ArrowRight className="h-3.5 w-3.5 text-slate-600" />
          <ExchangeBadge name={row.short_exchange} tone="sell" />
        </div>
      </td>
      <td className="px-5 py-4 text-right">
        <span
          className={`font-mono text-base font-semibold ${spreadColorClass(spread)}`}
        >
          {formatPercent(spread)}
        </span>
      </td>
      <td className="px-5 py-4 text-right font-mono text-xs text-slate-300">
        {formatPercent(row.net_funding_24h_pct, 3)}
      </td>
      <td className="px-5 py-4 text-right font-mono text-xs">
        <span className="text-emerald-300">
          {formatPercent(row.farm_24h_pct, 3)}
        </span>
        <span className="text-slate-600"> / </span>
        <span className="text-slate-400">
          {formatPercent(row.farm_72h_pct, 3)}
        </span>
      </td>
      <td className="px-5 py-4 text-right text-xs">
        <CountdownTimer nextMs={row.next_funding_ms} />
      </td>
      <td className="px-5 py-4 text-right">
        <button
          type="button"
          onClick={() => onViewChart(row)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-accent/30 bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent transition-colors hover:bg-accent/20"
        >
          <LineChart className="h-3.5 w-3.5" />
          Chart
        </button>
      </td>
    </tr>
  );
}

/** Desktop layout: rich data table (hidden on phones). */
export default function OpportunityTable({
  rows,
  onViewChart,
}: OpportunityTableProps) {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-base-850/60 shadow-glow backdrop-blur">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left">
              {COLUMNS.map((col, i) => (
                <th
                  key={col || i}
                  className={[
                    "px-5 py-3.5 text-xs font-semibold uppercase tracking-wider text-slate-500",
                    i >= 2 ? "text-right" : "",
                  ].join(" ")}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <Row
                key={opportunityKey(row)}
                row={row}
                onViewChart={onViewChart}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
