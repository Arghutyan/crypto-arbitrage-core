/**
 * Skeleton placeholders shown while SWR fetches the first page of data.
 *
 * They mirror the real layout (stat cards, mobile cards, desktop table) so the
 * dashboard never flashes blank or jumps when the data resolves.
 */

function Shimmer({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-md bg-white/[0.06] ${className}`}
      aria-hidden
    />
  );
}

function StatCardSkeleton() {
  return (
    <div className="rounded-2xl border border-white/10 bg-base-850/60 p-4 backdrop-blur">
      <div className="flex items-center justify-between">
        <Shimmer className="h-3 w-20" />
        <Shimmer className="h-4 w-4 rounded-full" />
      </div>
      <Shimmer className="mt-3 h-7 w-24" />
    </div>
  );
}

function CardSkeleton() {
  return (
    <div className="rounded-2xl border border-white/10 bg-base-850/60 p-4 backdrop-blur">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <Shimmer className="h-5 w-20" />
          <Shimmer className="h-4 w-40" />
        </div>
        <Shimmer className="h-8 w-20" />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <Shimmer className="h-12 w-full rounded-xl" />
        <Shimmer className="h-12 w-full rounded-xl" />
      </div>
      <div className="mt-3 flex items-center justify-between border-t border-white/[0.06] pt-3">
        <Shimmer className="h-4 w-32" />
        <Shimmer className="h-9 w-28 rounded-lg" />
      </div>
    </div>
  );
}

function TableRowSkeleton() {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/[0.04] px-5 py-4 last:border-0">
      <Shimmer className="h-5 w-24" />
      <Shimmer className="h-5 w-40" />
      <Shimmer className="h-5 w-16" />
      <Shimmer className="h-5 w-16" />
      <Shimmer className="h-9 w-20 rounded-lg" />
    </div>
  );
}

/** Full first-load placeholder for the dashboard. */
export default function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <StatCardSkeleton key={i} />
        ))}
      </div>

      <div className="rounded-2xl border border-white/10 bg-base-850/40 p-4 backdrop-blur">
        <Shimmer className="h-8 w-64 max-w-full" />
      </div>

      {/* Phone: cards */}
      <div className="flex flex-col gap-3 lg:hidden">
        {Array.from({ length: 4 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>

      {/* Desktop: table */}
      <div className="hidden overflow-hidden rounded-2xl border border-white/10 bg-base-850/60 lg:block">
        {Array.from({ length: 6 }).map((_, i) => (
          <TableRowSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}
