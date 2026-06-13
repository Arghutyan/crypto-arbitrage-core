# Spread+ Frontend

A dark-themed Next.js (App Router) dashboard for the crypto-arbitrage SaaS. It
fetches cross-exchange spreads from the FastAPI backend and renders them in a
live, color-coded table.

## Stack

- **Next.js 15** (App Router) + **React 19**
- **TypeScript**
- **Tailwind CSS**
- **Lucide React** icons

## Configuration

Copy the example env file and adjust the backend URL if needed:

```bash
cp .env.example .env.local
```

| Variable              | Default                 | Description                     |
| --------------------- | ----------------------- | ------------------------------- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL of the FastAPI backend |

## Develop locally

```bash
npm install
npm run dev
```

Open http://localhost:3000. The dashboard reads from
`${NEXT_PUBLIC_API_URL}/api/v1/spreads/latest`, so make sure the FastAPI service
is running.

## Production build

```bash
npm run build
npm start
```

## Docker

The multi-stage `Dockerfile` produces a minimal standalone image that listens
on port 3000.

```bash
# Build
docker build -t crypto-arbitrage-frontend .

# Run (point it at a reachable backend)
docker run --rm -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
  crypto-arbitrage-frontend
```
