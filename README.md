# Delta-Neutral Funding Arbitrage SaaS

A production-ready screener for **delta-neutral funding arbitrage** across 11
perpetual-swap venues. It finds cross-exchange price spreads, refines them with
real order-book slippage and live funding rates, then surfaces opportunities
through a **FastAPI** read API, a **Next.js 15** mobile-first dashboard, and an
**aiogram v3 Telegram** screener bot with per-user alerts.

> Convention: go **long** the cheaper venue and **short** the richer one. The
> price spread is captured on convergence while funding is farmed for the hold.

## Architecture

```
                         ┌─────────────┐
                         │ PostgreSQL  │  live_spreads cache + telegram_users filters
                         └──────┬──────┘
            writes cache /      │       reads cache / users
            pushes alerts       │
   ┌──────────────┐      ┌──────┴──────┐      ┌──────────────┐
   │   engine     │      │     api     │      │     bot      │
   │ scan + alert │      │  FastAPI    │      │  aiogram v3  │
   └──────┬───────┘      └──────┬──────┘      └──────────────┘
          │ ccxt                │ JSON               ▲ alerts
          ▼                     ▼                    │
   11 exchanges          ┌─────────────┐             │
                         │  frontend   │─────────────┘
                         │  Next.js 15 │
                         └─────────────┘
```

A **single backend image** runs three roles, selected by the container command:

| Role     | Command                                   | Purpose                                            |
| -------- | ----------------------------------------- | -------------------------------------------------- |
| `engine` | `python main.py`                          | Hybrid scan loop → cache spreads → trigger alerts  |
| `api`    | `uvicorn api.main:app --host 0.0.0.0 ...` | Read API for the frontend + on-demand spread chart |
| `bot`    | `python -m bot`                           | Telegram screener: registration, filters, alerts   |

## How the scan works (hybrid, anti-ban)

1. **Step 1 — cheap pass.** Concurrently `fetch_tickers` across all venues, group
   by asset, and keep only assets whose best mid-to-mid spread exceeds
   `ARB_MIN_RAW_SPREAD` (default `0.2%`).
2. **Step 2 — expensive pass.** For the top `ARB_TOP_N` (default 50) raw spreads,
   concurrently pull L2 order books and walk them for a fixed `ARB_ORDER_SIZE_USD`
   (default `$1000`) order to compute the **real spread** after slippage.
3. **Dynamic funding.** Funding intervals are parsed from each venue's payload
   (never hardcoded to 8h). The engine computes net 24h funding and projects
   **24h / 72h farm** estimates, plus the real `nextFundingTime`.

Venues scanned: Binance, Bybit, OKX, Gate.io, MEXC, KuCoin, HTX, Bitget,
Hyperliquid, Aster, XT (ccxt ids in `arbitrage/config.py`).

## API

| Endpoint                                          | Description                                                                 |
| ------------------------------------------------- | --------------------------------------------------------------------------- |
| `GET /health`                                     | Liveness/readiness probe.                                                    |
| `GET /api/v1/spreads/live?limit=100`              | Current cached opportunities (for the dashboard).                           |
| `GET /api/v1/spread-history/{asset}/{ex1}/{ex2}`  | 3-day hourly spread series fetched live via ccxt K-lines (not stored in DB). |

## Quick start (Docker Compose)

```bash
cp .env.example .env
# set TELEGRAM_BOT_TOKEN (from @BotFather) in .env
docker compose up --build
```

- Dashboard: http://localhost:3000
- API: http://localhost:8000 (`/health`, `/api/v1/spreads/live`)

## Local development (backend)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# point at a local/remote postgres
export DB_HOST=127.0.0.1 DB_PORT=5432 DB_USER=db_user \
       DB_PASSWORD=changeme DB_NAME=crypto_analytics

python main.py                                   # engine
uvicorn api.main:app --host 0.0.0.0 --port 8000  # api
python -m bot                                     # bot (needs TELEGRAM_BOT_TOKEN)
```

Frontend lives in `frontend/` (see `frontend/README.md`).

## Configuration

All settings are environment-overridable so the same image runs unchanged in
Compose and Kubernetes.

| Variable              | Default            | Used by         | Meaning                                   |
| --------------------- | ------------------ | --------------- | ----------------------------------------- |
| `DB_HOST`             | `postgres-service` | engine/api/bot  | PostgreSQL host                           |
| `DB_PORT`             | `5432`             | engine/api/bot  | PostgreSQL port                           |
| `DB_USER`             | `db_user`          | engine/api/bot  | PostgreSQL user                           |
| `DB_PASSWORD`         | `changeme`         | engine/api/bot  | PostgreSQL password                       |
| `DB_NAME`             | `crypto_analytics` | engine/api/bot  | PostgreSQL database                       |
| `TELEGRAM_BOT_TOKEN`  | _(empty)_          | engine, bot     | Telegram token; alerts are off if unset   |
| `ALERT_COOLDOWN_SECONDS` | `900`           | engine          | Per-user/opportunity alert cooldown       |
| `ARB_POLL_INTERVAL`   | `30`               | engine          | Seconds between scan cycles               |
| `ARB_MIN_RAW_SPREAD`  | `0.2`              | engine          | Step-1 minimum raw spread (%)             |
| `ARB_TOP_N`           | `50`               | engine          | Step-2 order books per cycle              |
| `ARB_ORDER_SIZE_USD`  | `1000`             | engine          | Notional for slippage estimation          |
| `ARB_REQUEST_TIMEOUT` | `20`               | engine          | Per-request ccxt timeout (s)              |
| `ARB_OB_CONCURRENCY`  | `20`               | engine          | Max concurrent order-book venues          |
| `CORS_ORIGINS`        | `*`                | api             | Allowed CORS origins                      |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | frontend   | API base URL for the browser              |

## Database

Two tables, created automatically on startup (`arbitrage/database.py`):

- **`live_spreads`** — atomically replaced cache of the latest opportunities.
- **`telegram_users`** — per-user alert filters: `min_spread`, `min_funding`,
  `excluded_exchanges` (JSONB), `alerts_enabled`.

Spread history is **never** persisted — it is fetched on demand from ccxt K-lines.

## Kubernetes

Manifests in `k8s/` (images pulled from GHCR, `ghcr-secret` expected in-cluster):

```bash
kubectl apply -f k8s/secrets.yaml      # set TELEGRAM_BOT_TOKEN first
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/deployment.yaml   # engine
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/bot.yaml
kubectl apply -f k8s/frontend.yaml
```

CI (`.github/workflows/build-and-push.yml`) builds the core + frontend images on
push to `main` and rolls out the engine, api, bot, and frontend deployments.
