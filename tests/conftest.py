"""Shared pytest fixtures for FollowTheFootPrints tests.

All fixtures produce synthetic DataFrames – no network calls are made.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from followthefootprints.analyzer import FollowTheFootPrints


@pytest.fixture
def analyzer() -> FollowTheFootPrints:
    """A weekly analyser instance (no network access used in unit tests)."""
    return FollowTheFootPrints(time_delta_days=365, index="nifty100", interval="1wk")


@pytest.fixture
def flat_ohlc() -> pd.DataFrame:
    """20-bar OHLC DataFrame with a clear uptrend used in multiple tests.

    Candle colours and ``%_of_change`` are pre-computed so individual signal
    methods can be called without running the full pipeline.
    """
    n = 20
    base = 100.0
    closes = [base + i * 2 for i in range(n)]
    opens = [c - 1 for c in closes]
    highs = [c + 2 for c in closes]
    lows = [o - 2 for o in opens]

    df = pd.DataFrame(
        {
            "Datetime": pd.date_range("2023-01-01", periods=n, freq="W"),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "vol": [10_000] * n,
        }
    )
    df.loc[df["open"] <= df["close"], "candle_colour"] = "Green"
    df.loc[df["open"] > df["close"], "candle_colour"] = "Red"
    df["%_of_change"] = (
        (df["close"] - df["close"].shift(1)) / df["close"].shift(1)
    ) * 100
    return df


@pytest.fixture
def pivot_high_ohlc() -> pd.DataFrame:
    """9-bar DataFrame with a staircase peak at index 4.

    ``max_value`` peaks at index 4 – used by resistance tests.
    open > close (Red bars) so max_value == open.
    """
    # open ascends to index 4 then descends → max_value peaks at 4
    opens  = [90.0, 92.0, 94.0, 96.0, 98.0, 96.0, 94.0, 92.0, 90.0]
    closes = [o - 1 for o in opens]  # open > close → Red

    df = pd.DataFrame(
        {
            "Datetime": pd.date_range("2023-01-01", periods=9, freq="W"),
            "open":  opens,
            "close": closes,
            "high":  [o + 2 for o in opens],
            "low":   [c - 2 for c in closes],
            "vol":   [5_000] * 9,
        }
    )
    df["max_value"] = df[["open", "close"]].max(axis=1).apply(np.ceil)
    df["min_value"] = df[["open", "close"]].min(axis=1).apply(np.floor)
    df["%_of_change"] = (
        (df["close"] - df["close"].shift(1)) / df["close"].shift(1)
    ) * 100
    df.loc[df["open"] <= df["close"], "candle_colour"] = "Green"
    df.loc[df["open"] > df["close"], "candle_colour"] = "Red"
    return df


@pytest.fixture
def pivot_low_ohlc() -> pd.DataFrame:
    """9-bar DataFrame with a staircase trough at index 4.

    ``min_value`` troughs at index 4 – used by support tests.
    open < close (Green bars) so min_value == open.
    """
    # open descends to index 4 then ascends → min_value troughs at 4
    opens  = [98.0, 96.0, 94.0, 92.0, 90.0, 92.0, 94.0, 96.0, 98.0]
    closes = [o + 1 for o in opens]  # open < close → Green

    df = pd.DataFrame(
        {
            "Datetime": pd.date_range("2023-01-01", periods=9, freq="W"),
            "open":  opens,
            "close": closes,
            "high":  [c + 2 for c in closes],
            "low":   [o - 2 for o in opens],
            "vol":   [5_000] * 9,
        }
    )
    df["max_value"] = df[["open", "close"]].max(axis=1).apply(np.ceil)
    df["min_value"] = df[["open", "close"]].min(axis=1).apply(np.floor)
    df["%_of_change"] = (
        (df["close"] - df["close"].shift(1)) / df["close"].shift(1)
    ) * 100
    df.loc[df["open"] <= df["close"], "candle_colour"] = "Green"
    df.loc[df["open"] > df["close"], "candle_colour"] = "Red"
    return df
