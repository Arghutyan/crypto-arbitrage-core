/**
 * Live opportunity returned by `GET /api/v1/spreads/live`.
 * Mirrors the `LiveSpread` Pydantic model on the backend.
 */
export interface LiveSpread {
  asset: string;
  long_exchange: string;
  short_exchange: string;
  long_symbol: string | null;
  short_symbol: string | null;
  long_price: number | null;
  short_price: number | null;
  raw_spread_pct: number | null;
  real_spread_pct: number | null;
  long_funding: number | null;
  short_funding: number | null;
  net_funding_24h_pct: number | null;
  farm_24h_pct: number | null;
  farm_72h_pct: number | null;
  next_funding_ms: number | null;
}

/** One point of the on-demand spread history series. */
export interface SpreadHistoryPoint {
  time: number;
  ex1_price: number;
  ex2_price: number;
  spread_pct: number;
}

export interface SpreadHistoryResponse {
  asset: string;
  ex1: string;
  ex2: string;
  points: SpreadHistoryPoint[];
}
