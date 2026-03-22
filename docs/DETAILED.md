# FollowTheFootPrints – Detailed Documentation

## Strategy Overview

The scanner looks for stocks that have printed a green leg-out candle from a fresh support zone and subsequently shown bullish follow-through.

| Step | What it does |
|------|--------------|
| **Leg-out detection** | Flags candles whose percentage move is ≥ 1.7× the average green move |
| **Support / resistance marking** | Identifies pivot lows (support) and pivot highs (resistance) using two structural patterns |
| **Demand zone** | A green leg-out that fires *from* a support zone with no resistance or red leg-in in the prior 6 bars |
| **Fresh zone** | Confirms the support has not been revisited since the DZ formed |
| **Follow-through** | Checks the next 3–4 candles for a bullish pattern (GGG, GRGG, GGRG) |
| **Output** | Only stocks with confirmed follow-through and a positive gain are written to the CSV. Each row includes `base_candle_low` and `base_candle_high` (the candle before the leg-out) to define the demand zone per chart. |

---

## Using as a Library

```python
from followthefootprints.analyzer import FollowTheFootPrints

scanner = FollowTheFootPrints(
    time_delta_days=365,
    index="nifty100",
    interval="1wk",   # "1wk" | "1d" | "1h" | "15m"
)
scanner.process()     # writes nifty100_weekly.csv
```

---

## Project Structure

```
followthefootprints/
├── pyproject.toml
├── README.md
├── docs/
│   └── DETAILED.md
├── src/
│   └── followthefootprints/
│       ├── __init__.py
│       ├── __main__.py     ← CLI (ftf command)
│       ├── analyzer.py     ← Core analysis engine
│       ├── indices.py      ← Stock index lists
│       └── exceptions.py   ← Custom exceptions
└── tests/
    ├── conftest.py         ← Shared fixtures
    └── test_analyzer.py    ← Unit tests
```

---

## Code → Documentation Map

| Code area changed | Document to update |
|-------------------|-------------------|
| `__main__` – index, interval, `time_delta_days` | README (CLI options) / DETAILED |
| `indices.py` – new index added/removed | README (Supported Indices) |
| `mark_leg_candle()` – threshold multipliers (1.7×, 2.0×) | DETAILED (Strategy Overview) |
| `mark_resistance_points()` / `mark_support_points()` – window size | DETAILED |
| `identify_possible_dz()` – lookback window | DETAILED |
| `get_good_dz()` – comparison logic | DETAILED |
| `is_it_fresh_zone()` – freshness condition | DETAILED |
| `get_stocks_with_follow_through()` – candle patterns | DETAILED |
| `add_percentage_of_change()` / final filter | DETAILED |
| Output filename pattern or CSV columns | README (how to run) / DETAILED |
| New dependency | README (Dependencies) |
| New file in `src/` | DETAILED (Project Structure) |
