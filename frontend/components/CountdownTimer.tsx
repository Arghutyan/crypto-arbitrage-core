"use client";

import { useEffect, useState } from "react";
import { Timer } from "lucide-react";
import { formatCountdown } from "@/lib/format";

interface CountdownTimerProps {
  nextMs: number | null;
  className?: string;
}

/** Live ticking countdown to the next funding settlement. */
export default function CountdownTimer({
  nextMs,
  className = "",
}: CountdownTimerProps) {
  const [, setTick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const label = formatCountdown(nextMs);
  const remainingMs = nextMs != null ? nextMs - Date.now() : null;
  // Tiered urgency: <5m is critical (red), <1h is soon (orange) and pulses.
  const critical = remainingMs != null && remainingMs > 0 && remainingMs < 5 * 60 * 1000;
  const soon =
    remainingMs != null && remainingMs > 0 && remainingMs < 60 * 60 * 1000;

  const tone = critical
    ? "text-rose-400"
    : soon
      ? "text-amber-400"
      : "text-slate-400";

  return (
    <span
      className={[
        "inline-flex items-center gap-1 font-mono tabular-nums",
        tone,
        soon ? "animate-pulse font-semibold" : "",
        className,
      ].join(" ")}
    >
      <Timer className="h-3.5 w-3.5" />
      {label}
    </span>
  );
}
