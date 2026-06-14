/** Formatting helpers shared across the dashboard. */

export function formatPrice(value: number | null): string {
  if (value == null) return "—";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: value < 1 ? 6 : 2,
  });
}

export function formatPercent(value: number | null, digits = 2): string {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}

/** Funding rates are fractions (0.0001 == 0.01%); render as signed percent. */
export function formatFunding(value: number | null): string {
  if (value == null) return "—";
  const pct = value * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(4)}%`;
}

/** Spread % -> semantic color class. */
export function spreadColorClass(value: number | null): string {
  if (value == null) return "text-slate-500";
  if (value > 1) return "text-positive";
  if (value > 0) return "text-emerald-400/80";
  if (value < 0) return "text-negative";
  return "text-slate-400";
}

/** Milliseconds-until-funding -> "Hh Mm Ss" countdown string. */
export function formatCountdown(nextMs: number | null): string {
  if (!nextMs) return "—";
  const remaining = Math.floor((nextMs - Date.now()) / 1000);
  if (remaining <= 0) return "now";
  const h = Math.floor(remaining / 3600);
  const m = Math.floor((remaining % 3600) / 60);
  const s = remaining % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

/** Stable key for an opportunity (asset + venue direction). */
export function opportunityKey(o: {
  asset: string;
  long_exchange: string;
  short_exchange: string;
}): string {
  return `${o.asset}:${o.long_exchange}->${o.short_exchange}`;
}
