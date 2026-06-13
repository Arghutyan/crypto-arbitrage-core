"use client";

import { useState } from "react";
import {
  Layers,
  Ban,
  Repeat,
  TrendingUp,
  SlidersHorizontal,
  Check,
} from "lucide-react";

interface FilterOption {
  id: string;
  label: string;
  icon: React.ElementType;
  /** Whether the filter starts enabled. */
  defaultOn?: boolean;
}

// UI placeholders for now — wiring to real query params comes later.
const FILTERS: FilterOption[] = [
  { id: "spot-futures", label: "Spot + Futures", icon: Layers, defaultOn: true },
  { id: "exclude-dex", label: "Exclude DEX", icon: Ban, defaultOn: true },
  { id: "funding-arb", label: "Funding Arb", icon: Repeat },
  { id: "high-spread", label: "Spread > 1%", icon: TrendingUp },
];

export default function FilterBar() {
  const [active, setActive] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(FILTERS.map((f) => [f.id, Boolean(f.defaultOn)])),
  );

  const toggle = (id: string) =>
    setActive((prev) => ({ ...prev, [id]: !prev[id] }));

  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <span className="mr-1 hidden items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-slate-500 sm:flex">
        <SlidersHorizontal className="h-3.5 w-3.5" />
        Filters
      </span>

      {FILTERS.map(({ id, label, icon: Icon }) => {
        const on = active[id];
        return (
          <button
            key={id}
            type="button"
            onClick={() => toggle(id)}
            aria-pressed={on}
            className={[
              "group inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-sm font-medium transition-all duration-150",
              on
                ? "border-accent/40 bg-accent/15 text-accent shadow-glow"
                : "border-white/10 bg-base-800/60 text-slate-400 hover:border-white/20 hover:text-slate-200",
            ].join(" ")}
          >
            <span className="relative flex h-4 w-4 items-center justify-center">
              {on ? (
                <Check className="h-3.5 w-3.5" />
              ) : (
                <Icon className="h-4 w-4" />
              )}
            </span>
            {label}
          </button>
        );
      })}
    </div>
  );
}
