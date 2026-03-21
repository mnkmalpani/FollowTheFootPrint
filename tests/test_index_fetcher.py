"""Unit tests for index fetcher.

All tests mock HTTP – no network calls are made.
"""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from followthefootprints.index_fetcher import (
    _CACHE,
    get_index_constituents,
    refresh_index,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the fetcher cache before each test."""
    _CACHE.clear()
    yield
    _CACHE.clear()


class TestGetIndexConstituents:
    """Tests for get_index_constituents."""

    def test_nifty50_fetch_returns_tickers_with_ns_suffix(self):
        """Nifty 50 fetch returns NSE tickers with .NS suffix."""
        html = """
        <table><tr><th>Symbol</th><th>Company</th></tr>
        <tr><td>RELIANCE</td><td>Reliance</td></tr>
        <tr><td>TCS</td><td>TCS</td></tr>
        </table>
        """
        with patch("followthefootprints.index_fetcher.requests.get") as mock_get:
            mock_get.return_value.text = html
            mock_get.return_value.raise_for_status = lambda: None
            with patch("followthefootprints.index_fetcher.pd.read_html") as mock_html:
                mock_html.return_value = [
                    pd.DataFrame({"Symbol": ["RELIANCE", "TCS"], "Company": ["R", "T"]})
                ]
                result = get_index_constituents("nifty50", use_cache=False)
        assert result == ["RELIANCE.NS", "TCS.NS"]

    def test_nasdaq100_fetch_returns_tickers_without_suffix(self):
        """NASDAQ 100 fetch returns US tickers without suffix."""
        with patch("followthefootprints.index_fetcher.requests.get") as mock_get:
            mock_get.return_value.text = "<html></html>"
            mock_get.return_value.raise_for_status = lambda: None
            with patch("followthefootprints.index_fetcher.pd.read_html") as mock_html:
                mock_html.return_value = [
                    pd.DataFrame({"Ticker": ["AAPL", "MSFT"], "Company": ["A", "M"]})
                ]
                result = get_index_constituents(
                    "nasdaq100", use_cache=False, fallback_list=["GOOGL"]
                )
        assert result == ["AAPL", "MSFT"]

    def test_uses_fallback_when_fetch_fails(self):
        """When fetch fails, uses fallback list."""
        with patch("followthefootprints.index_fetcher._fetch_index", return_value=None):
            result = get_index_constituents(
                "nifty200", use_cache=False, fallback_list=["RELIANCE.NS", "TCS.NS"]
            )
        assert result == ["RELIANCE.NS", "TCS.NS"]

    def test_raises_when_no_fallback_and_fetch_fails(self):
        """Raises when fetch fails and no fallback provided."""
        with patch("followthefootprints.index_fetcher._fetch_index", return_value=None):
            with pytest.raises(ValueError, match="Cannot get constituents"):
                get_index_constituents("nifty200", use_cache=False)

    def test_cache_used_when_use_cache_true(self):
        """When use_cache=True and cache is populated, returns cached value."""
        cached = ["CACHED.NS"]
        _CACHE["nifty50"] = cached
        with patch("followthefootprints.index_fetcher._fetch_index") as mock_fetch:
            result = get_index_constituents("nifty50", use_cache=True)
        mock_fetch.assert_not_called()
        assert result == cached


class TestRefreshIndex:
    """Tests for refresh_index."""

    def test_clears_cache_for_index(self):
        """refresh_index removes cached entry for the index."""
        _CACHE["nifty100"] = ["OLD.NS"]
        refresh_index("nifty100")
        assert "nifty100" not in _CACHE
