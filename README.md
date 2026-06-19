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

# point at a local/remote postgres (use localhost when running outside compose)
export DATABASE_URL=postgresql+asyncpg://db_user:changeme@localhost:5432/crypto_analytics

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
| `DATABASE_URL`        | _(constructed)_    | engine/api/bot  | Full DSN; the connection standard (`+asyncpg` suffix is normalised) |
| `POSTGRES_USER`       | `db_user`          | db, engine/api/bot | PostgreSQL user (official image var); builds the DSN when `DATABASE_URL` is unset |
| `POSTGRES_PASSWORD`   | `changeme`         | db, engine/api/bot | PostgreSQL password (official image var) |
| `POSTGRES_DB`         | `crypto_analytics` | db, engine/api/bot | PostgreSQL database (official image var) |
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

---

## Infrastructure & DevOps

The production deployment is fully automated and cloud-native, spanning IaC provisioning, container orchestration, TLS termination, CI/CD, observability, and autonomous disaster recovery — with zero manual intervention required after initial bootstrap.

### Infrastructure as Code (Terraform)

All cloud resources are declared in `terraform/` and managed via Terraform with a remote backend for safe team collaboration.

- **Compute** — AWS `m7i-flex.large` EC2 instance (Intel Xeon Scalable, burstable vCPU credits) running Ubuntu 24.04 LTS (Noble), provisioned via `user_data` bootstrap script.
- **Storage** — Two S3 buckets:
  - `terraform-state-*` — remote Terraform state, with **versioning enabled**, **AES-256 server-side encryption**, and **S3 native state locking** (`use_lockfile = true`) replacing the legacy DynamoDB lock table.
  - `arbitcrypto-db-backups-*` — dedicated bucket for PostgreSQL database dumps (see Disaster Recovery below).
- **Root volume** — `gp3` EBS, dynamically resizable without instance stop via `aws_instance.root_block_device`.
- **Networking** — Security group allowing inbound SSH (22), HTTP (80), and HTTPS (443) only; all egress unrestricted.
- **Key management** — Ed25519 deployer key pair provisioned via `aws_key_pair`; private key never stored in state.

### Kubernetes (K3s)

The application runs on a single-node **K3s** cluster (lightweight Kubernetes) bootstrapped on the EC2 instance at provision time.

- **PostgreSQL** — deployed as a `StatefulSet` with a `PersistentVolumeClaim` backed by a local `gp3` volume, guaranteeing stable network identity and durable storage across pod restarts.
- **Application workloads** — `engine`, `api`, and `bot` run as separate `Deployment` objects, each independently scalable and rollable. The `frontend` Next.js app is similarly deployed as its own `Deployment`.
- **Image registry** — all images are pulled from **GitHub Container Registry (GHCR)**; in-cluster pull access is granted via a pre-provisioned `ghcr-secret` `imagePullSecret`.
- **Health probes** — `livenessProbe` and `readinessProbe` on the API (`GET /health`) prevent traffic from being routed to pods that have not fully initialised.

### Networking & Security

- **Traefik Ingress** — K3s ships with Traefik as the default Ingress controller; all external HTTP/HTTPS traffic is routed through it.
- **Automated TLS** — Traefik integrates with **Let's Encrypt** via the ACME protocol (`TLS-ALPN-01` challenge) to provision and auto-renew certificates, ensuring the API and dashboard are always served over HTTPS with zero manual certificate management.
- **Internal services** — PostgreSQL, Prometheus, and Grafana are not exposed through the Ingress; they are reachable only within the cluster or via SSH tunnelling (see Observability).

### CI/CD Pipeline

Defined in `.github/workflows/build-and-push.yml`, the pipeline triggers on every push to `main`:

1. **Build** — Docker Buildx builds the backend (`engine`/`api`/`bot`) and `frontend` images in parallel, leveraging layer caching to minimise build time.
2. **Push** — Multi-arch images are pushed to **GHCR** under the repository's package namespace, tagged with the commit SHA and `latest`.
3. **Zero-downtime rollout** — `kubectl rollout restart deployment/<name>` is issued for each workload. K3s performs a rolling update, bringing up pods with the new image before terminating old ones, guaranteeing uninterrupted service throughout the deploy.

### Observability

- **Prometheus** — scrapes node and pod metrics (CPU, memory, disk I/O, network) from the K3s cluster on a 15-second interval.
- **Grafana** — pre-configured dashboards visualise cluster health and application-level metrics sourced from Prometheus.
- **Secure access** — neither Prometheus nor Grafana is exposed to the public internet. Dashboards are accessed via **SSH local port forwarding**:
  ```bash
  ssh -L 3001:localhost:3001 -L 9090:localhost:9090 ubuntu@<server-ip>
  ```
  This eliminates the need for authentication middleware in front of the observability stack while keeping the attack surface minimal.

### Disaster Recovery & Autonomous Maintenance

All maintenance tasks are driven by server-side **cron jobs** — no external orchestration required.

| Cron schedule | Task | Detail |
| ------------- | ---- | ------ |
| Daily (00:00 UTC) | **PostgreSQL full dump → S3** | `pg_dumpall` output is piped through `gzip` and streamed directly to `arbitcrypto-db-backups-*` via `aws s3 cp -` (no temporary disk writes), preserving full cluster dumps with daily retention. |
| Weekly | **Container image pruning** | `crictl rmi --prune` removes dangling and unused images from the containerd image store, reclaiming disk space that would otherwise accumulate from rolling deployments. |
| Continuous (K3s config) | **Log rotation** | K3s container log rotation is configured with strict `max-size` and `max-file` limits, preventing unbounded log growth from causing disk pressure on the single-node cluster. |

> **Recovery objective** — in the event of instance failure, a full environment can be restored by running `terraform apply` (new EC2 instance + EBS) followed by restoring the latest S3 dump with `psql < dump.sql.gz`, with no data loss beyond the most recent daily window.
