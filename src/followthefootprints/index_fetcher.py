"""Auto-fetch index constituents from Wikipedia.

Fetches current ticker lists to avoid stale/delisted symbols (e.g. HDFC.NS).
Falls back to built-in lists when fetch fails or for indices without Wikipedia pages.
"""

from __future__ import annotations

import io
import logging
from typing import Dict, List, Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# User-Agent required by Wikipedia for programmatic access.
_WIKI_HEADERS = {
    "User-Agent": "FollowTheFootprints/1.0 (https://github.com/; stock analysis)",
}

# Module-level cache: index_key -> List[str]. Cleared on refresh.
_CACHE: Dict[str, List[str]] = {}

# Fallback lists when fetch fails. NSE tickers use .NS suffix; NASDAQ has no suffix.
# These are kept as last resort – fetcher prefers live data.
_FALLBACK_LISTS: Dict[str, List[str]] = {}


def _fetch_nifty50() -> List[str]:
    """Fetch Nifty 50 constituents from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/NIFTY_50"
    r = requests.get(url, headers=_WIKI_HEADERS, timeout=30)
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))
    for t in tables:
        if "Symbol" in t.columns:
            syms = (
                t["Symbol"]
                .dropna()
                .astype(str)
                .str.strip()
                .str.upper()
            )
            syms = syms[syms.str.match(r"^[A-Z0-9&.-]+$", na=False)]
            return [f"{s}.NS" for s in syms]
    return []


def _fetch_nifty_next_50() -> List[str]:
    """Fetch Nifty Next 50 constituents from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/NIFTY_Next_50"
    r = requests.get(url, headers=_WIKI_HEADERS, timeout=30)
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))
    for t in tables:
        if "Symbol" in t.columns:
            syms = (
                t["Symbol"]
                .dropna()
                .astype(str)
                .str.strip()
                .str.upper()
            )
            syms = syms[syms.str.match(r"^[A-Z0-9&.-]+$", na=False)]
            return [f"{s}.NS" for s in syms]
    return []


def _fetch_nasdaq100() -> List[str]:
    """Fetch NASDAQ 100 constituents from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    r = requests.get(url, headers=_WIKI_HEADERS, timeout=30)
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))
    for t in tables:
        cols = [str(c).lower() for c in t.columns]
        if "ticker" in str(cols):
            tick_col = next(
                c for c in t.columns if "ticker" in str(c).lower()
            )
            ticks = (
                t[tick_col]
                .dropna()
                .astype(str)
                .str.strip()
                .str.upper()
            )
            ticks = ticks[ticks.str.match(r"^[A-Z0-9.-]+$", na=False)]
            return ticks.tolist()
    return []


def _fetch_index(index_key: str) -> Optional[List[str]]:
    """Fetch tickers for the given index. Returns None on failure."""
    try:
        if index_key == "nifty50":
            return _fetch_nifty50()
        if index_key == "nifty100":
            n50 = _fetch_nifty50()
            nnext = _fetch_nifty_next_50()
            seen = set(n50)
            combined = list(n50)
            for s in nnext:
                if s not in seen:
                    seen.add(s)
                    combined.append(s)
            return combined
        if index_key == "nasdaq100":
            return _fetch_nasdaq100()
        # nifty200 has no Wikipedia page – caller should use fallback
        return None
    except Exception as e:
        logger.warning("Failed to fetch %s from Wikipedia: %s", index_key, e)
        return None


def get_index_constituents(
    index_key: str,
    *,
    use_cache: bool = True,
    fallback_list: Optional[List[str]] = None,
) -> List[str]:
    """Return ticker list for the index, fetching from Wikipedia when possible.

    Parameters
    ----------
    index_key :
        One of ``nifty50``, ``nifty100``, ``nifty200``, ``nasdaq100``.
    use_cache :
        If True and we have cached result, return it without fetching.
    fallback_list :
        List to use when fetch fails or is unavailable (e.g. nifty200).

    Returns
    -------
    List of ticker strings (e.g. ``HDFCBANK.NS`` for NSE, ``AAPL`` for NASDAQ).
    """
    if use_cache and index_key in _CACHE:
        return _CACHE[index_key]

    tickers = _fetch_index(index_key)
    if tickers:
        _CACHE[index_key] = tickers
        return tickers

    if fallback_list:
        logger.info("Using fallback list for %s (%d tickers)", index_key, len(fallback_list))
        _CACHE[index_key] = fallback_list
        return fallback_list

    raise ValueError(
        f"Cannot get constituents for {index_key}: fetch failed and no fallback."
    )


def refresh_index(index_key: str) -> None:
    """Clear cache for the index so the next get_index_constituents() fetches fresh."""
    if index_key in _CACHE:
        del _CACHE[index_key]
        logger.info("Refreshed index cache for %s", index_key)
