"use client";

import { SlidersHorizontal, Sprout, TrendingUp } from "lucide-react";

export interface SpreadFilters {
  minSpread: number;
  fundingPositive: boolean;
}

interface FilterBarProps {
  filters: SpreadFilters;
  onChange: (next: SpreadFilters) => void;
}

const SPREAD_PRESETS = [0, 0.5, 1, 2];

export default function FilterBar({ filters, onChange }: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <span className="mr-1 hidden items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-slate-500 sm:flex">
        <SlidersHorizontal className="h-3.5 w-3.5" />
        Filters
      </span>

      <div className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-base-800/60 p-1">
        <TrendingUp className="ml-2 h-3.5 w-3.5 shrink-0 text-slate-500" />
        {SPREAD_PRESETS.map((preset) => {
          const on = filters.minSpread === preset;
          return (
            <button
              key={preset}
              type="button"
              onClick={() => onChange({ ...filters, minSpread: preset })}
              aria-pressed={on}
              className={[
                "inline-flex min-h-[40px] items-center rounded-full px-3.5 text-sm font-medium transition-colors",
                on
                  ? "bg-accent/20 text-accent"
                  : "text-slate-400 hover:text-slate-200 active:text-white",
              ].join(" ")}
            >
              {preset === 0 ? "All" : `>${preset}%`}
            </button>
          );
        })}
      </div>

      <button
        type="button"
        onClick={() =>
          onChange({ ...filters, fundingPositive: !filters.fundingPositive })
        }
        aria-pressed={filters.fundingPositive}
        className={[
          "inline-flex min-h-[44px] items-center gap-2 rounded-full border px-4 text-sm font-medium transition-all",
          filters.fundingPositive
            ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300 shadow-glow"
            : "border-white/10 bg-base-800/60 text-slate-400 hover:border-white/20 hover:text-slate-200",
        ].join(" ")}
      >
        <Sprout className="h-4 w-4" />
        Positive Farm
      </button>
    </div>
  );
}
