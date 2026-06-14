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
  const urgent = nextMs != null && nextMs - Date.now() < 5 * 60 * 1000;

  return (
    <span
      className={[
        "inline-flex items-center gap-1 font-mono tabular-nums",
        urgent ? "text-amber-300" : "text-slate-400",
        className,
      ].join(" ")}
    >
      <Timer className="h-3.5 w-3.5" />
      {label}
    </span>
  );
}
