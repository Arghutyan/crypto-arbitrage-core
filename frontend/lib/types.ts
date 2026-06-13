/**
 * Raw record shape returned by the FastAPI backend
 * (`GET /api/v1/spreads/latest`). Mirrors the `SpreadRecord` Pydantic model.
 */
export interface SpreadRecord {
  id: number;
  timestamp: string;
  pair: string;
  binance_price: number | null;
  gate_price: number | null;
  spread_pct: number | null;
  binance_funding: number | null;
  gate_funding: number | null;
}

/**
 * Normalized, view-friendly row derived from a {@link SpreadRecord}.
 * Buy/sell exchanges are inferred from the relative prices.
 */
export interface SpreadRow {
  id: number;
  timestamp: string;
  pair: string;
  buyExchange: string;
  buyPrice: number | null;
  sellExchange: string;
  sellPrice: number | null;
  spreadPct: number | null;
  /** Funding rate (fraction, e.g. 0.0001 == 0.01%) for the buy-side exchange. */
  buyFunding: number | null;
  /** Funding rate for the sell-side exchange. */
  sellFunding: number | null;
}
