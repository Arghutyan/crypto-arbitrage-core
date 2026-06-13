import type { SpreadRecord, SpreadRow } from "./types";

const EXCHANGE_BINANCE = "Binance";
const EXCHANGE_GATE = "Gate";

/**
 * Base URL of the FastAPI backend. Configurable at build/runtime via
 * `NEXT_PUBLIC_API_URL`; defaults to the local dev server.
 */
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

/**
 * Convert a raw backend record into a normalized row for the table.
 *
 * The backend tracks two venues (Binance & Gate). We treat the cheaper venue
 * as the "buy" side and the pricier as the "sell" side — the natural direction
 * of an arbitrage trade.
 */
export function toSpreadRow(record: SpreadRecord): SpreadRow {
  const { binance_price, gate_price } = record;

  // Default orientation: buy Binance / sell Gate.
  let buyExchange = EXCHANGE_BINANCE;
  let sellExchange = EXCHANGE_GATE;
  let buyPrice = binance_price;
  let sellPrice = gate_price;
  let buyFunding = record.binance_funding;
  let sellFunding = record.gate_funding;

  // Flip when Gate is cheaper, so "buy" is always the lower price.
  if (
    binance_price != null &&
    gate_price != null &&
    gate_price < binance_price
  ) {
    buyExchange = EXCHANGE_GATE;
    sellExchange = EXCHANGE_BINANCE;
    buyPrice = gate_price;
    sellPrice = binance_price;
    buyFunding = record.gate_funding;
    sellFunding = record.binance_funding;
  }

  return {
    id: record.id,
    timestamp: record.timestamp,
    pair: record.pair,
    buyExchange,
    buyPrice,
    sellExchange,
    sellPrice,
    spreadPct: record.spread_pct,
    buyFunding,
    sellFunding,
  };
}

/**
 * Fetch the latest spreads from the backend and normalize them for display.
 *
 * Runs on the server (App Router). `cache: "no-store"` keeps the dashboard
 * live rather than serving a statically cached snapshot.
 */
export async function fetchLatestSpreads(): Promise<SpreadRow[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/spreads/latest`, {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    throw new Error(
      `Backend returned ${res.status} ${res.statusText} for /api/v1/spreads/latest`,
    );
  }

  const data = (await res.json()) as SpreadRecord[];
  return data.map(toSpreadRow);
}
