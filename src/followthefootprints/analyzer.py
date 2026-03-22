"""Core demand-zone analysis engine."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests
import pandas as pd
import yfinance as yf
from pandas import DataFrame, json_normalize

from .exceptions import UnknownIntervalException
from .indices import INDEX_LISTS, get_tickers, refresh_index_cache

logger = logging.getLogger(__name__)

# Maps yfinance interval strings to human-readable mode names.
INTERVAL_MODE_MAP: Dict[str, str] = {
    "1wk": "weekly",
    "1d": "daily",
    "1h": "hourly",
    "15m": "15m",
}

# Intervals where yfinance returns a ``Date`` index instead of ``Datetime``.
_DATE_INDEX_INTERVALS = {"1wk", "1d"}

# Leg-out detection thresholds (multiples of the average move).
_GREEN_LEG_THRESHOLD = 1.7
_RED_LEG_THRESHOLD = 2.0

# Backtest bounce detection thresholds.
_BOUNCE_MIN_PCT = 5.0
_WEEKS_1_MONTH = 4
_WEEKS_2_MONTHS = 8


class FollowTheFootPrints:
    """Scans a stock index for demand zones with follow-through confirmation.

    Parameters
    ----------
    time_delta_days:
        How many calendar days of history to fetch from today.
    index:
        One of ``"nifty100"``, ``"nifty200"``, ``"nifty50"``, ``"nasdaq100"``.
    interval:
        yfinance interval string – ``"1wk"`` (weekly) or ``"1d"`` (daily).
        ``"1h"`` and ``"15m"`` are also accepted programmatically.
    """

    def __init__(
        self,
        time_delta_days: int,
        index: str = "nifty100",
        interval: str = "1wk",
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
    ) -> None:
        if index not in INDEX_LISTS:
            raise ValueError(
                f"Unknown index '{index}'. Valid options: {sorted(INDEX_LISTS)}"
            )
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.start_date = (
            datetime.now() - timedelta(days=time_delta_days)
        ).strftime("%Y-%m-%d")
        self.index = index
        self.interval = interval
        self.mode = self._get_mode(interval)
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.good_stocks: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_mode(self, interval: str) -> str:
        if interval not in INTERVAL_MODE_MAP:
            raise UnknownIntervalException(
                f"Interval '{interval}' is not supported. "
                f"Valid options: {sorted(INTERVAL_MODE_MAP)}"
            )
        return INTERVAL_MODE_MAP[interval]

    def _prepare_ohlc(self, stock: str) -> DataFrame:
        """Download OHLC data from yfinance and return a normalised DataFrame.

        The returned DataFrame always has columns:
        ``Datetime, open, high, low, close, vol, candle_colour, %_of_change``
        """
        raw: DataFrame = yf.download(
            stock,
            start=self.start_date,
            end=self.current_date,
            interval=self.interval,
            rounding=True,
            progress=False,
        )

        df = raw.reset_index()

        # Newer yfinance versions may return a MultiIndex; flatten to single level.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[~df.isna().any(axis=1)].copy()

        # Normalise column names.  ``Date`` (daily/weekly) → ``Datetime``.
        df.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "vol",
                "Date": "Datetime",
            },
            inplace=True,
        )

        # Return empty DataFrame if no valid rows (e.g. yfinance failure, delisted).
        # Avoids "cannot set a frame with no defined index and a scalar" on empty df.
        required = {"open", "close"}
        if df.empty or not required.issubset(df.columns):
            return pd.DataFrame(
                columns=[
                    "Datetime", "open", "high", "low", "close", "vol",
                    "candle_colour", "%_of_change",
                ]
            )

        df["open"] = pd.to_numeric(df["open"])
        df["close"] = pd.to_numeric(df["close"])

        df.loc[df["open"] <= df["close"], "candle_colour"] = "Green"
        df.loc[df["open"] > df["close"], "candle_colour"] = "Red"

        df["%_of_change"] = (
            (df["close"] - df["close"].shift(1)) / df["close"].shift(1)
        ) * 100

        return df

    # ------------------------------------------------------------------
    # Signal computation steps
    # ------------------------------------------------------------------

    def calculate_avg_perc_changes(self, data_ohlc: DataFrame) -> None:
        """Add avg percentage-change columns for green, red, and all candles."""
        data_ohlc["avg_%_green"] = data_ohlc.loc[
            data_ohlc["%_of_change"] >= 0.0, "%_of_change"
        ].mean()
        data_ohlc["avg_%_red"] = data_ohlc.loc[
            data_ohlc["%_of_change"] < 0, "%_of_change"
        ].mean()
        data_ohlc["avg_%"] = data_ohlc["%_of_change"].mean()

    def mark_leg_candle(self, data_ohlc: DataFrame) -> None:
        """Mark outsized moves as green leg-out or red leg-in."""
        data_ohlc.loc[
            (data_ohlc["%_of_change"] / data_ohlc["avg_%_green"])
            >= _GREEN_LEG_THRESHOLD,
            "leg",
        ] = "green_leg_out"
        data_ohlc.loc[
            (data_ohlc["%_of_change"] / data_ohlc["avg_%_red"])
            >= _RED_LEG_THRESHOLD,
            "leg",
        ] = "red_leg_in"

    def mark_resistance_points(self, data_ohlc: DataFrame) -> None:
        """Label pivot highs as resistance using two structural patterns."""
        mv = data_ohlc["max_value"]

        # Pattern A: strictly ascending staircase of 4 candles on each side.
        cond_staircase = (
            (mv >= mv.shift(1))
            & (mv.shift(1) > mv.shift(2))
            & (mv.shift(2) > mv.shift(3))
            & (mv.shift(3) > mv.shift(4))
            & (mv >= mv.shift(-1))
            & (mv.shift(-1) > mv.shift(-2))
            & (mv.shift(-2) > mv.shift(-3))
            & (mv.shift(-3) > mv.shift(-4))
        )

        # Pattern B: dominant high – >= all 4 neighbours, strictly > the 5th.
        cond_dominant = (
            (mv >= mv.shift(1))
            & (mv >= mv.shift(2))
            & (mv >= mv.shift(3))
            & (mv >= mv.shift(4))
            & (mv > mv.shift(5))
            & (mv >= mv.shift(-1))
            & (mv >= mv.shift(-2))
            & (mv >= mv.shift(-3))
            & (mv >= mv.shift(-4))
            & (mv > mv.shift(-5))
        )

        data_ohlc.loc[cond_staircase | cond_dominant, "resistance"] = "Y"

    def mark_support_points(self, data_ohlc: DataFrame) -> None:
        """Label pivot lows as support using two structural patterns."""
        mn = data_ohlc["min_value"]

        # Pattern A: strictly descending staircase of 4 candles on each side.
        cond_staircase = (
            (mn <= mn.shift(1))
            & (mn.shift(1) < mn.shift(2))
            & (mn.shift(2) < mn.shift(3))
            & (mn.shift(3) < mn.shift(4))
            & (mn <= mn.shift(-1))
            & (mn.shift(-1) < mn.shift(-2))
            & (mn.shift(-2) < mn.shift(-3))
            & (mn.shift(-3) < mn.shift(-4))
        )

        # Pattern B: dominant low – <= all 4 neighbours on each side.
        cond_dominant = (
            (mn <= mn.shift(1))
            & (mn <= mn.shift(2))
            & (mn <= mn.shift(3))
            & (mn <= mn.shift(4))
            & (mn <= mn.shift(-1))
            & (mn <= mn.shift(-2))
            & (mn <= mn.shift(-3))
            & (mn <= mn.shift(-4))
        )

        data_ohlc.loc[cond_staircase | cond_dominant, "support"] = "Y"

    def identify_possible_dz(self, data_ohlc: DataFrame) -> None:
        """Mark a candle as a demand zone when a green leg-out fires from a
        support base with no resistance or red leg-in in the preceding 6 bars.
        Consecutive DZ marks are collapsed to a single event.
        """
        support_within_6 = (
            (data_ohlc["support"].shift(1) == "Y")
            | (data_ohlc["support"].shift(2) == "Y")
            | (data_ohlc["support"].shift(3) == "Y")
            | (data_ohlc["support"].shift(4) == "Y")
            | (data_ohlc["support"].shift(5) == "Y")
            | (data_ohlc["support"].shift(6) == "Y")
        )
        no_resistance_within_6 = (
            (data_ohlc["resistance"].shift(1) != "Y")
            & (data_ohlc["resistance"].shift(2) != "Y")
            & (data_ohlc["resistance"].shift(3) != "Y")
            & (data_ohlc["resistance"].shift(4) != "Y")
            & (data_ohlc["resistance"].shift(5) != "Y")
            & (data_ohlc["resistance"].shift(6) != "Y")
        )
        no_red_leg_within_6 = (
            (data_ohlc["leg"].shift(1) != "red_leg_in")
            & (data_ohlc["leg"].shift(2) != "red_leg_in")
            & (data_ohlc["leg"].shift(3) != "red_leg_in")
            & (data_ohlc["leg"].shift(4) != "red_leg_in")
            & (data_ohlc["leg"].shift(5) != "red_leg_in")
            & (data_ohlc["leg"].shift(6) != "red_leg_in")
        )

        data_ohlc.loc[
            (data_ohlc["leg"] == "green_leg_out")
            & support_within_6
            & no_resistance_within_6
            & no_red_leg_within_6,
            "dz",
        ] = "Y"

        # Remove duplicate consecutive DZ marks – keep only the last.
        # Keeping the last leg-out ensures the prior candles (base) are the
        # consolidation weeks immediately before the final breakout, not
        # earlier leg-outs that are still inside the base.
        data_ohlc.loc[
            (data_ohlc["dz"] == "Y")
            & (
                (data_ohlc["dz"].shift(-1) == "Y")
                | (data_ohlc["dz"].shift(-2) == "Y")
            ),
            "dz",
        ] = float("NaN")

    def get_good_dz(
        self,
        achievement: List[Dict[str, Any]],
        potential_stocks: List[Dict[str, Any]],
        fresh_zone_helper_list: List[Tuple[Any, str, float]],
        stock: str,
    ) -> None:
        """Identify demand zones sitting between two ascending resistance levels.

        A DZ is "good" when the resistance level immediately before the zone
        is lower than the resistance level immediately after it, confirming the
        stock has moved into higher price territory after leaving the zone.
        """
        # Build an ordered list of (datetime, resistance_price | 'Y') events.
        dz_points: List[Tuple[Any, Any]] = []
        for item in achievement:
            if item.get("resistance") == "Y":
                dz_points.append((item["Datetime"], item["max_value"]))
            if item.get("dz") == "Y":
                dz_points.append((item["Datetime"], item["dz"]))
                fresh_zone_helper_list.append(
                    (item["Datetime"], item["dz"], item["low"])
                )

        for i, item in enumerate(dz_points):
            if item[1] != "Y":
                continue

            # Walk backward to the nearest resistance price.
            prev_idx = i - 1
            try:
                while prev_idx >= 0 and not isinstance(dz_points[prev_idx][1], float):
                    prev_idx -= 1
                previous_r = dz_points[prev_idx] if prev_idx >= 0 else ("", 0.0)
            except IndexError:
                previous_r = ("", 0.0)

            # Walk forward to the nearest resistance price.
            next_idx = i + 1
            try:
                while next_idx < len(dz_points) and not isinstance(
                    dz_points[next_idx][1], float
                ):
                    next_idx += 1
                next_r = (
                    dz_points[next_idx]
                    if next_idx < len(dz_points)
                    else ("", float("inf"))
                )
            except IndexError:
                next_r = ("", float("inf"))

            if previous_r[1] < next_r[1]:
                potential_stocks.append({"stock": stock, "date": item[0]})
            else:
                logger.debug("Skipping DZ for %s on %s – not between ascending resistance", stock, item[0])

    def is_it_fresh_zone(
        self,
        support_for_dz: Tuple[Any, str, float],
        data_ohlc: DataFrame,
    ) -> bool:
        """Return True if price has not revisited the support low since the DZ formed.

        Algorithm:
        1. Filter all candles *after* the DZ datetime.
        2. If the subsequent minimum low is above the support's low → fresh zone.
        """
        datetime_filter = support_for_dz[0]
        subsequent = data_ohlc[data_ohlc["Datetime"] > datetime_filter]
        if subsequent.empty:
            return False
        min_low = subsequent["low"].min()
        return float(min_low) > float(support_for_dz[2])

    def get_fresh_zone(
        self,
        potential_stocks: List[Dict[str, Any]],
        fresh_zone_helper_list: List[Tuple[Any, str, float]],
        data_ohlc: DataFrame,
    ) -> None:
        """Annotate each potential stock entry with a ``fresh`` flag."""
        for item in potential_stocks:
            stock_time = item["date"]
            for record in fresh_zone_helper_list:
                if record[0] != stock_time:
                    continue
                item["fresh"] = "Y" if self.is_it_fresh_zone(record, data_ohlc) else "N"
                break

    def get_stocks_with_follow_through(
        self,
        potential_stocks: List[Dict[str, Any]],
        data_ohlc: DataFrame,
    ) -> None:
        """Check whether the 3-4 candles after the DZ show bullish follow-through.

        Accepted patterns (G=Green, R=Red):
        - G G G
        - G R G G
        - G G R G
        """
        for item in potential_stocks:
            stock_time = item["date"]
            filtered_df = data_ohlc[data_ohlc["Datetime"] >= stock_time]

            def _colour(shift: int, pos: int) -> str | None:
                shifted = filtered_df["candle_colour"].shift(shift).values
                return shifted[pos] if len(shifted) > pos else None

            c1 = _colour(1, 2)
            c2 = _colour(2, 4)
            c3 = _colour(3, 6)
            c4 = _colour(4, 8)

            bullish_patterns = (
                (c1 == "Green" and c2 == "Green" and c3 == "Green")
                or (c1 == "Green" and c2 == "Red" and c3 == "Green" and c4 == "Green")
                or (c1 == "Green" and c2 == "Green" and c3 == "Red" and c4 == "Green")
            )

            if bullish_patterns:
                item["follow_through"] = "Y"
                item["green_leg_out_low_price"] = float(filtered_df["open"].iloc[0])
                item["current_closing_price"] = float(filtered_df["close"].iloc[-1])
                # Demand zone: examine up to 3 candles before the leg-out.
                # _find_base_candle() picks the representative candle (smallest range
                # that passes is_it_base_candle). Its body top becomes the zone ceiling.
                # Zone floor = min low of ALL 3 prior candles so the full consolidation
                # area (including lower wicks from any of the 3 weeks) is captured.
                prior = data_ohlc[data_ohlc["Datetime"] < stock_time].tail(3)
                base_row = self._find_base_candle(prior)
                if base_row is not None:
                    bh = float(base_row["high"])
                    bo = float(base_row["open"])
                    bc = float(base_row["close"])
                    full_range = abs(bh - float(base_row["low"]))
                    body_pct = round(abs(bc - bo) / full_range * 100, 1) if full_range > 0 else 0.0
                    base_dt = pd.Timestamp(base_row["Datetime"])
                    if self.interval == "1wk":
                        # Normalize to Monday so it matches TradingView's weekly label
                        # (TradingView always uses calendar Monday; yfinance may use
                        # the first actual trading day on holiday weeks).
                        monday = base_dt - pd.Timedelta(days=base_dt.weekday())
                        item["base_candle_date"] = monday.date()
                    else:
                        item["base_candle_date"] = base_dt
                    # Zone top = body max of representative candle (excluding upper wick).
                    # Zone bottom = min low across all prior candidates (full consolidation).
                    item["base_candle_low"] = float(prior["low"].min())
                    item["base_candle_high"] = max(bo, bc)
                    item["base_candle_body_pct"] = body_pct
                else:
                    item["base_candle_date"] = float("nan")
                    item["base_candle_low"] = float("nan")
                    item["base_candle_high"] = float("nan")
                    item["base_candle_body_pct"] = float("nan")
            else:
                item["follow_through"] = "N"
                item["green_leg_out_low_price"] = float("nan")
                item["current_closing_price"] = float("nan")

    @staticmethod
    def is_it_base_candle(open: float, close: float, low: float, high: float) -> bool:
        """Return True when the candle qualifies as a consolidation base.

        Rules:
        - Body must be ≤ 50 % of the full range.
        - Lower wick must not exceed 60 % of range (rejects hammers).
        - Upper wick must not exceed 60 % of range (rejects shooting stars).
        """
        full_range = abs(high - low)
        if full_range == 0:
            return True
        if (abs(close - open) / full_range) * 100 > 50.0:
            return False
        lower_wick = min(open, close) - low
        if lower_wick / full_range > 0.6:
            return False
        upper_wick = high - max(open, close)
        if upper_wick / full_range > 0.6:
            return False
        return True

    @staticmethod
    def _find_base_candle(candidates: DataFrame) -> Optional[Any]:
        """Return the most compact base candle from a DataFrame of candidates.

        Among rows passing ``is_it_base_candle()`` (body ≤ 50 %, not a
        hammer/shooting-star), pick the one with the smallest total range
        (high − low).  A smaller range means tighter consolidation and a
        more reliable demand zone boundary.  Hammers and shooting stars are
        excluded because their extreme wicks distort the zone definition.
        Fallback: last row of the candidates DataFrame.
        """
        if candidates.empty:
            return None

        best_row = None
        best_range = float("inf")

        for _, row in candidates.iterrows():
            o = float(row["open"])
            c = float(row["close"])
            l = float(row["low"])
            h = float(row["high"])
            if not FollowTheFootPrints.is_it_base_candle(open=o, close=c, low=l, high=h):
                continue
            candle_range = abs(h - l)
            if candle_range < best_range:
                best_range = candle_range
                best_row = row

        return best_row if best_row is not None else candidates.iloc[-1]

    def get_stocks_with_base_before_follow_through(
        self,
        potential_stocks: List[Dict[str, Any]],
        data_ohlc: DataFrame,
    ) -> None:
        """Optionally tighten the signal by requiring a base candle directly
        before the leg-out candle.  The base's body top must sit within the
        lower third of the leg-out candle's body range.
        """
        for item in potential_stocks:
            if item.get("follow_through") == "N":
                item["follow_through_with_base"] = "N"
                continue

            stock_time = item["date"]
            filtered_df: DataFrame = data_ohlc[data_ohlc["Datetime"] <= stock_time]

            base_open = filtered_df["open"].shift(1).values.tolist()[-1]
            base_close = filtered_df["close"].shift(1).values.tolist()[-1]
            base_low = filtered_df["low"].shift(1).values.tolist()[-1]
            base_high = filtered_df["high"].shift(1).values.tolist()[-1]

            if not self.is_it_base_candle(
                open=base_open, close=base_close, low=base_low, high=base_high
            ):
                item["follow_through_with_base"] = "N"
                continue

            leg_open = filtered_df["open"].values.tolist()[-1]
            leg_close = filtered_df["close"].values.tolist()[-1]
            leg_min = min(leg_open, leg_close)
            leg_max = max(leg_open, leg_close)
            lower_third = leg_min + (leg_max - leg_min) / 3

            item["follow_through_with_base"] = (
                "Y" if max(base_open, base_close) <= lower_third else "N"
            )

    @staticmethod
    def get_change(current: float, previous: float) -> float:
        """Percentage change from *previous* to *current*."""
        if current == previous:
            return 0.0
        try:
            return ((current - previous) / previous) * 100.0
        except ZeroDivisionError:
            return float("inf")

    def add_percentage_of_change(
        self, potential_stocks: List[Dict[str, Any]]
    ) -> None:
        """Append the percentage gain from the leg-out open to the current close."""
        for item in potential_stocks:
            entry = item.get("green_leg_out_low_price")
            current = item.get("current_closing_price")
            if (
                entry is None
                or current is None
                or (isinstance(entry, float) and np.isnan(entry))
                or (isinstance(current, float) and np.isnan(current))
            ):
                item["percentage_of_change"] = float("nan")
            else:
                item["percentage_of_change"] = self.get_change(
                    current=current, previous=entry
                )

    # ------------------------------------------------------------------
    # Backtest helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_zone_entries(
        df: DataFrame, zone_low: float, zone_high: float
    ) -> List[Dict[str, Any]]:
        """Find all bars where the weekly low entered the demand zone."""
        entries: List[Dict[str, Any]] = []
        for i in range(len(df)):
            low = float(df.iloc[i]["low"])
            if low <= zone_high and low >= zone_low * 0.95:
                entries.append({"iloc_idx": i, "low": low})
        return entries

    @staticmethod
    def _did_bounce(
        df: DataFrame,
        entry_idx: int,
        entry_low: float,
        weeks_ahead: int,
        min_gain_pct: float = _BOUNCE_MIN_PCT,
    ) -> bool:
        """Return True if close exceeds entry_low + min_gain_pct within *weeks_ahead* bars."""
        future = df.iloc[entry_idx + 1 : entry_idx + weeks_ahead + 1]
        if future.empty:
            return False
        for _, row in future.iterrows():
            gain = ((float(row["close"]) - entry_low) / entry_low) * 100
            if gain >= min_gain_pct:
                return True
        return False

    @staticmethod
    def _distance_to_zone(
        current_price: float, zone_low: float, zone_high: float
    ) -> float:
        """Distance from current price to demand zone; 0 when inside."""
        if zone_low <= current_price <= zone_high:
            return 0.0
        return min(abs(current_price - zone_low), abs(current_price - zone_high))

    def _run_backtest_for_entry(
        self,
        data_ohlc: DataFrame,
        zone_low: float,
        zone_high: float,
        current_price: float,
    ) -> Dict[str, Any]:
        """Run bounce-back backtest for a single demand zone.

        Returns ``pct_from_zone`` and ``likelihood_to_bounce``
        (score = 0.4 x 1-month success rate + 0.6 x 2-month success rate).
        """
        df = data_ohlc.reset_index(drop=True)
        entries = self._find_zone_entries(df, zone_low, zone_high)

        distance = self._distance_to_zone(current_price, zone_low, zone_high)
        pct_from_zone = (distance / zone_low * 100) if zone_low else 0.0

        if not entries:
            return {
                "pct_from_zone": round(pct_from_zone, 1),
                "likelihood_to_bounce": 0.0,
            }

        bounced_1m = bounced_2m = 0
        for ent in entries:
            if self._did_bounce(df, ent["iloc_idx"], ent["low"], _WEEKS_1_MONTH):
                bounced_1m += 1
            if self._did_bounce(df, ent["iloc_idx"], ent["low"], _WEEKS_2_MONTHS):
                bounced_2m += 1

        n = len(entries)
        sr_1m = (bounced_1m / n * 100) if n else 0.0
        sr_2m = (bounced_2m / n * 100) if n else 0.0
        score = sr_1m * 0.4 + sr_2m * 0.6

        return {
            "pct_from_zone": round(pct_from_zone, 1),
            "likelihood_to_bounce": round(score, 1),
        }

    # ------------------------------------------------------------------
    # Main orchestration
    # ------------------------------------------------------------------

    def process(self) -> None:
        """Run the full analysis pipeline with backtest and write a proximity report CSV.

        Output file: ``{index}_{mode}.csv`` – stocks nearest to their demand
        zone, sorted by ``pct_away`` (IN ZONE first), with a
        ``likelihood_to_bounce_pct`` column derived from historical backtest.
        Only stocks with confirmed follow-through, a fresh zone, and a positive
        gain are included.  The same CSV is sent to Telegram when configured.
        """
        logger.info(
            "Analysis started | index=%s | interval=%s | %s → %s",
            self.index,
            self.interval,
            self.start_date,
            self.current_date,
        )

        tickers = get_tickers(self.index)
        skip: set = set()

        for stock in tickers:
            if stock in skip:
                continue
            try:
                data_ohlc = self._prepare_ohlc(stock)

                if data_ohlc.empty:
                    logger.warning(
                        "No data for %s – possibly delisted; refreshing index list",
                        stock,
                    )
                    refresh_index_cache(self.index)
                    skip.add(stock)
                    continue

                self.calculate_avg_perc_changes(data_ohlc)
                self.mark_leg_candle(data_ohlc)

                data_ohlc["max_value"] = (
                    data_ohlc[["open", "close"]].max(axis=1).apply(np.ceil)
                )
                data_ohlc["min_value"] = (
                    data_ohlc[["open", "close"]].min(axis=1).apply(np.floor)
                )

                self.mark_resistance_points(data_ohlc)
                self.mark_support_points(data_ohlc)
                self.identify_possible_dz(data_ohlc)

                fresh_zone_helper: List[Tuple[Any, str, float]] = []
                potential_stocks: List[Dict[str, Any]] = []
                achievement = data_ohlc.to_dict("records")

                self.get_good_dz(achievement, potential_stocks, fresh_zone_helper, stock)
                self.get_fresh_zone(potential_stocks, fresh_zone_helper, data_ohlc)
                self.get_stocks_with_follow_through(potential_stocks, data_ohlc)
                self.add_percentage_of_change(potential_stocks)

                for item in potential_stocks:
                    zone_low = item.get("base_candle_low")
                    zone_high = item.get("base_candle_high")
                    current = item.get("current_closing_price")
                    if (
                        item.get("follow_through") != "Y"
                        or item.get("fresh") != "Y"
                        or zone_low is None
                        or zone_high is None
                        or (isinstance(zone_low, float) and np.isnan(zone_low))
                        or (isinstance(zone_high, float) and np.isnan(zone_high))
                        or current is None
                        or (isinstance(current, float) and np.isnan(current))
                    ):
                        continue
                    backtest = self._run_backtest_for_entry(
                        data_ohlc, zone_low, zone_high, current
                    )
                    item.update(backtest)

                self.good_stocks.extend(potential_stocks)

            except Exception as e:
                logger.exception("Error processing %s", stock)
                err_msg = str(e).lower()
                if "delisted" in err_msg or "timezone" in err_msg:
                    logger.warning(
                        "Detected delisted/tz error for %s; refreshing index list",
                        stock,
                    )
                    refresh_index_cache(self.index)
                    skip.add(stock)

        df = json_normalize(self.good_stocks)

        if df.empty:
            logger.warning("No results found. CSV not written.")
            return

        filtered = df[
            (df["follow_through"] == "Y")
            & (df["fresh"] == "Y")
            & df["percentage_of_change"].notna()
            & (df["percentage_of_change"] > 0)
        ]

        if "pct_from_zone" not in filtered.columns or filtered["pct_from_zone"].notna().sum() == 0:
            logger.warning("No backtest data available. CSV not written.")
            return

        filtered = filtered[filtered["pct_from_zone"].notna()].copy()

        if filtered.empty:
            logger.warning("No results after filtering. CSV not written.")
            return

        proximity_df = pd.DataFrame({
            "stock": filtered["stock"].values,
            "current_price": filtered["current_closing_price"].round(2).values,
            "zone_low": filtered["base_candle_low"].round(2).values,
            "zone_high": filtered["base_candle_high"].round(2).values,
            "pct_away": filtered["pct_from_zone"].round(1).values,
            "status": filtered["pct_from_zone"].apply(
                lambda x: "IN ZONE" if x == 0 else f"{x:.1f}% away"
            ).values,
            "base_body_pct": filtered["base_candle_body_pct"].round(1).values,
            "likelihood_to_bounce_pct": filtered["likelihood_to_bounce"].round(1).values,
        })

        proximity_df = proximity_df.sort_values("pct_away", ascending=True)

        output_path = f"{self.index}_{self.mode}.csv"
        proximity_df.to_csv(output_path, encoding="utf-8", index=False)
        logger.info("Proximity report written to %s (%d rows)", output_path, len(proximity_df))
        self._send_telegram_alert(output_path, len(proximity_df))

    def _send_telegram_alert(self, csv_path: str, count: int) -> None:
        """Send the generated CSV to Telegram if credentials are configured."""
        if not self.telegram_token or not self.telegram_chat_id:
            logger.debug("Telegram credentials not provided. Skipping alert.")
            return
        try:
            logger.info("Sending results to Telegram...")
            msg_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            msg_data = {
                "chat_id": self.telegram_chat_id,
                "text": (
                    f"📊 *Stocks Nearest to Demand Zone*\n\n"
                    f"Index: {self.index}\nInterval: {self.interval}\n"
                    f"Stocks Found: {count}\n\n"
                    f"Sorted by proximity (IN ZONE first) with likelihood to bounce 👇"
                ),
                "parse_mode": "Markdown",
            }
            requests.post(msg_url, data=msg_data, timeout=10)
            doc_url = f"https://api.telegram.org/bot{self.telegram_token}/sendDocument"
            with open(csv_path, "rb") as f:
                requests.post(
                    doc_url,
                    data={"chat_id": self.telegram_chat_id},
                    files={"document": (os.path.basename(csv_path), f)},
                    timeout=30,
                )
            logger.info("Telegram alert sent successfully.")
        except Exception as e:
            logger.warning("Failed to send Telegram alert: %s", e)
