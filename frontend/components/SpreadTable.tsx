import { ArrowDownRight, ArrowUpRight, Inbox } from "lucide-react";
import type { SpreadRow } from "@/lib/types";
import {
  formatFunding,
  formatPercent,
  formatPrice,
  spreadColorClass,
} from "@/lib/format";
import ExchangeBadge from "./ExchangeBadge";

interface SpreadTableProps {
  rows: SpreadRow[];
}

const COLUMNS = [
  "Trading Pair",
  "Buy Exchange",
  "Sell Exchange",
  "Spread %",
  "24h Volume / Funding",
];

export default function SpreadTable({ rows }: SpreadTableProps) {
  if (rows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-white/10 bg-base-850/60 py-20 text-center">
        <Inbox className="h-8 w-8 text-slate-600" />
        <p className="text-sm font-medium text-slate-400">
          No spreads available right now
        </p>
        <p className="max-w-sm text-xs text-slate-600">
          The backend returned an empty set. Once the engine writes fresh
          spread data, opportunities will appear here automatically.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-base-850/60 shadow-glow backdrop-blur">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left">
              {COLUMNS.map((col, i) => (
                <th
                  key={col}
                  className={[
                    "px-5 py-3.5 text-xs font-semibold uppercase tracking-wider text-slate-500",
                    i === 3 ? "text-right" : "",
                    i === 4 ? "text-right" : "",
                  ].join(" ")}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const positive = (row.spreadPct ?? 0) >= 0;
              return (
                <tr
                  key={row.id}
                  className="border-b border-white/[0.04] transition-colors last:border-0 hover:bg-white/[0.025]"
                >
                  {/* Trading pair */}
                  <td className="px-5 py-4">
                    <div className="flex flex-col">
                      <span className="font-mono text-sm font-semibold text-slate-100">
                        {row.pair}
                      </span>
                      <span className="text-[11px] text-slate-600">
                        ID #{row.id}
                      </span>
                    </div>
                  </td>

                  {/* Buy exchange */}
                  <td className="px-5 py-4">
                    <div className="flex flex-col gap-1">
                      <ExchangeBadge name={row.buyExchange} tone="buy" />
                      <span className="font-mono text-xs text-slate-400">
                        {formatPrice(row.buyPrice)}
                      </span>
                    </div>
                  </td>

                  {/* Sell exchange */}
                  <td className="px-5 py-4">
                    <div className="flex flex-col gap-1">
                      <ExchangeBadge name={row.sellExchange} tone="sell" />
                      <span className="font-mono text-xs text-slate-400">
                        {formatPrice(row.sellPrice)}
                      </span>
                    </div>
                  </td>

                  {/* Spread % with dynamic color */}
                  <td className="px-5 py-4 text-right">
                    <span
                      className={`inline-flex items-center justify-end gap-1 font-mono text-base font-semibold ${spreadColorClass(
                        row.spreadPct,
                      )}`}
                    >
                      {row.spreadPct != null &&
                        (positive ? (
                          <ArrowUpRight className="h-4 w-4" />
                        ) : (
                          <ArrowDownRight className="h-4 w-4" />
                        ))}
                      {formatPercent(row.spreadPct)}
                    </span>
                  </td>

                  {/* Funding rates (proxy for 24h volume/funding) */}
                  <td className="px-5 py-4 text-right">
                    <div className="flex flex-col items-end gap-0.5 font-mono text-xs">
                      <span className="text-slate-300">
                        {row.buyExchange}: {formatFunding(row.buyFunding)}
                      </span>
                      <span className="text-slate-500">
                        {row.sellExchange}: {formatFunding(row.sellFunding)}
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
