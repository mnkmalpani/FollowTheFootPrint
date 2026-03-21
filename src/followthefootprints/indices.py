"""Centralised stock index lists.

All NSE tickers carry the ``.NS`` suffix required by yfinance.
NASDAQ/US tickers have no suffix.

Index constituents are auto-fetched from Wikipedia; fallback lists below
are used when fetch fails or for indices without a Wikipedia page (e.g. Nifty 200).
"""

from typing import Dict, List

from .index_fetcher import get_index_constituents, refresh_index

__all__ = [
    "INDEX_LISTS",
    "get_tickers",
    "refresh_index_cache",
]

# Fallback lists when Wikipedia fetch fails or is unavailable (e.g. Nifty 200).
# Kept in sync for reference; prefer get_tickers() which fetches live data.
NASDAQ100_LIST: List[str] = [
    "ATVI", "ADBE", "ADP", "ABNB", "ALGN", "GOOGL", "GOOG", "AMZN", "AMD",
    "AEP", "AMGN", "ADI", "ANSS", "AAPL", "AMAT", "ASML", "AZN", "TEAM",
    "ADSK", "BKR", "BIIB", "BKNG", "AVGO", "CDNS", "CHTR", "CTAS", "CSCO",
    "CTSH", "CMCSA", "CEG", "CPRT", "CSGP", "COST", "CRWD", "CSX", "DDOG",
    "DXCM", "FANG", "DLTR", "EBAY", "EA", "ENPH", "EXC", "FAST", "FISV",
    "FTNT", "GILD", "GFS", "HON", "IDXX", "ILMN", "INTC", "INTU", "ISRG",
    "JD", "KDP", "KLAC", "KHC", "LRCX", "LCID", "LULU", "MAR", "MRVL",
    "MELI", "META", "MCHP", "MU", "MSFT", "MRNA", "MDLZ", "MNST", "NFLX",
    "NVDA", "NXPI", "ORLY", "ODFL", "PCAR", "PANW", "PAYX", "PYPL", "PDD",
    "PEP", "QCOM", "REGN", "RIVN", "ROST", "SGEN", "SIRI", "SBUX", "SNPS",
    "TMUS", "TSLA", "TXN", "VRSK", "VRTX", "WBA", "WBD", "WDAY", "XEL",
    "ZM", "ZS",
]

NIFTY100_LIST: List[str] = [
    "INDUSINDBK.NS", "HDFCLIFE.NS", "EICHERMOT.NS", "SBICARD.NS", "DABUR.NS",
    "APOLLOHOSP.NS", "POWERGRID.NS", "DLF.NS", "AXISBANK.NS", "BAJAJFINSV.NS",
    "PNB.NS", "KOTAKBANK.NS", "ADANIENT.NS", "ZOMATO.NS", "HINDALCO.NS",
    "JUBLFOOD.NS", "ICICIBANK.NS", "SBIN.NS", "TATAMOTORS.NS", "ASIANPAINT.NS",
    "BAJFINANCE.NS", "MUTHOOTFIN.NS", "DMART.NS", "BOSCHLTD.NS", "ONGC.NS",
    "HDFC.NS", "SRF.NS", "ADANIPORTS.NS", "BANKBARODA.NS", "MARUTI.NS",
    "ACC.NS", "ITC.NS", "HDFCBANK.NS", "PAYTM.NS", "HDFCAMC.NS",
    "RELIANCE.NS", "HAVELLS.NS", "JSWSTEEL.NS", "SBILIFE.NS", "LICI.NS",
    "HINDUNILVR.NS", "BIOCON.NS", "TATACONSUM.NS", "NESTLEIND.NS",
    "PIDILITIND.NS", "CHOLAFIN.NS", "INDIGO.NS", "BAJAJ-AUTO.NS", "VEDL.NS",
    "PIIND.NS", "ADANIGREEN.NS", "TITAN.NS", "ICICIPRULI.NS", "TATASTEEL.NS",
    "MARICO.NS", "BRITANNIA.NS", "ZYDUSLIFE.NS", "M&M.NS", "SIEMENS.NS",
    "CIPLA.NS", "ULTRACEMCO.NS", "ICICIGI.NS", "UPL.NS", "TATAPOWER.NS",
    "GAIL.NS", "COLPAL.NS", "BHARTIARTL.NS", "MCDOWELL-N.NS", "DRREDDY.NS",
    "TORNTPHARM.NS", "GODREJCP.NS", "NYKAA.NS", "PGHH.NS", "AMBUJACEM.NS",
    "DIVISLAB.NS", "BERGEPAINT.NS", "GRASIM.NS", "COALINDIA.NS", "NAUKRI.NS",
    "WIPRO.NS", "IOC.NS", "SHREECEM.NS", "GLAND.NS", "LUPIN.NS",
    "ADANITRANS.NS", "HEROMOTOCO.NS", "LT.NS", "SUNPHARMA.NS", "SAIL.NS",
    "BAJAJHLDNG.NS", "BPCL.NS", "INDUSTOWER.NS", "NTPC.NS", "TCS.NS",
    "HCLTECH.NS", "TECHM.NS", "BANDHANBNK.NS", "INFY.NS", "LTIM.NS",
    "HAL.NS",
]

