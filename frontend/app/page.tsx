import { Activity, Zap } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import LiveDashboard from "@/components/LiveDashboard";

export default function DashboardPage() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
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
              Delta-neutral funding arbitrage screener
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

      <LiveDashboard />

      <footer className="mt-10 border-t border-white/10 pt-6 text-center text-xs text-slate-600">
        Spread+ · Real-time across 10 venues · For research use only
      </footer>
    </main>
  );
}
