"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { Inbox, RefreshCw, TriangleAlert } from "lucide-react";
import { API_BASE_URL, fetcher, LIVE_SPREADS_PATH } from "@/lib/api";
import type { LiveSpread } from "@/lib/types";
import { opportunityKey } from "@/lib/format";
import ChartModal from "./ChartModal";
import FilterBar, { type SpreadFilters } from "./FilterBar";
import OpportunityCard from "./OpportunityCard";
import OpportunityTable from "./OpportunityTable";
import StatCards from "./StatCards";

const REFRESH_MS = 10_000;

export default function LiveDashboard() {
  const { data, error, isLoading } = useSWR<LiveSpread[]>(
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

  const rows = useMemo(() => {
    const all = data ?? [];
    return all.filter((r) => {
      const spread = r.real_spread_pct ?? r.raw_spread_pct ?? 0;
      if (spread < filters.minSpread) return false;
      if (filters.fundingPositive && (r.farm_24h_pct ?? 0) <= 0) return false;
      return true;
    });
  }, [data, filters]);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-rose-500/20 bg-rose-500/[0.06] py-16 text-center">
        <TriangleAlert className="h-8 w-8 text-rose-400" />
        <p className="text-sm font-medium text-rose-200">
          Couldn&apos;t reach the backend
        </p>
        <p className="mt-1 inline-flex items-center gap-1.5 text-xs text-slate-600">
          <RefreshCw className="h-3.5 w-3.5" />
          Ensure the API is running at{" "}
          <code className="rounded bg-base-700/60 px-1 py-0.5 text-slate-400">
            {API_BASE_URL}
          </code>
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <StatCards rows={data ?? []} />

      <section className="rounded-2xl border border-white/10 bg-base-850/40 p-4 backdrop-blur">
        <FilterBar filters={filters} onChange={setFilters} />
      </section>

      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Live Opportunities
        </h2>
        <span className="inline-flex items-center gap-1.5 text-xs text-slate-600">
          {isLoading && !data ? (
            <>
              <RefreshCw className="h-3.5 w-3.5 animate-spin" /> loading…
            </>
          ) : (
            <>
              {rows.length} shown · auto-refresh {REFRESH_MS / 1000}s
            </>
          )}
        </span>
      </div>

      {rows.length === 0 && !isLoading ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-white/10 bg-base-850/60 py-20 text-center">
          <Inbox className="h-8 w-8 text-slate-600" />
          <p className="text-sm font-medium text-slate-400">
            No opportunities match your filters
          </p>
          <p className="max-w-sm text-xs text-slate-600">
            Loosen the spread threshold or wait for the next scan cycle.
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
              />
            ))}
          </div>

          {/* Desktop: rich table */}
          <div className="hidden lg:block">
            <OpportunityTable rows={rows} onViewChart={setSelected} />
          </div>
        </>
      )}

      <ChartModal opportunity={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
