"""Unit tests for FollowTheFootPrints analyser.

All tests use synthetic DataFrames – no yfinance network calls are made.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from followthefootprints.analyzer import FollowTheFootPrints
from followthefootprints.exceptions import UnknownIntervalException


# ---------------------------------------------------------------------------
# Mode / interval resolution
# ---------------------------------------------------------------------------

class TestGetMode:
    def test_weekly(self, analyzer):
        assert analyzer._get_mode("1wk") == "weekly"

    def test_daily(self, analyzer):
        assert analyzer._get_mode("1d") == "daily"

    def test_hourly(self, analyzer):
        assert analyzer._get_mode("1h") == "hourly"

    def test_15m(self, analyzer):
        assert analyzer._get_mode("15m") == "15m"

    def test_unknown_raises(self, analyzer):
        with pytest.raises(UnknownIntervalException):
            analyzer._get_mode("1yr")

    def test_default_interval_is_weekly(self):
        obj = FollowTheFootPrints(time_delta_days=30)
        assert obj.mode == "weekly"
        assert obj.interval == "1wk"


# ---------------------------------------------------------------------------
# OHLC preparation (empty / malformed yfinance responses)
# ---------------------------------------------------------------------------

class TestPrepareOhlc:
    """Tests for _prepare_ohlc handling of empty or malformed yfinance data."""

    def test_empty_yfinance_response_returns_empty_dataframe(self, analyzer):
        """When yfinance returns empty data (e.g. failed download, delisted), return empty df."""
        empty_raw = pd.DataFrame(
            columns=["Open", "High", "Low", "Close", "Volume", "Date"]
        )
        with patch("followthefootprints.analyzer.yf") as mock_yf:
            mock_yf.download.return_value = empty_raw
            result = analyzer._prepare_ohlc("FAKE.NS")
        assert result.empty
        assert list(result.columns) == [
            "Datetime", "open", "high", "low", "close", "vol",
            "candle_colour", "%_of_change",
        ]

    def test_all_nan_rows_returns_empty_dataframe(self, analyzer):
        """When all rows are dropped as NaN, return empty df without raising."""
        raw = pd.DataFrame({
            "Open": [np.nan], "High": [np.nan], "Low": [np.nan],
            "Close": [np.nan], "Volume": [np.nan], "Date": [pd.NaT],
        })
        raw.index = pd.DatetimeIndex([pd.Timestamp("2024-01-01")])
        with patch("followthefootprints.analyzer.yf") as mock_yf:
            mock_yf.download.return_value = raw
            result = analyzer._prepare_ohlc("FAKE.NS")
        assert result.empty
        assert "candle_colour" in result.columns

    def test_missing_columns_returns_empty_dataframe(self, analyzer):
        """When yfinance returns unexpected structure (no OHLC), return empty df."""
        malformed = pd.DataFrame({"foo": [], "bar": []})
        with patch("followthefootprints.analyzer.yf") as mock_yf:
            mock_yf.download.return_value = malformed
            result = analyzer._prepare_ohlc("FAKE.NS")
        assert result.empty
        assert "candle_colour" in result.columns

    def test_valid_data_returns_processed_dataframe(self, analyzer):
        """When yfinance returns valid OHLC, _prepare_ohlc processes it correctly."""
        n = 5
        raw = pd.DataFrame({
            "Open": [100.0 + i for i in range(n)],
            "High": [105.0 + i for i in range(n)],
            "Low": [98.0 + i for i in range(n)],
            "Close": [102.0 + i for i in range(n)],
            "Volume": [10_000] * n,
        }, index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=n, freq="D")))
        raw.index.name = "Date"
        with patch("followthefootprints.analyzer.yf") as mock_yf:
            mock_yf.download.return_value = raw
            result = analyzer._prepare_ohlc("TEST.NS")
        assert not result.empty
        assert len(result) == n
        assert "candle_colour" in result.columns
        assert "%_of_change" in result.columns
        assert set(result["candle_colour"].unique()).issubset({"Green", "Red"})

    def test_process_completes_when_all_tickers_return_empty(self, analyzer):
        """process() completes without crashing when yfinance returns empty for all tickers."""
        empty_raw = pd.DataFrame(
            columns=["Open", "High", "Low", "Close", "Volume", "Date"]
        )
        with (
            patch("followthefootprints.analyzer.get_tickers") as mock_get_tickers,
            patch("followthefootprints.analyzer.yf") as mock_yf,
        ):
            mock_get_tickers.return_value = ["FAKE1.NS", "FAKE2.NS"]
            mock_yf.download.return_value = empty_raw
            analyzer.index = "nifty50"
            analyzer.process()
        assert analyzer.good_stocks == []
        # No exception, no CSV written (logged as warning)

    def test_delisted_ticker_triggers_index_refresh(self, analyzer):
        """When a ticker returns empty data (possibly delisted), refresh_index_cache is called."""
        tickers_with_delisted = ["RELIANCE.NS", "HDFC.NS", "TCS.NS"]
        valid_raw = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [105.0, 106.0],
                "Low": [98.0, 99.0],
                "Close": [102.0, 103.0],
                "Volume": [10_000, 10_000],
            },
            index=pd.DatetimeIndex(pd.date_range("2024-01-01", periods=2, freq="D")),
        )
        valid_raw.index.name = "Date"
        empty_raw = pd.DataFrame(
            columns=["Open", "High", "Low", "Close", "Volume", "Date"]
        )

        with (
            patch("followthefootprints.analyzer.get_tickers") as mock_get_tickers,
            patch("followthefootprints.analyzer.refresh_index_cache") as mock_refresh,
            patch("followthefootprints.analyzer.yf") as mock_yf,
        ):
            mock_get_tickers.return_value = tickers_with_delisted

            def download_side_effect(symbol, **kwargs):
                if symbol == "HDFC.NS":
                    return empty_raw
                return valid_raw.copy()

            mock_yf.download.side_effect = download_side_effect

            analyzer.index = "nifty100"
            analyzer.process()

        mock_refresh.assert_called_once_with("nifty100")

    def test_delisted_exception_triggers_index_refresh(self, analyzer):
        """When yfinance raises an exception with 'delisted' or 'timezone', refresh is called."""
        with (
            patch("followthefootprints.analyzer.get_tickers") as mock_get_tickers,
            patch("followthefootprints.analyzer.refresh_index_cache") as mock_refresh,
            patch("followthefootprints.analyzer.yf") as mock_yf,
        ):
            mock_get_tickers.return_value = ["HDFC.NS"]
            mock_yf.download.side_effect = Exception(
                "HDFC.NS: possibly delisted; no timezone found"
            )

            analyzer.index = "nifty100"
            analyzer.process()

        mock_refresh.assert_called_once_with("nifty100")


# ---------------------------------------------------------------------------
# Static helpers
# ---------------------------------------------------------------------------

class TestGetChange:
    def test_positive_change(self):
        assert FollowTheFootPrints.get_change(110.0, 100.0) == pytest.approx(10.0)

    def test_negative_change(self):
        assert FollowTheFootPrints.get_change(90.0, 100.0) == pytest.approx(-10.0)

    def test_no_change(self):
        assert FollowTheFootPrints.get_change(100.0, 100.0) == 0.0

    def test_zero_division(self):
        result = FollowTheFootPrints.get_change(10.0, 0.0)
        assert result == float("inf")


class TestIsBaseCandle:
    def test_narrow_body_is_base(self):
        # Body = 2, Range = 6 → 33 % ≤ 50 %
        assert FollowTheFootPrints.is_it_base_candle(
            open=100.0, close=102.0, low=99.0, high=105.0
        ) is True

    def test_wide_body_is_not_base(self):
        # Body = 4, Range = 6 → 67 % > 50 %
        assert FollowTheFootPrints.is_it_base_candle(
            open=100.0, close=104.0, low=99.0, high=105.0
        ) is False

    def test_doji_is_base(self):
        # Body = 0 → 0 % ≤ 50 %
        assert FollowTheFootPrints.is_it_base_candle(
            open=100.0, close=100.0, low=98.0, high=102.0
        ) is True

    def test_zero_range_is_base(self):
        assert FollowTheFootPrints.is_it_base_candle(
            open=100.0, close=100.0, low=100.0, high=100.0
        ) is True


# ---------------------------------------------------------------------------
# Average percentage change calculation
# ---------------------------------------------------------------------------

class TestCalculateAvgPercChanges:
    def test_green_avg_is_positive(self, analyzer, flat_ohlc):
        analyzer.calculate_avg_perc_changes(flat_ohlc)
        assert flat_ohlc["avg_%_green"].iloc[-1] > 0

    def test_red_avg_is_negative_or_nan(self, analyzer, flat_ohlc):
        # flat_ohlc is fully bullish – no red bars, so avg_%_red is NaN.
        analyzer.calculate_avg_perc_changes(flat_ohlc)
        assert flat_ohlc["avg_%_red"].isna().all()

    def test_overall_avg_computed(self, analyzer, flat_ohlc):
        analyzer.calculate_avg_perc_changes(flat_ohlc)
        assert not flat_ohlc["avg_%"].isna().all()

    def test_mixed_candles(self, analyzer):
        df = pd.DataFrame(
            {
                "Datetime": pd.date_range("2023-01-01", periods=6, freq="W"),
                "open":  [100, 105, 103, 108, 106, 110],
                "close": [105, 103, 108, 106, 110, 108],
            }
        )
        df.loc[df["open"] <= df["close"], "candle_colour"] = "Green"
        df.loc[df["open"] > df["close"], "candle_colour"] = "Red"
        df["%_of_change"] = (
            (df["close"] - df["close"].shift(1)) / df["close"].shift(1)
        ) * 100
        analyzer.calculate_avg_perc_changes(df)
        # avg_%_green must be positive, avg_%_red must be negative
        assert df["avg_%_green"].iloc[-1] > 0
        assert df["avg_%_red"].iloc[-1] < 0


# ---------------------------------------------------------------------------
# Leg-candle detection
# ---------------------------------------------------------------------------

class TestMarkLegCandle:
    def _make_df(self, pct_values: list[float]) -> pd.DataFrame:
        n = len(pct_values)
        df = pd.DataFrame(
            {
                "Datetime": pd.date_range("2023-01-01", periods=n, freq="W"),
                "%_of_change": pct_values,
                "avg_%_green": [2.0] * n,
                "avg_%_red": [-2.0] * n,
            }
        )
        return df

    def test_green_leg_out_marked(self, analyzer):
        # 2.0 * 1.7 = 3.4 → bar at 3.5 qualifies
        df = self._make_df([1.0, 1.0, 1.0, 1.0, 3.5, 1.0])
        analyzer.mark_leg_candle(df)
        assert df.loc[4, "leg"] == "green_leg_out"

    def test_red_leg_in_marked(self, analyzer):
        # -2.0 * 2.0 = -4.0 → bar at -4.5 qualifies
        df = self._make_df([-1.0, -1.0, -1.0, -1.0, -4.5, -1.0])
        analyzer.mark_leg_candle(df)
        assert df.loc[4, "leg"] == "red_leg_in"

    def test_normal_bar_not_marked(self, analyzer):
        df = self._make_df([1.0, 1.0, 1.0, 1.0, 1.5, 1.0])
        analyzer.mark_leg_candle(df)
        assert "leg" not in df.columns or pd.isna(df.loc[4, "leg"])


# ---------------------------------------------------------------------------
# Resistance / support marking
# ---------------------------------------------------------------------------

class TestMarkResistancePoints:
    def test_peak_marked_as_resistance(self, analyzer, pivot_high_ohlc):
        analyzer.mark_resistance_points(pivot_high_ohlc)
        assert pivot_high_ohlc.loc[4, "resistance"] == "Y"

    def test_non_peak_not_marked(self, analyzer, pivot_high_ohlc):
        analyzer.mark_resistance_points(pivot_high_ohlc)
        # Candles on the slope should NOT be resistance
        assert pivot_high_ohlc.loc[0, "resistance"] != "Y"
        assert pivot_high_ohlc.loc[8, "resistance"] != "Y"


class TestMarkSupportPoints:
    def test_trough_marked_as_support(self, analyzer, pivot_low_ohlc):
        analyzer.mark_support_points(pivot_low_ohlc)
        assert pivot_low_ohlc.loc[4, "support"] == "Y"

    def test_non_trough_not_marked(self, analyzer, pivot_low_ohlc):
        analyzer.mark_support_points(pivot_low_ohlc)
        assert pivot_low_ohlc.loc[0, "support"] != "Y"
        assert pivot_low_ohlc.loc[8, "support"] != "Y"


# ---------------------------------------------------------------------------
# Demand zone identification
# ---------------------------------------------------------------------------

class TestIdentifyPossibleDz:
    def _build_dz_scenario(self) -> pd.DataFrame:
        """Construct a minimal DataFrame that should trigger a DZ mark."""
        n = 10
        df = pd.DataFrame(
            {
                "Datetime": pd.date_range("2023-01-01", periods=n, freq="W"),
                "open":  [100.0] * n,
                "close": [102.0] * n,
                "high":  [105.0] * n,
                "low":   [98.0] * n,
                "vol":   [1000] * n,
                "leg":   [None] * n,
                "support": [None] * n,
                "resistance": [None] * n,
                "dz":    [None] * n,
            }
        )
        # Place a support 3 bars before the leg-out.
        df.at[5, "support"] = "Y"
        # The leg-out fires at bar 8.
        df.at[8, "leg"] = "green_leg_out"
        return df

    def test_dz_marked_when_conditions_met(self, analyzer):
        df = self._build_dz_scenario()
        analyzer.identify_possible_dz(df)
        assert df.loc[8, "dz"] == "Y"

    def test_no_dz_without_support(self, analyzer):
        df = self._build_dz_scenario()
        df["support"] = None  # remove support
        analyzer.identify_possible_dz(df)
        assert df.loc[8, "dz"] != "Y"

    def test_consecutive_dz_collapsed(self, analyzer):
        df = self._build_dz_scenario()
        # Add a second leg-out right after the first.
        df.at[9, "leg"] = "green_leg_out"
        analyzer.identify_possible_dz(df)
        # The later consecutive DZ should be NaN (de-duplicated).
        assert pd.isna(df.loc[9, "dz"]) or df.loc[9, "dz"] != "Y"


# ---------------------------------------------------------------------------
# Fresh zone detection
# ---------------------------------------------------------------------------

class TestIsFreshZone:
    def _make_subsequent_df(
        self, lows: list[float], dz_time: pd.Timestamp
    ) -> pd.DataFrame:
        n = len(lows)
        return pd.DataFrame(
            {
                "Datetime": pd.date_range(
                    dz_time + pd.Timedelta(weeks=1), periods=n, freq="W"
                ),
                "low": lows,
            }
        )

    def test_fresh_when_price_stays_above(self, analyzer):
        dz_time = pd.Timestamp("2023-06-01")
        support_record = (dz_time, "Y", 95.0)
        subsequent = self._make_subsequent_df([98.0, 99.0, 100.0], dz_time)
        full_df = pd.concat(
            [
                pd.DataFrame({"Datetime": [dz_time], "low": [96.0]}),
                subsequent,
            ],
            ignore_index=True,
        )
        assert analyzer.is_it_fresh_zone(support_record, full_df) is True

    def test_not_fresh_when_price_dips_below(self, analyzer):
        dz_time = pd.Timestamp("2023-06-01")
        support_record = (dz_time, "Y", 95.0)
        subsequent = self._make_subsequent_df([98.0, 93.0, 100.0], dz_time)
        full_df = pd.concat(
            [
                pd.DataFrame({"Datetime": [dz_time], "low": [96.0]}),
                subsequent,
            ],
            ignore_index=True,
        )
        assert analyzer.is_it_fresh_zone(support_record, full_df) is False

    def test_no_subsequent_data_returns_false(self, analyzer):
        dz_time = pd.Timestamp("2023-12-31")
        support_record = (dz_time, "Y", 95.0)
        df = pd.DataFrame({"Datetime": [dz_time], "low": [96.0]})
        assert analyzer.is_it_fresh_zone(support_record, df) is False


# ---------------------------------------------------------------------------
# Percentage-of-change annotation
# ---------------------------------------------------------------------------

class TestAddPercentageOfChange:
    def test_positive_gain_computed(self, analyzer):
        stocks = [{"green_leg_out_low_price": 100.0, "current_closing_price": 110.0}]
        analyzer.add_percentage_of_change(stocks)
        assert stocks[0]["percentage_of_change"] == pytest.approx(10.0)

    def test_nan_when_entry_missing(self, analyzer):
        stocks = [{"green_leg_out_low_price": float("nan"), "current_closing_price": 110.0}]
        analyzer.add_percentage_of_change(stocks)
        assert np.isnan(stocks[0]["percentage_of_change"])

    def test_nan_when_both_missing(self, analyzer):
        stocks = [{"green_leg_out_low_price": float("nan"), "current_closing_price": float("nan")}]
        analyzer.add_percentage_of_change(stocks)
        assert np.isnan(stocks[0]["percentage_of_change"])


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

class TestCLI:
    def test_default_mode_is_weekly(self, capsys):
        from followthefootprints.__main__ import _build_parser
        args = _build_parser().parse_args([])
        assert args.mode == "weekly"
        assert args.index == "nifty100"
        assert args.days == 365

    def test_daily_mode_parsed(self):
        from followthefootprints.__main__ import _build_parser
        args = _build_parser().parse_args(["--mode", "daily"])
        assert args.mode == "daily"

    def test_custom_index_parsed(self):
        from followthefootprints.__main__ import _build_parser
        args = _build_parser().parse_args(["--index", "nasdaq100"])
        assert args.index == "nasdaq100"

    def test_invalid_mode_exits(self):
        from followthefootprints.__main__ import _build_parser
        with pytest.raises(SystemExit):
            _build_parser().parse_args(["--mode", "hourly"])