# Raw symbols (without exchange suffix) – ``.NS`` added below
_NIFTY200_BASE: List[str] = [
    "NYKAA", "ZOMATO", "PFC", "HINDALCO", "HEROMOTOCO", "APOLLOHOSP",
    "ASTRAL", "JINDALSTEL", "INDIANB", "HAL", "DLF", "HONAUT", "TRENT",
    "RECLTD", "MPHASIS", "TATACOMM", "POLYCAB", "TVSMOTOR", "NMDC", "ABB",
    "TATASTEEL", "OBEROIRLTY", "PAYTM", "MARUTI", "M&M", "JSWSTEEL",
    "AMBUJACEM", "GODREJPROP", "MOTHERSON", "LAURUSLABS", "SAIL", "INDIGO",
    "DRREDDY", "TTML", "SUNPHARMA", "SRF", "M&MFIN", "ABBOTINDIA", "DIXON",
    "BHEL", "LT", "BHARTIARTL", "CANBK", "IPCALAB", "PNB", "CONCOR",
    "NAUKRI", "TITAN", "PERSISTENT", "LTTS", "BANKBARODA", "INDUSTOWER",
    "POONAWALLA", "ZYDUSLIFE", "LUPIN", "UPL", "ACC", "COROMANDEL",
    "BOSCHLTD", "GODREJCP", "HDFCAMC", "VBL", "ITC", "LALPATHLAB",
    "POWERGRID", "BAJAJ-AUTO", "ZEEL", "IDEA", "SBICARD", "NESTLEIND",
    "TATAELXSI", "ONGC", "SBIN", "SUNTV", "RAMCOCEM", "INDUSINDBK",
    "FEDERALBNK", "NAVINFLUOR", "PGHH", "VEDL", "DMART", "BRITANNIA",
    "COFORGE", "DEEPAKNTR", "LICHSGFIN", "HINDUNILVR", "ABCAPITAL", "PEL",
    "GRASIM", "TORNTPOWER", "AXISBANK", "L&TFH", "AUBANK", "UNIONBANK",
    "SHRIRAMFIN", "ADANIPORTS", "AUROPHARMA", "ICICIGI", "SIEMENS", "LTIM",
    "BAJAJFINSV", "MSUMI", "SONACOMS", "ADANIPOWER", "HINDZINC", "TRIDENT",
    "YESBANK", "JUBLFOOD", "DABUR", "OFSS", "BERGEPAINT", "KOTAKBANK",
    "PRESTIGE", "HAVELLS", "TATACONSUM", "IDFCFIRSTB", "BEL", "CUMMINSIND",
    "COALINDIA", "HDFCBANK", "TATAPOWER", "INDHOTEL", "BANKINDIA", "LICI",
    "ICICIBANK", "APOLLOTYRE", "CIPLA", "BAJAJHLDNG", "TORNTPHARM",
    "DALBHARAT", "MCDOWELL-N", "TATAMOTORS", "ULTRACEMCO", "COLPAL",
    "DIVISLAB", "ALKEM", "TATACHEM", "DEVYANI", "TECHM", "NTPC", "EICHERMOT",
    "BALKRISIND", "INFY", "HDFC", "JSWENERGY", "BAJFINANCE", "PETRONET",
    "CHOLAFIN", "TIINDIA", "ASIANPAINT", "MAXHEALTH", "IRFC", "RELIANCE",
    "SBILIFE", "CROMPTON", "HCLTECH", "WIPRO", "NHPC", "ABFRL", "SHREECEM",
    "MUTHOOTFIN", "ESCORTS", "TCS", "GAIL", "ASHOKLEY", "HINDPETRO",
    "VOLTAS", "PIDILITIND", "IOC", "IRCTC", "FORTIS", "WHIRLPOOL", "UBL",
    "SYNGENE", "BHARATFORG", "GLAND", "AWL", "HDFCLIFE", "PIIND",
    "DELHIVERY", "BATAINDIA", "BANDHANBNK", "ADANIGREEN", "ICICIPRULI",
    "MARICO", "MRF", "BPCL", "FLUOROCHEM", "POLICYBZR", "PAGEIND",
    "PATANJALI", "MFSL", "OIL", "BIOCON", "ADANIENT", "CGPOWER", "GUJGASLTD",
    "ADANITRANS", "IGL", "ATGL",
]

NIFTY200_LIST: List[str] = [f"{t}.NS" for t in _NIFTY200_BASE]

NIFTY50_LIST: List[str] = [
    "HDFCBANK.NS", "RELIANCE.NS", "ICICIBANK.NS", "INFY.NS", "HDFC.NS",
    "TCS.NS", "KOTAKBANK.NS", "HINDUNILVR.NS", "AXISBANK.NS", "ITC.NS",
    "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "WIPRO.NS",
    "MARUTI.NS", "TITAN.NS", "ULTRACEMCO.NS", "ADANIENT.NS", "NTPC.NS",
    "SUNPHARMA.NS", "TATAMOTORS.NS", "LT.NS", "BAJAJFINSV.NS", "NESTLEIND.NS",
    "ONGC.NS", "M&M.NS", "POWERGRID.NS", "TATACONSUM.NS", "JSWSTEEL.NS",
]

INDEX_LISTS: Dict[str, List[str]] = {
    "nasdaq100": NASDAQ100_LIST,
    "nifty100": NIFTY100_LIST,
    "nifty200": NIFTY200_LIST,
    "nifty50": NIFTY50_LIST,
}


def get_tickers(index_key: str, *, use_cache: bool = True) -> List[str]:
    """Return ticker list for the index, auto-fetched from Wikipedia when possible.

    Uses fallback lists when fetch fails or for indices without a Wikipedia page.
    """
    fallbacks: Dict[str, List[str]] = {
        "nasdaq100": NASDAQ100_LIST,
        "nifty100": NIFTY100_LIST,
        "nifty200": NIFTY200_LIST,
        "nifty50": NIFTY50_LIST,
    }
    return get_index_constituents(
        index_key,
        use_cache=use_cache,
        fallback_list=fallbacks.get(index_key),
    )


def refresh_index_cache(index_key: str) -> None:
    """Clear cache for the index so next get_tickers() fetches fresh constituents."""
    refresh_index(index_key)
