"use client";

import { useCallback, useMemo, useState } from "react";
import useSWR from "swr";
import { Inbox, RefreshCw, TriangleAlert, X } from "lucide-react";
import {
  API_BASE_URL,
  blacklistSymbol,
  fetcher,
  LIVE_SPREADS_PATH,
} from "@/lib/api";
import type { LiveSpread } from "@/lib/types";
import { opportunityKey } from "@/lib/format";
import ChartModal from "./ChartModal";
import FilterBar, { type SpreadFilters } from "./FilterBar";
import OpportunityCard from "./OpportunityCard";
import OpportunityTable, { type SortKey, type SortState } from "./OpportunityTable";
import StatCards from "./StatCards";
import DashboardSkeleton from "./Skeleton";

const REFRESH_MS = 10_000;

function spreadValue(r: LiveSpread): number {
  return r.real_spread_pct ?? r.raw_spread_pct ?? 0;
}

function sortValue(r: LiveSpread, key: SortKey): number {
  if (key === "funding") return r.net_funding_24h_pct ?? -Infinity;
  return spreadValue(r);
}

export default function LiveDashboard() {
  const { data, error, isLoading, mutate } = useSWR<LiveSpread[]>(
    LIVE_SPREADS_PATH,
    fetcher,
    {
      refreshInterval: REFRESH_MS,
      keepPreviousData: true,
      revalidateOnFocus: false,
    },
  );

  const [filters, setFilters] = useState<SpreadFilters>({
    minSpread: 0,
    fundingPositive: false,
  });
  const [selected, setSelected] = useState<LiveSpread | null>(null);
  const [sort, setSort] = useState<SortState>({ key: "spread", dir: "desc" });
  const [assetFilter, setAssetFilter] = useState<string | null>(null);
  // Locally hidden assets (blacklisted from the UI) so they don't flicker back
  // in on the next refresh before the engine drops them server-side.
  const [hidden, setHidden] = useState<Set<string>>(new Set());

  const toggleSort = useCallback((key: SortKey) => {
    setSort((cur) =>
      cur.key === key
        ? { key, dir: cur.dir === "desc" ? "asc" : "desc" }
        : { key, dir: "desc" },
    );
  }, []);

  const handleBlacklist = useCallback(
    async (asset: string) => {
      // Optimistic: hide immediately and drop from the SWR cache.
      setHidden((cur) => new Set(cur).add(asset));
      mutate(
        (cur) => (cur ?? []).filter((r) => r.asset !== asset),
        { revalidate: false },
      );
      try {
        await blacklistSymbol(asset);
      } catch {
        // Roll back the optimistic hide on failure and refetch.
        setHidden((cur) => {
          const next = new Set(cur);
          next.delete(asset);
          return next;
        });
        mutate();
      }
    },
    [mutate],
  );

  const rows = useMemo(() => {
    let all = (data ?? []).filter((r) => !hidden.has(r.asset));
    if (assetFilter) {
      all = all.filter((r) => r.asset === assetFilter);
    }
    all = all.filter((r) => {
      if (spreadValue(r) < filters.minSpread) return false;
      if (filters.fundingPositive && (r.farm_24h_pct ?? 0) <= 0) return false;
      return true;
    });
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...all].sort(
      (a, b) => (sortValue(a, sort.key) - sortValue(b, sort.key)) * dir,
    );
  }, [data, filters, sort, assetFilter, hidden]);

  if (error && !data) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-rose-500/20 bg-rose-500/[0.06] px-4 py-16 text-center">
        <TriangleAlert className="h-8 w-8 text-rose-400" />
        <p className="text-sm font-medium text-rose-200">
          Couldn&apos;t reach the backend
        </p>
        <p className="mt-1 flex flex-wrap items-center justify-center gap-1.5 text-xs text-slate-600">
          <RefreshCw className="h-3.5 w-3.5" />
          Ensure the API is running at{" "}
          <code className="rounded bg-base-700/60 px-1 py-0.5 text-slate-400">
            {API_BASE_URL}
          </code>
        </p>
      </div>
    );
  }

  // First load: render a layout-matching skeleton instead of a blank screen.
  if (isLoading && !data) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="flex flex-col gap-6">
      <StatCards rows={data ?? []} />

      <section className="rounded-2xl border border-white/10 bg-base-850/40 p-4 backdrop-blur">
        <FilterBar filters={filters} onChange={setFilters} />
      </section>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Live Opportunities
          </h2>
          {assetFilter && (
            <button
              type="button"
              onClick={() => setAssetFilter(null)}
              className="inline-flex items-center gap-1.5 rounded-full border border-accent/40 bg-accent/15 px-3 py-1 text-xs font-medium text-accent transition-colors hover:bg-accent/25"
            >
              {assetFilter}
              <X className="h-3.5 w-3.5" />
              <span className="sr-only">Clear filter</span>
            </button>
          )}
        </div>
        <span className="inline-flex items-center gap-1.5 text-xs text-slate-600">
          {rows.length} shown · auto-refresh {REFRESH_MS / 1000}s
        </span>
      </div>

      {rows.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-white/10 bg-base-850/60 py-20 text-center">
          <Inbox className="h-8 w-8 text-slate-600" />
          <p className="text-sm font-medium text-slate-400">
            {assetFilter
              ? `No live opportunities for ${assetFilter}`
              : "No opportunities match your filters"}
          </p>
          <p className="max-w-sm text-xs text-slate-600">
            {assetFilter
              ? "Clear the asset filter or wait for the next scan cycle."
              : "Loosen the spread threshold or wait for the next scan cycle."}
          </p>
        </div>
      ) : (
        <>
          {/* Phone: card layout */}
          <div className="flex flex-col gap-3 lg:hidden">
            {rows.map((row) => (
              <OpportunityCard
                key={opportunityKey(row)}
                row={row}
                onViewChart={setSelected}
                onSelectAsset={setAssetFilter}
                onBlacklist={handleBlacklist}
              />
            ))}
          </div>

          {/* Desktop: rich table */}
          <div className="hidden lg:block">
            <OpportunityTable
              rows={rows}
              sort={sort}
              onToggleSort={toggleSort}
              onViewChart={setSelected}
              onSelectAsset={setAssetFilter}
              onBlacklist={handleBlacklist}
            />
          </div>
        </>
      )}

      <ChartModal opportunity={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
