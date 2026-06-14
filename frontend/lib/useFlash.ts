"use client";

import { useEffect, useRef, useState } from "react";

export type FlashDirection = "up" | "down" | null;

/**
 * Track a numeric value across renders and briefly flag whether it moved up or
 * down, so the UI can flash green/red on live updates.
 */
export function useFlash(value: number | null, durationMs = 1200): FlashDirection {
  const prev = useRef<number | null>(value);
  const [dir, setDir] = useState<FlashDirection>(null);

  useEffect(() => {
    const previous = prev.current;
    prev.current = value;

    if (value == null || previous == null || value === previous) {
      return;
    }
    setDir(value > previous ? "up" : "down");
    const id = setTimeout(() => setDir(null), durationMs);
    return () => clearTimeout(id);
  }, [value, durationMs]);

  return dir;
}

/** Tailwind classes for a flash direction. */
export function flashClass(dir: FlashDirection): string {
  if (dir === "up") return "bg-emerald-500/15 transition-colors duration-700";
  if (dir === "down") return "bg-rose-500/15 transition-colors duration-700";
  return "transition-colors duration-700";
}
