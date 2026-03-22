# Demand Zone Experiments

## `demand_zone_backtest.py`

Validates the FollowTheFootPrints approach using historical data: when price enters a demand zone, does it bounce back within 1–2 months?

### Logic

1. **Zone definition**: Demand zone = **base candle** (candle before the leg-out) low–high range (per chart). Uses `base_candle_low` / `base_candle_high` from CSV when present; else derives from OHLC by finding the candle before the CSV date. Fallback: `green_leg_out_low_price ± 3%`.
2. **Entry event**: A week where the candle low touches the zone (price re-enters).
3. **Bounce**: Within 4 weeks (1 month) or 8 weeks (2 months), does close exceed entry low by ≥5%?

### Usage

```bash
# Backtest top 10 stocks from nifty100_weekly.csv + Thomas Cook example
uv run python experiments/demand_zone_backtest.py

# Backtest top 5 only
uv run python experiments/demand_zone_backtest.py --top 5

# Thomas Cook example only
uv run python experiments/demand_zone_backtest.py --examples-only

# Use a different CSV
uv run python experiments/demand_zone_backtest.py --csv nifty50_weekly.csv
```

### Output

- **entries**: Number of historical zone-entry events.
- **success_rate_1m / success_rate_2m**: % of entries that bounced within 4 / 8 weeks.
- **avg_gain_when_bounced**: Average gain when a bounce occurred.
- **Example bounce**: One example per stock with date and price range when a bounce was observed (entry date, zone range, bounce date, gain %).
- **Stocks nearest to demand zone**: Ranked by how close current price is to the zone – closer = higher likelihood of a bounce opportunity.
- **Ranked by likelihood**: Score = 0.4×1m + 0.6×2m.

### Example: Thomas Cook

Thomas Cook (THOMASCOOK.NS) is included as a manual example with demand zone 80–87 (from chart analysis). Historically, when price entered this zone, it bounced ~44% of the time within 1–2 months, with an average gain of ~19% when it did bounce.
