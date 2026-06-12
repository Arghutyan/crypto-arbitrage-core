# Crypto Arbitrage Engine (ACE/USDT Perpetuals)

Async core engine that monitors **ACE/USDT futures** on **Binance** and
**Gate.io**, computes the cross-exchange price spread, and logs price +
funding metrics to the console every 5 seconds.

## Metrics

For each exchange every cycle the engine fetches:

- **Last Price** of the perpetual futures contract
- **Current Funding Rate**

It then computes the **Spread (%)** as:

```
spread% = (binance_price - gate_price) / gate_price * 100
```

A positive spread means Binance is trading richer than Gate.

## Project layout

```
main.py                         # entry point + graceful shutdown
arbitrage/
├── config.py                   # settings + per-exchange config (env overridable)
├── models.py                   # MarketSnapshot, SpreadReport
├── engine.py                   # polling loop + spread computation
├── reporter.py                 # console formatting (swappable sink)
└── exchanges/
    ├── base.py                 # abstract ExchangeConnector (+ order-book seam)
    ├── ccxt_connector.py       # generic ccxt async implementation
    └── __init__.py             # build_connector() factory
```

The engine talks to exchanges only through `ExchangeConnector`. Each cycle it
asks every connector for a `MarketSnapshot` — it never knows whether the data
came from REST or a socket. That boundary is the integration seam for the
upcoming WebSocket order-book feed.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

Example output:

```
Time       | Binance Price  | Gate Price     | Spread     | Binance Fund | Gate Fund
-------------------------------------------------------------------------------------
03:48:12   | 1.23450        | 1.23310        | +0.1135%   | +0.0100%     | +0.0085%
03:48:17   | 1.23380        | 1.23290        | +0.0730%   | +0.0100%     | +0.0085%
```

Stop with `Ctrl+C` (SIGINT/SIGTERM are handled for clean shutdown).

## Configuration

Override defaults via environment variables:

| Variable              | Default     | Meaning                          |
| --------------------- | ----------- | -------------------------------- |
| `ARB_PAIR`            | `ACE/USDT`  | Display label for the pair       |
| `ARB_POLL_INTERVAL`   | `5`         | Seconds between polls            |
| `ARB_REQUEST_TIMEOUT` | `10`        | Per-request network timeout (s)  |

## Extending: WebSocket order book (next step)

The seam is already in place:

1. `ExchangeConnector.supports_order_book` / `watch_order_book()` in
   `exchanges/base.py` are defined and ready to override.
2. `MarketSnapshot` already carries `best_bid` / `best_ask` fields.

To add live order books, implement a connector (e.g. on top of `ccxt.pro`'s
`watch_order_book`), override those two members, and register it in
`exchanges/__init__.build_connector`. The engine and reporter need no changes.
```
