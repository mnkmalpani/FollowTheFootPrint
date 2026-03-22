# FollowTheFootPrints

A demand-zone stock scanner that identifies potential buying opportunities using the *Follow The Footprints* strategy.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Package manager | [UV](https://docs.astral.sh/uv/) (recommended) or pip |
| Dependencies | yfinance, pandas, numpy, lxml, requests |
| Build | hatchling |

---

## Setup

```bash
# Install UV (if needed): https://docs.astral.sh/uv/
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone, enter project
git clone <repo-url>
cd <project-folder>

# Server setup: install deps + configure .env for Telegram
./setup.sh

# Or manually:
uv sync
cp .env.example .env
# Edit .env and add TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
```

## Dependencies

Dependencies are in `pyproject.toml`. Use `uv sync` for production; `uv sync --dev` for pytest.

---

## How to Run

```bash
# Weekly analysis of Nifty 100 (default)
uv run ftf

# Daily analysis
uv run ftf --mode daily

# Different index (nifty50, nifty200, nasdaq100)
uv run ftf --index nasdaq100

# Custom history window
uv run ftf --days 730 --log-level DEBUG
```

Results are written to `{index}_{mode}.csv` (e.g. `nifty100_weekly.csv`).

### Demand zone backtest (experiments)

Validate the approach using historical data: when price enters a demand zone, does it bounce back within 1–2 months?

```bash
# Backtest top 10 stocks from CSV + Thomas Cook example
uv run python experiments/demand_zone_backtest.py

# Thomas Cook example only
uv run python experiments/demand_zone_backtest.py --examples-only

# Or: make backtest
```

See [experiments/README.md](experiments/README.md) for details.

### Telegram alerts

When `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` are set (via `.env` or environment), the CSV and a summary are sent to Telegram after each run. Run `./setup.sh` to create `.env` from `.env.example`, then edit `.env` with your values.

```bash
# Option 1: .env file (recommended for server)
# After setup.sh, edit .env with your token and chat ID
uv run ftf

# Option 2: Export for current shell
export TELEGRAM_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
uv run ftf
```

To skip Telegram even when credentials are set, use `--no-telegram`.

### CLI options

| Option | Description | Default |
|--------|-------------|---------|
| `--mode` | Chart interval: weekly, daily | weekly |
| `--index` | Index: nifty100, nifty200, nifty50, nasdaq100 | nifty100 |
| `--days` | Calendar days of history | 365 |
| `--log-level` | DEBUG, INFO, WARNING, ERROR | INFO |
| `--no-telegram` | Skip Telegram even if credentials are set | — |

---

## Tests

```bash
uv sync --dev
uv run pytest
# Or: make test
```

Tests use synthetic data – no network calls.

---

## Supported Indices

Index constituents are **auto-fetched from Wikipedia** to avoid stale or delisted tickers (e.g. HDFC.NS).  
When a ticker returns no data (possibly delisted) or raises a delisted/timezone error, the index list is refreshed and the ticker is skipped.

| Key | Description |
|-----|-------------|
| nifty100 | NSE Nifty 100 (Nifty 50 + Next 50) |
| nifty200 | NSE Nifty 200 (fallback list when fetch unavailable) |
| nifty50 | NSE Nifty 50 |
| nasdaq100 | NASDAQ 100 |

---

For strategy details, algorithm steps, and project structure, see [docs/DETAILED.md](docs/DETAILED.md).
