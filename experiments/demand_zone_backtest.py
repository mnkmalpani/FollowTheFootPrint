#!/usr/bin/env python3
"""
Demand Zone Bounce-Back Validator

Validates the FollowTheFootPrints approach by backtesting:
- Demand zone = base candle body max (max of open/close) as top,
  candle low (full wick) as bottom.
- When price historically enters this zone, does it bounce back within 1–2 months?

Reads from FTF CSV (uses base_candle_low/high when present) or derives zone
from OHLC by finding the candle before the CSV date. Fallback: green_leg_out_low ± 3%.

Usage:
  uv run python experiments/demand_zone_backtest.py
  uv run python experiments/demand_zone_backtest.py --csv nifty100_weekly.csv
  uv run python experiments/demand_zone_backtest.py --examples-only
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M",
)
logger = logging.getLogger(__name__)

# --- Constants ---
ZONE_BAND_PCT = 0.03  # Zone = green_leg_out_low ± 3%
BOUNCE_MIN_PCT = 5.0  # Minimum gain from zone entry to count as "bounced"
WEEKS_1_MONTH = 4
WEEKS_2_MONTHS = 8
HISTORY_DAYS = 1825  # ~5 years for backtest

# Manual examples: stock -> (zone_low, zone_high, base_candle_body_pct) for known demand zones
# Thomas Cook: zone ~80–87 (from chart); bounced from ~70–80 in Jul 2023
# ITC: ideal textbook setup - base candle week of Jun 20 2022 (tight, body%=26.8),
#      leg-out Jun 27 2022, clean GGG follow-through. Zone = base candle low–high.
MANUAL_EXAMPLES: dict[str, tuple[float, float, float]] = {
    "THOMASCOOK.NS": (80.0, 87.0, float("nan")),
    "ITC.NS": (221.75, 229.81, 26.8),  # Jun 20 2022 base candle
}


def fetch_weekly_ohlc(ticker: str, days: int = HISTORY_DAYS) -> pd.DataFrame:
    """Fetch weekly OHLC from yfinance, normalised columns."""
    end = datetime.now()
    start = end - timedelta(days=days)
    raw = yf.download(
        ticker,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        interval="1wk",
        rounding=True,
        progress=False,
    )
    if raw.empty:
        return pd.DataFrame()

    df = raw.reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[~df.isna().any(axis=1)].copy()
    df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Date": "Datetime",
        },
        inplace=True,
    )
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["open", "high", "low", "close"])


def zone_range_from_low(low_price: float, band_pct: float = ZONE_BAND_PCT) -> tuple[float, float]:
    """Return (zone_low, zone_high) for a given green_leg_out_low."""
    band = low_price * band_pct
    return (low_price - band, low_price + band)


def find_zone_entries(
    df: pd.DataFrame,
    zone_low: float,
    zone_high: float,
) -> list[dict]:
    """
    Find all weeks where price 'entered' the demand zone (weekly low <= zone_high).
    Returns list of {iloc_idx, datetime, low, close, zone_touch_price}.
    """
    entries: list[dict] = []
    df = df.reset_index(drop=True)
    for iloc_idx in range(len(df)):
        row = df.iloc[iloc_idx]
        low = float(row["low"])
        if low <= zone_high and low >= zone_low * 0.95:
            touch = min(low, zone_high)
            entries.append({
                "iloc_idx": iloc_idx,
                "datetime": row["Datetime"],
                "low": low,
                "close": float(row["close"]),
                "zone_touch_price": touch,
            })
    return entries


def did_bounce(
    df: pd.DataFrame,
    entry_idx: int,
    entry_low: float,
    weeks_ahead: int,
    min_gain_pct: float = BOUNCE_MIN_PCT,
) -> tuple[bool, float | None, object]:
    """
    Check if within `weeks_ahead` weeks, close exceeded entry_low + min_gain_pct.
    Returns (bounced, max_gain_pct, bounce_date).
    """
    future = df.iloc[entry_idx + 1 : entry_idx + weeks_ahead + 1]
    if future.empty:
        return False, None, None

    for _, row in future.iterrows():
        close = float(row["close"])
        gain_pct = ((close - entry_low) / entry_low) * 100
        if gain_pct >= min_gain_pct:
            dt = row.get("Datetime", row.get("datetime"))
            return True, gain_pct, dt

    max_close = future["close"].max()
    max_gain = ((max_close - entry_low) / entry_low) * 100 if max_close is not None else None
    return False, max_gain, None


def _distance_to_zone(current_price: float, zone_low: float, zone_high: float) -> float:
    """Return distance from current price to demand zone. 0 = inside zone."""
    if zone_low <= current_price <= zone_high:
        return 0.0
    return min(abs(current_price - zone_low), abs(current_price - zone_high))


def run_backtest(
    ticker: str,
    zone_low: float,
    zone_high: float,
    df: pd.DataFrame,
) -> dict:
    """Run backtest for one stock. Returns stats dict."""
    df = df.reset_index(drop=True)
    entries = find_zone_entries(df, zone_low, zone_high)

    # Latest close for proximity-to-zone calculation
    latest_close = float(df["close"].iloc[-1]) if not df.empty else 0.0
    distance_to_zone = _distance_to_zone(latest_close, zone_low, zone_high)
    pct_from_zone = (distance_to_zone / zone_low * 100) if zone_low else 0.0

    if not entries:
        return {
            "ticker": ticker,
            "zone_low": zone_low,
            "zone_high": zone_high,
            "entries": 0,
            "bounced_1m": 0,
            "bounced_2m": 0,
            "success_rate_1m": 0.0,
            "success_rate_2m": 0.0,
            "avg_gain_when_bounced": None,
            "example_bounce": None,
            "current_price": latest_close,
            "distance_to_zone": distance_to_zone,
            "pct_from_zone": pct_from_zone,
        }

    bounced_1m = 0
    bounced_2m = 0
    gains: list[float] = []
    example_bounce: dict | None = None

    for ent in entries:
        iloc_idx = ent["iloc_idx"]
        entry_low = ent["low"]

        b1, g1, d1 = did_bounce(df, iloc_idx, entry_low, WEEKS_1_MONTH)
        b2, g2, d2 = did_bounce(df, iloc_idx, entry_low, WEEKS_2_MONTHS)
        if b1:
            bounced_1m += 1
        if b2:
            bounced_2m += 1
        if g1 is not None and b1:
            gains.append(g1)
        elif g2 is not None and b2:
            gains.append(g2)

        # Capture first example bounce for output
        if example_bounce is None and (b1 or b2):
            entry_date = ent["datetime"]
            entry_date_str = (
                entry_date.strftime("%Y-%m-%d") if hasattr(entry_date, "strftime") else str(entry_date)
            )
            bounce_date = d1 if b1 else d2
            bounce_date_str = (
                bounce_date.strftime("%Y-%m-%d") if bounce_date and hasattr(bounce_date, "strftime") else str(bounce_date)
            )
            gain = g1 if b1 else g2
            example_bounce = {
                "entry_date": entry_date_str,
                "entry_low": entry_low,
                "zone_range": f"{zone_low:.1f}-{zone_high:.1f}",
                "bounce_date": bounce_date_str,
                "gain_pct": gain,
            }

    n = len(entries)
    return {
        "ticker": ticker,
        "zone_low": zone_low,
        "zone_high": zone_high,
        "entries": n,
        "bounced_1m": bounced_1m,
        "bounced_2m": bounced_2m,
        "success_rate_1m": (bounced_1m / n * 100) if n else 0,
        "success_rate_2m": (bounced_2m / n * 100) if n else 0,
        "avg_gain_when_bounced": sum(gains) / len(gains) if gains else None,
        "example_bounce": example_bounce,
        "current_price": latest_close,
        "distance_to_zone": distance_to_zone,
        "pct_from_zone": pct_from_zone,
    }


def _is_base_candle(row: pd.Series) -> bool:
    """Return True when the candle qualifies as a consolidation base.

    Rules (mirrors FollowTheFootPrints.is_it_base_candle):
    - Body ≤ 50 % of full range.
    - Lower wick ≤ 60 % of full range (rejects hammers).
    - Upper wick ≤ 60 % of full range (rejects shooting stars).
    """
    o, c = float(row["open"]), float(row["close"])
    l, h = float(row["low"]), float(row["high"])
    full_range = abs(h - l)
    if full_range == 0:
        return True
    if abs(c - o) / full_range * 100 > 50.0:
        return False
    if (min(o, c) - l) / full_range > 0.6:
        return False
    if (h - max(o, c)) / full_range > 0.6:
        return False
    return True


def _find_base_candle(candidates: pd.DataFrame) -> pd.Series | None:
    """Among up to 3 candles before the leg-out, return the tightest base candle.

    Picks the row with the smallest total range (high−low) that passes the
    base-candle rules (body ≤ 50%, not a hammer/shooting-star).
    Fallback: last row of candidates.
    """
    if candidates.empty:
        return None

    best_row = None
    best_range = float("inf")
    for _, row in candidates.iterrows():
        if not _is_base_candle(row):
            continue
        candle_range = abs(float(row["high"]) - float(row["low"]))
        if candle_range < best_range:
            best_range = candle_range
            best_row = row

    return best_row if best_row is not None else candidates.iloc[-1]


def _resolve_zone_from_base_candle(
    df: pd.DataFrame,
    dz_date_str: str,
    fallback_low: float,
) -> tuple[float, float]:
    """
    Derive demand zone from the tightest base candle within 3 candles before
    the leg-out date.
    Zone top  = body max (max of open/close, excluding upper wick).
    Zone bottom = candle low (full low, including lower wick).
    Fallback: fallback_low ± 3%.
    """
    if df.empty:
        return zone_range_from_low(fallback_low)

    df = df.copy()
    df["Datetime"] = pd.to_datetime(df["Datetime"])
    target = pd.to_datetime(dz_date_str)

    # Find leg-out row and take up to 3 preceding rows as candidates
    after = df[df["Datetime"] >= target]
    if after.empty:
        return zone_range_from_low(fallback_low)
    leg_out_pos = df.index.get_loc(after.index[0])
    if leg_out_pos <= 0:
        return zone_range_from_low(fallback_low)

    start_pos = max(0, leg_out_pos - 3)
    candidates = df.iloc[start_pos:leg_out_pos]
    base = _find_base_candle(candidates)
    if base is None:
        return zone_range_from_low(fallback_low)

    base_body_high = max(float(base["open"]), float(base["close"]))
    # Zone floor = min low across all candidate candles (full consolidation area).
    zone_low = float(candidates["low"].min())
    if zone_low >= base_body_high:
        return zone_range_from_low(fallback_low)
    return (zone_low, base_body_high)


def _parse_float(val: str) -> float | None:
    """Return float or None for empty/invalid strings."""
    if val and val.strip():
        try:
            return float(val.strip())
        except ValueError:
            pass
    return None


def load_csv_stocks(csv_path: str) -> list[dict]:
    """Load stocks from FTF CSV.

    Returns list of dicts with keys:
      ticker, dz_date, green_leg_out_low,
      base_candle_low?, base_candle_high?, base_candle_body_pct?
    """
    rows: list[dict] = []
    path = Path(csv_path)
    if not path.exists():
        logger.warning("CSV not found: %s", csv_path)
        return rows

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            ticker = r.get("stock", "").strip()
            low_str = r.get("green_leg_out_low_price", "")
            dz_date = r.get("date", "").strip()
            if not ticker or not low_str:
                continue
            low_price = _parse_float(low_str)
            if low_price is None:
                continue
            rows.append({
                "ticker": ticker,
                "dz_date": dz_date or None,
                "green_leg_out_low": low_price,
                "base_candle_low": _parse_float(r.get("base_candle_low", "")),
                "base_candle_high": _parse_float(r.get("base_candle_high", "")),
                "base_candle_body_pct": _parse_float(r.get("base_candle_body_pct", "")),
            })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate demand zone bounce-back using historical data"
    )
    parser.add_argument(
        "--csv",
        default="nifty100_weekly.csv",
        help="FTF output CSV to backtest (default: nifty100_weekly.csv)",
    )
    parser.add_argument(
        "--examples-only",
        action="store_true",
        help="Run only manual examples (e.g. Thomas Cook)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Top N stocks from CSV to test (default: 10)",
    )
    args = parser.parse_args()

    stocks_to_test: list[dict] = []

    if not args.examples_only:
        stocks_to_test.extend(load_csv_stocks(args.csv)[: args.top])
        logger.info("Loaded %d stocks from %s", len(stocks_to_test), args.csv)

    for ticker, (z_low, z_high, base_body_pct) in MANUAL_EXAMPLES.items():
        if not any(s.get("ticker") == ticker for s in stocks_to_test):
            stocks_to_test.append({
                "ticker": ticker,
                "zone_low": z_low,
                "zone_high": z_high,
                "base_candle_body_pct": base_body_pct,
            })
    logger.info("Running backtest on %d stocks", len(stocks_to_test))

    results: list[dict] = []
    for item in stocks_to_test:
        ticker = item["ticker"]
        df = fetch_weekly_ohlc(ticker)
        if df.empty:
            logger.warning("No data for %s – skipping", ticker)
            continue

        # Resolve zone: explicit from CSV/manual, or derived from OHLC base candle
        if "zone_low" in item and "zone_high" in item:
            z_low, z_high = item["zone_low"], item["zone_high"]
        elif item.get("base_candle_low") is not None and item.get("base_candle_high") is not None:
            z_low = item["base_candle_low"]
            z_high = item["base_candle_high"]
        elif item.get("dz_date"):
            z_low, z_high = _resolve_zone_from_base_candle(
                df, item["dz_date"], item["green_leg_out_low"]
            )
        else:
            z_low, z_high = zone_range_from_low(item["green_leg_out_low"])

        stats = run_backtest(ticker, z_low, z_high, df)
        # Carry forward the base candle quality metric from CSV / manual examples
        stats["base_candle_body_pct"] = item.get("base_candle_body_pct")
        results.append(stats)
        logger.info(
            "%s: %d entries, 1m bounce %.0f%%, 2m bounce %.0f%%",
            ticker,
            stats["entries"],
            stats["success_rate_1m"],
            stats["success_rate_2m"],
        )

    if not results:
        logger.error("No results. Check CSV path or ticker symbols.")
        return 1

    df_out = pd.DataFrame(results)
    df_out["score"] = (
        df_out["success_rate_2m"] * 0.6 + df_out["success_rate_1m"] * 0.4
    )
    df_out = df_out.sort_values("score", ascending=False)

    print("\n" + "=" * 80)
    print("DEMAND ZONE BOUNCE-BACK VALIDATION")
    print("=" * 80)
    print(
        f"Zone: base candle (low to body-max) | Bounce threshold: +{BOUNCE_MIN_PCT}% | "
        f"Lookahead: 4wk (1m) / 8wk (2m)"
    )
    print("=" * 80)
    print(
        df_out[
            [
                "ticker",
                "zone_low",
                "zone_high",
                "current_price",
                "entries",
                "bounced_1m",
                "bounced_2m",
                "success_rate_1m",
                "success_rate_2m",
                "avg_gain_when_bounced",
            ]
        ].to_string(index=False)
    )

    # Example bounce per stock
    print("\n--- Example bounce (date / price range) ---")
    for _, r in df_out.iterrows():
        ex = r.get("example_bounce")
        if ex and isinstance(ex, dict):
            print(
                f"  {r['ticker']}: Zone {ex['zone_range']} | "
                f"Entry {ex['entry_date']} @ {ex['entry_low']:.1f} | "
                f"Bounced {ex['bounce_date']} +{ex['gain_pct']:.1f}%"
            )
        else:
            print(f"  {r['ticker']}: (no bounce observed in backtest)")

    # Stocks nearest to demand zone (higher likelihood to bounce)
    df_near = df_out.copy()
    df_near = df_near.sort_values("distance_to_zone", ascending=True)
    print("\n--- Stocks nearest to demand zone (current price vs zone) ---")
    print("base_body% = body of base candle as % of its range; lower = tighter/better base\n")
    for _, r in df_near.iterrows():
        status = "IN ZONE" if r["distance_to_zone"] == 0 else f"{r['pct_from_zone']:.1f}% away"
        bpct = r.get("base_candle_body_pct")
        quality = f"base_body={bpct:.0f}%" if bpct is not None and not pd.isna(bpct) else "base_body=?"
        print(
            f"  {r['ticker']}: current {r['current_price']:.1f} | "
            f"zone {r['zone_low']:.1f}-{r['zone_high']:.1f} | {status} | {quality}"
        )

    print("\nRanked by likelihood to bounce (score = 0.4×1m + 0.6×2m):")
    for _, r in df_out.iterrows():
        print(
            f"  {r['ticker']}: {r['score']:.1f} "
            f"(entries={r['entries']}, 2m={r['success_rate_2m']:.0f}%)"
        )
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
