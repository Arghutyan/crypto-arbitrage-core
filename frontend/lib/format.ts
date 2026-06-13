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

/**
 * Funding rates are stored as fractions (e.g. 0.0001 == 0.01%).
 * Render them as a signed percentage with extra precision.
 */
export function formatFunding(value: number | null): string {
  if (value == null) return "—";
  const pct = value * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(4)}%`;
}

export function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Map a spread percentage to a semantic color class.
 *   > 1%   -> strong green
 *   > 0%   -> soft green
 *   < 0%   -> red
 *   == 0/null -> muted
 */
export function spreadColorClass(value: number | null): string {
  if (value == null) return "text-slate-500";
  if (value > 1) return "text-positive";
  if (value > 0) return "text-emerald-400/80";
  if (value < 0) return "text-negative";
  return "text-slate-400";
}
