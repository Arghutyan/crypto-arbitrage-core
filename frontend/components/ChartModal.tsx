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

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-0 backdrop-blur-sm sm:items-center sm:p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl rounded-t-3xl border border-white/10 bg-base-850 p-5 shadow-glow sm:rounded-3xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-mono text-lg font-semibold text-slate-100">
              {opportunity.asset} · 3-Day Spread
            </h3>
            <p className="text-xs text-slate-500">
              {opportunity.long_exchange} → {opportunity.short_exchange} ·
              hourly
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-white/10 p-2 text-slate-400 transition-colors hover:bg-white/5 hover:text-slate-200"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
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
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  tickFormatter={(v: number) => `${v.toFixed(1)}%`}
                  stroke="rgba(255,255,255,0.1)"
                  width={50}
                />
                <Tooltip
                  contentStyle={{
                    background: "#0d121d",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 12,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "#94a3b8" }}
                  formatter={(value: number) => [
                    formatPercent(value, 3),
                    "Spread",
                  ]}
                />
                <Area
                  type="monotone"
                  dataKey="spread_pct"
                  stroke="#5b8cff"
                  strokeWidth={2}
                  fill="url(#spreadFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
