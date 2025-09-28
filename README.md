# FastPI – Crypto Intelligence API

FastPI is a Python-powered serverless API designed for Vercel. It consolidates real-time market snapshots from Bybit, Binance, and CoinCap while scraping authoritative crypto news outlets to deliver a broad, fast-moving view of the ecosystem.

## Features

- **Market aggregation** – Pulls 24h price, change, and volume metrics for any base/quote pair from Binance, Bybit, and CoinCap.
- **Editorial intelligence** – Scrapes latest headlines from CoinDesk, The Block, Blockworks, Cointelegraph, The Defiant, DL News, Protos, Decrypt, Messari, Glassnode Insights, plus CryptoPanic alerts via RSS without requiring API access.
- **Async-first stack** – Uses `httpx` with connection pooling, structured Pydantic models, and FastAPI + Mangum for Vercel compatibility.
- **Extensible design** – Centralised services layer with clear extension points for new data providers or caching.

## Project layout

```
api/                # Serverless entrypoint exposed on Vercel
fastpi/
  config.py        # Settings and provider endpoints
  http_client.py   # Shared async HTTP client lifecycle
  models/          # Pydantic schemas for market/news payloads
  services/        # Data aggregation logic
requirements.txt   # Runtime dependencies for the Vercel build
vercel.json        # Runtime configuration (Python 3.11)
```

## Getting started locally

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .[dev]  # optional: tooling & tests
uvicorn api.index:app --reload
```

The API exposes the following routes:

- `GET /health` – Simple health check.
- `GET /market/summary?base=BTC&quote=USDT` – Aggregated market data.
- `GET /news/aggregate?limit=6` – Latest headlines per publisher.

## Environment variables

| Variable | Description |
| --- | --- |
| `HTTP_TIMEOUT` | HTTP client timeout in seconds (default `10`). |
| `HTTP_MAX_CONNECTIONS` | Maximum concurrent connections (default `20`). |
| `HTTP_MAX_KEEPALIVE` | Maximum idle keepalive sockets (default `10`). |
| `HTTP_USER_AGENT` | Override the outbound user-agent string. |
| `COINCAP_API_KEY` | Optional bearer token for elevated CoinCap rate limits. |
| `COINMARKETCAP_API_KEY` | Reserved for future CoinMarketCap integration. |

CryptoPanic headlines are sourced via the public RSS feed, so no authentication is necessary.

Create a `.env` file locally or configure Vercel Project Environment Variables.

## Testing

Run the test suite after installing the optional `dev` extras:

```bash
pytest
```

Tests rely on `respx` to stub HTTP calls and do not hit external services.

## Deployment to Vercel

1. Push the repository to GitHub/GitLab/Bitbucket.
2. Create a new Vercel project pointing to the repo root.
3. Ensure the Python runtime is set to 3.11 (already enforced via `vercel.json`).
4. Add any required environment variables for HTTP tuning or exchange overrides.
5. Deploy – Vercel will install `requirements.txt`, build the API, and expose endpoints under `/api`.

---

FastPI is designed as a foundation; extend the services layer for additional exchanges, analytics, or persistence requirements as your product evolves.
