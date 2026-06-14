"use client";

import { ArrowDown, ArrowRight, ArrowUp, Ban, LineChart } from "lucide-react";
import type { LiveSpread } from "@/lib/types";
import {
  formatInterval,
  formatPercent,
  formatPrice,
  opportunityKey,
  signedColorClass,
  spreadColorClass,
} from "@/lib/format";
import { flashClass, useFlash } from "@/lib/useFlash";
import CountdownTimer from "./CountdownTimer";
import ExchangeBadge from "./ExchangeBadge";

export type SortKey = "spread" | "funding";
export interface SortState {
  key: SortKey;
  dir: "asc" | "desc";
}

interface OpportunityTableProps {
  rows: LiveSpread[];
  sort: SortState;
  onToggleSort: (key: SortKey) => void;
  onViewChart: (row: LiveSpread) => void;
  onSelectAsset: (asset: string) => void;
  onBlacklist: (asset: string) => void;
}

function SortHeader({
  label,
  column,
  sort,
  onToggleSort,
}: {
  label: string;
  column: SortKey;
  sort: SortState;
  onToggleSort: (key: SortKey) => void;
}) {
  const active = sort.key === column;
  return (
    <th className="px-5 py-3.5 text-right">
      <button
        type="button"
        onClick={() => onToggleSort(column)}
        className={[
          "ml-auto inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wider transition-colors",
          active ? "text-accent" : "text-slate-500 hover:text-slate-300",
        ].join(" ")}
      >
        {label}
        {active ? (
          sort.dir === "desc" ? (
            <ArrowDown className="h-3.5 w-3.5" />
          ) : (
            <ArrowUp className="h-3.5 w-3.5" />
          )
        ) : (
          <ArrowDown className="h-3.5 w-3.5 opacity-30" />
        )}
      </button>
    </th>
  );
}

function Row({
  row,
  onViewChart,
  onSelectAsset,
  onBlacklist,
}: {
  row: LiveSpread;
  onViewChart: (row: LiveSpread) => void;
  onSelectAsset: (asset: string) => void;
  onBlacklist: (asset: string) => void;
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
          <button
            type="button"
            onClick={() => onSelectAsset(row.asset)}
            title={`Filter to ${row.asset}`}
            className="w-fit font-mono text-sm font-semibold text-slate-100 transition-colors hover:text-accent"
          >
            {row.asset}
          </button>
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
        <div className="mt-1 font-mono text-[11px] text-slate-600">
          Intervals: {formatInterval(row.long_funding_interval_h)} (
          {row.long_exchange}) / {formatInterval(row.short_funding_interval_h)} (
          {row.short_exchange})
        </div>
      </td>
      <td className="px-5 py-4 text-right">
        <span
          className={`font-mono text-base font-semibold ${spreadColorClass(spread)}`}
        >
          {formatPercent(spread)}
        </span>
      </td>
      <td
        className={`px-5 py-4 text-right font-mono text-xs ${signedColorClass(
          row.net_funding_24h_pct,
        )}`}
      >
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
      <td className="px-5 py-4">
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => onViewChart(row)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-accent/30 bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent transition-colors hover:bg-accent/20"
          >
            <LineChart className="h-3.5 w-3.5" />
            Chart
          </button>
          <button
            type="button"
            onClick={() => onBlacklist(row.asset)}
            title={`Hide & blacklist ${row.asset}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-300 transition-colors hover:bg-rose-500/20"
          >
            <Ban className="h-3.5 w-3.5" />
            Hide
          </button>
        </div>
      </td>
    </tr>
  );
}

/** Desktop layout: rich data table (hidden on phones). */
export default function OpportunityTable({
  rows,
  sort,
  onToggleSort,
  onViewChart,
  onSelectAsset,
  onBlacklist,
}: OpportunityTableProps) {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-base-850/60 shadow-glow backdrop-blur">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left">
              <th className="px-5 py-3.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Asset
              </th>
              <th className="px-5 py-3.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Route
              </th>
              <SortHeader
                label="Real Spread"
                column="spread"
                sort={sort}
                onToggleSort={onToggleSort}
              />
              <SortHeader
                label="Funding 24h"
                column="funding"
                sort={sort}
                onToggleSort={onToggleSort}
              />
              <th className="px-5 py-3.5 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">
                Farm 24h / 72h
              </th>
              <th className="px-5 py-3.5 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">
                Next Funding
              </th>
              <th className="px-5 py-3.5" />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <Row
                key={opportunityKey(row)}
                row={row}
                onViewChart={onViewChart}
                onSelectAsset={onSelectAsset}
                onBlacklist={onBlacklist}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
