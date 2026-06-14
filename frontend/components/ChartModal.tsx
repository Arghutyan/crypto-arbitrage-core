"use client";

import { useEffect } from "react";
import useSWR from "swr";
import { Loader2, TriangleAlert, X } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetcher, spreadHistoryPath } from "@/lib/api";
import type { LiveSpread, SpreadHistoryResponse } from "@/lib/types";
import { formatPercent } from "@/lib/format";

interface ChartModalProps {
  opportunity: LiveSpread | null;
  onClose: () => void;
}

function hourLabel(ms: number): string {
  return new Date(ms).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
  });
}

export default function ChartModal({ opportunity, onClose }: ChartModalProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const key = opportunity
    ? spreadHistoryPath(
        opportunity.asset,
        opportunity.long_exchange,
        opportunity.short_exchange,
      )
    : null;

  const { data, error, isLoading } = useSWR<SpreadHistoryResponse>(
    key,
    fetcher,
  );

  if (!opportunity) return null;

  const points = (data?.points ?? []).map((p) => ({
    ...p,
    label: hourLabel(p.time),
  }));

  // Dynamic Y domain with ~12% padding so small spread moves aren't flattened
  // against a fixed 0-based axis.
  const yDomain = ((): [number, number] => {
    if (points.length === 0) return [0, 1];
    const values = points.map((p) => p.spread_pct);
    const lo = Math.min(...values);
    const hi = Math.max(...values);
    const span = hi - lo;
    const pad = span > 0 ? span * 0.12 : Math.max(Math.abs(hi) * 0.1, 0.05);
    return [lo - pad, hi + pad];
  })();

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-0 backdrop-blur-sm sm:items-center sm:p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-t-3xl border border-white/10 bg-base-850 p-5 shadow-glow sm:rounded-3xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate font-mono text-lg font-semibold text-slate-100">
              {opportunity.asset} · 3-Day Spread
            </h3>
            <p className="truncate text-xs text-slate-500">
              {opportunity.long_exchange} → {opportunity.short_exchange} ·
              hourly
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-white/10 text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-200 active:bg-white/10"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-5 h-72 w-full">
          {isLoading ? (
            <div className="flex h-full items-center justify-center gap-2 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading klines…
            </div>
          ) : error ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-rose-300">
              <TriangleAlert className="h-6 w-6" />
              Couldn&apos;t load history for this pair.
            </div>
          ) : points.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">
              No overlapping candles for these venues.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={points}
                margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="spreadFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#5b8cff" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#5b8cff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(255,255,255,0.06)"
                />
                <XAxis
                  dataKey="label"
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  minTickGap={40}
                  stroke="rgba(255,255,255,0.1)"
                />
                <YAxis
                  domain={yDomain}
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  tickFormatter={(v: number) => `${v.toFixed(2)}%`}
                  stroke="rgba(255,255,255,0.1)"
                  width={56}
                  allowDecimals
                />
                <Tooltip
                  cursor={{
                    stroke: "rgba(91,140,255,0.5)",
                    strokeWidth: 1,
                    strokeDasharray: "4 4",
                  }}
                  contentStyle={{
                    background: "#0d121d",
                    border: "1px solid rgba(255,255,255,0.12)",
                    borderRadius: 12,
                    fontSize: 12,
                    boxShadow: "0 8px 30px rgba(0,0,0,0.5)",
                  }}
                  labelStyle={{ color: "#94a3b8", marginBottom: 4 }}
                  itemStyle={{ color: "#e2e8f0" }}
                  formatter={(value: number) => [
                    formatPercent(value, 3),
                    "Spread",
                  ]}
                />
                <Area
                  type="monotone"
                  dataKey="spread_pct"
                  stroke="#5b8cff"
                  strokeWidth={2.5}
                  fill="url(#spreadFill)"
                  dot={false}
                  activeDot={{
                    r: 4,
                    fill: "#5b8cff",
                    stroke: "#0d121d",
                    strokeWidth: 2,
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
