import { Activity, RefreshCw, TriangleAlert, Zap } from "lucide-react";
import { API_BASE_URL, fetchLatestSpreads } from "@/lib/api";
import type { SpreadRow } from "@/lib/types";
import FilterBar from "@/components/FilterBar";
import SpreadTable from "@/components/SpreadTable";
import StatCards from "@/components/StatCards";

// Always render fresh — this is a live trading view.
export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let rows: SpreadRow[] = [];
  let error: string | null = null;

  try {
    rows = await fetchLatestSpreads();
  } catch (err) {
    error = err instanceof Error ? err.message : "Unknown error";
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Brand header */}
      <header className="mb-8 flex flex-col gap-6 border-b border-white/10 pb-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-accent to-accent-muted shadow-glow">
            <Zap className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-white">
              Spread<span className="text-accent">+</span>
            </h1>
            <p className="text-sm text-slate-500">
              Cross-exchange crypto arbitrage dashboard
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
            </span>
            Live
          </span>
          <span className="hidden items-center gap-1.5 text-xs text-slate-500 sm:flex">
            <Activity className="h-3.5 w-3.5" />
            {API_BASE_URL}
          </span>
        </div>
      </header>

      {/* Filter bar */}
      <section className="mb-6 rounded-2xl border border-white/10 bg-base-850/40 p-4 backdrop-blur">
        <FilterBar />
      </section>

      {error ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-rose-500/20 bg-rose-500/[0.06] py-16 text-center">
          <TriangleAlert className="h-8 w-8 text-rose-400" />
          <p className="text-sm font-medium text-rose-200">
            Couldn&apos;t reach the backend
          </p>
          <p className="max-w-md text-xs text-slate-500">{error}</p>
          <p className="mt-1 inline-flex items-center gap-1.5 text-xs text-slate-600">
            <RefreshCw className="h-3.5 w-3.5" />
            Ensure the FastAPI service is running at{" "}
            <code className="rounded bg-base-700/60 px-1 py-0.5 text-slate-400">
              {API_BASE_URL}
            </code>
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          <StatCards rows={rows} />

          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Latest Spreads
            </h2>
            <span className="text-xs text-slate-600">
              {rows.length} record{rows.length === 1 ? "" : "s"}
            </span>
          </div>

          <SpreadTable rows={rows} />
        </div>
      )}

      <footer className="mt-10 border-t border-white/10 pt-6 text-center text-xs text-slate-600">
        Spread+ · Data refreshes on each load · For research use only
      </footer>
    </main>
  );
}
