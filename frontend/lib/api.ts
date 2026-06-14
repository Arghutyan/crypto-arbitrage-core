import type { LiveSpread, SpreadHistoryResponse } from "./types";

/**
 * Base URL of the FastAPI backend. Configurable via `NEXT_PUBLIC_API_URL`;
 * defaults to the local dev server.
 */
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

/** Generic JSON fetcher used by SWR. */
export async function fetcher<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Backend returned ${res.status} for ${path}`);
  }
  return (await res.json()) as T;
}

export const LIVE_SPREADS_PATH = "/api/v1/spreads/live";

export function fetchLiveSpreads(): Promise<LiveSpread[]> {
  return fetcher<LiveSpread[]>(LIVE_SPREADS_PATH);
}

export function spreadHistoryPath(
  asset: string,
  ex1: string,
  ex2: string,
): string {
  return `/api/v1/spread-history/${encodeURIComponent(
    asset,
  )}/${encodeURIComponent(ex1)}/${encodeURIComponent(ex2)}`;
}

export function fetchSpreadHistory(
  asset: string,
  ex1: string,
  ex2: string,
): Promise<SpreadHistoryResponse> {
  return fetcher<SpreadHistoryResponse>(spreadHistoryPath(asset, ex1, ex2));
}
