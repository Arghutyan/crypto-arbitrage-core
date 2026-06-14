"use client";

import { ArrowRight, Ban, LineChart, Sprout } from "lucide-react";
import type { LiveSpread } from "@/lib/types";
import {
  formatFunding,
  formatInterval,
  formatPercent,
  formatPrice,
  spreadColorClass,
} from "@/lib/format";
import { flashClass, useFlash } from "@/lib/useFlash";
import CountdownTimer from "./CountdownTimer";
import ExchangeBadge from "./ExchangeBadge";

interface OpportunityCardProps {
  row: LiveSpread;
  onViewChart: (row: LiveSpread) => void;
  onSelectAsset: (asset: string) => void;
  onBlacklist: (asset: string) => void;
}

/** Mobile-first card: the primary layout on phones. */
export default function OpportunityCard({
  row,
  onViewChart,
  onSelectAsset,
  onBlacklist,
}: OpportunityCardProps) {
  const spread = row.real_spread_pct ?? row.raw_spread_pct;
  const flash = useFlash(spread);

  return (
    <div
      className={[
        "rounded-2xl border border-white/10 bg-base-850/60 p-4 backdrop-blur",
        flashClass(flash),
      ].join(" ")}
    >
      <div className="flex items-start justify-between">
        <div>
          <button
            type="button"
            onClick={() => onSelectAsset(row.asset)}
            className="font-mono text-lg font-semibold text-slate-100 transition-colors hover:text-accent"
          >
            {row.asset}
          </button>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs">
            <ExchangeBadge name={row.long_exchange} tone="buy" />
            <ArrowRight className="h-3.5 w-3.5 shrink-0 text-slate-600" />
            <ExchangeBadge name={row.short_exchange} tone="sell" />
          </div>
        </div>
        <div className="text-right">
          <div
            className={`font-mono text-2xl font-bold ${spreadColorClass(spread)}`}
          >
            {formatPercent(spread)}
          </div>
          <div className="text-[11px] uppercase tracking-wider text-slate-600">
            Real Spread
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
        <div className="rounded-xl bg-base-800/60 p-2.5">
          <div className="text-slate-600">Buy {row.long_exchange}</div>
          <div className="mt-0.5 font-mono text-slate-200">
            {formatPrice(row.long_price)}
          </div>
        </div>
        <div className="rounded-xl bg-base-800/60 p-2.5">
          <div className="text-slate-600">Sell {row.short_exchange}</div>
          <div className="mt-0.5 font-mono text-slate-200">
            {formatPrice(row.short_price)}
          </div>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-white/[0.06] pt-3 text-xs">
        <span className="inline-flex items-center gap-1 text-slate-400">
          <Sprout className="h-3.5 w-3.5 text-emerald-400" />
          24h {formatPercent(row.farm_24h_pct, 3)} · 72h{" "}
          {formatPercent(row.farm_72h_pct, 3)}
        </span>
        <CountdownTimer nextMs={row.next_funding_ms} />
      </div>

      <div className="mt-2 font-mono text-[11px] text-slate-500">
        Intervals: {formatInterval(row.long_funding_interval_h)} (
        {row.long_exchange}) / {formatInterval(row.short_funding_interval_h)} (
        {row.short_exchange})
      </div>

      <div className="mt-3 flex items-center justify-between gap-2 border-t border-white/[0.06] pt-3 text-[11px] text-slate-500">
        <span className="min-w-0 truncate font-mono">
          Fund {formatFunding(row.long_funding)} /{" "}
          {formatFunding(row.short_funding)}
        </span>
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => onBlacklist(row.asset)}
            className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm font-medium text-rose-300 transition-colors hover:bg-rose-500/20 active:bg-rose-500/30"
          >
            <Ban className="h-4 w-4" />
            Hide
          </button>
          <button
            type="button"
            onClick={() => onViewChart(row)}
            className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg border border-accent/30 bg-accent/10 px-4 py-2 text-sm font-medium text-accent transition-colors hover:bg-accent/20 active:bg-accent/30"
          >
            <LineChart className="h-4 w-4" />
            Chart
          </button>
        </div>
      </div>
    </div>
  );
}
