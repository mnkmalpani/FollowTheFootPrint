# Agent Instructions – FollowTheFootPrints

This file gives high-level context for AI agents working on this repo.

## Project Summary

FollowTheFootPrints is a **demand-zone stock scanner** for NSE/NASDAQ indices. It uses the *Follow The Footprints* strategy (leg-out candles, support zones, follow-through) and writes CSV results. Optional Telegram alerts when env vars are set.

## Before Making Changes

1. **Read [.cursor/rules/repo-structure.mdc](.cursor/rules/repo-structure.mdc)** – coding conventions, directory layout, where logic lives.
2. **Tests**: Never make real network calls. Use synthetic fixtures in `conftest.py`.
3. **Docs**: When you change `src/` logic or CLI, update `README.md` or `docs/DETAILED.md` per [sync-docs.mdc](.cursor/rules/sync-docs.mdc).

## Common Commands

| Command | Purpose |
|---------|---------|
| `uv sync --dev` | Install deps including pytest |
| `uv run pytest` | Run tests |
| `uv run ftf` | Run scanner (default: nifty100, weekly) |
| `uv run ftf --mode daily --index nifty50` | Different mode/index |
| `make backtest` | Validate demand zone bounce-back (experiments) |
| `./setup.sh` | First-time setup: uv sync + create .env from .env.example |

## Important Paths

- **Core logic**: `src/followthefootprints/analyzer.py`
- **Indices / tickers**: `src/followthefootprints/indices.py`, `index_fetcher.py`
- **CLI**: `src/followthefootprints/__main__.py`
- **Legacy script**: `src/weekly_low_gemini.py` – standalone, uses different data source (niftyindices.com). Not part of the installable package.

## Output

- CSV files: `{index}_{mode}.csv` (e.g. `nifty100_weekly.csv`)
- Listed in `.gitignore` – do not commit.

## Adding New Features

- **New index**: See "Adding New Indices" in repo-structure.mdc.
- **New analysis step**: See "Adding New Signals / Analysis Steps" in repo-structure.mdc.
- **New rule**: See [cursor-rules.mdc](.cursor/rules/cursor-rules.mdc).
