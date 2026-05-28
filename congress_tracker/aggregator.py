"""
Main aggregator — pulls from all sources, deduplicates, enriches, and sorts.
"""
import hashlib
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from .config import Config, SPOTLIGHT_POLITICIANS, INSTITUTIONAL_INVESTORS, ARK_ETFS
from .sources import house_watcher, senate_watcher, finnhub_source, quiver_source, sec_edgar, ark_etf

logger = logging.getLogger(__name__)

# Amount range → midpoint estimate for sorting
AMOUNT_MIDPOINTS = {
    "$1,001 - $15,000": 8_000,
    "$15,001 - $50,000": 32_500,
    "$50,001 - $100,000": 75_000,
    "$100,001 - $250,000": 175_000,
    "$250,001 - $500,000": 375_000,
    "$500,001 - $1,000,000": 750_000,
    "$1,000,001 - $5,000,000": 3_000_000,
    "Over $5,000,000": 7_500_000,
    "$5,000,001 - $25,000,000": 15_000_000,
    "Over $25,000,000": 30_000_000,
}


class AggregatedData:
    def __init__(self):
        self.congress_trades: list[dict] = []
        self.spotlight_trades: list[dict] = []
        self.hot_tickers: list[tuple[str, int, int]] = []  # (ticker, buys, sells)
        self.institutional_filings: list[dict] = []
        self.ark_holdings: dict[str, dict] = {}
        self.generated_at: datetime = datetime.utcnow()
        self.errors: list[str] = []


def run(config: Config) -> AggregatedData:
    result = AggregatedData()
    days = config.lookback_days

    logger.info("=== Starting aggregation (lookback=%d days) ===", days)

    # --- Congress trades ---
    all_trades: list[dict] = []

    try:
        all_trades.extend(house_watcher.fetch(days))
    except Exception as e:
        msg = f"House Watcher error: {e}"
        logger.error(msg)
        result.errors.append(msg)

    try:
        all_trades.extend(senate_watcher.fetch(days))
    except Exception as e:
        msg = f"Senate Watcher error: {e}"
        logger.error(msg)
        result.errors.append(msg)

    if config.finnhub_api_key:
        try:
            all_trades.extend(finnhub_source.fetch(config.finnhub_api_key, days))
        except Exception as e:
            msg = f"Finnhub error: {e}"
            logger.error(msg)
            result.errors.append(msg)

    if config.quiver_api_key:
        try:
            all_trades.extend(quiver_source.fetch(config.quiver_api_key, days))
        except Exception as e:
            msg = f"Quiver error: {e}"
            logger.error(msg)
            result.errors.append(msg)

    all_trades = _deduplicate(all_trades)
    all_trades = _enrich(all_trades)
    all_trades.sort(key=lambda t: t["trade_date"], reverse=True)

    result.congress_trades = all_trades
    result.spotlight_trades = _filter_spotlight(all_trades)
    result.hot_tickers = _compute_hot_tickers(all_trades)

    logger.info("Total unique congress trades: %d", len(all_trades))

    # --- Institutional 13F filings ---
    for name, cik in INSTITUTIONAL_INVESTORS.items():
        try:
            filing = sec_edgar.fetch_latest_13f(cik, name)
            if filing:
                result.institutional_filings.append(filing)
                logger.info("13F loaded: %s (%s)", name, filing["filing_date"])
        except Exception as e:
            msg = f"SEC EDGAR error for {name}: {e}"
            logger.error(msg)
            result.errors.append(msg)

    # --- ARK ETF holdings ---
    try:
        result.ark_holdings = ark_etf.fetch_all_holdings()
    except Exception as e:
        msg = f"ARK ETF error: {e}"
        logger.error(msg)
        result.errors.append(msg)

    logger.info("=== Aggregation complete ===")
    return result


def _deduplicate(trades: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for t in trades:
        key = _trade_key(t)
        if key not in seen:
            seen.add(key)
            unique.append(t)
    return unique


def _trade_key(t: dict) -> str:
    parts = [
        t.get("politician", ""),
        t.get("ticker", ""),
        t.get("transaction_type", ""),
        str(t.get("trade_date", ""))[:10],
        t.get("amount_range", ""),
    ]
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def _enrich(trades: list[dict]) -> list[dict]:
    for t in trades:
        # Normalize politician name for spotlight matching
        t["politician_normalized"] = t.get("politician", "").strip().lower()
        t["is_spotlight"] = any(
            sp.lower() in t["politician_normalized"] for sp in SPOTLIGHT_POLITICIANS
        )
        # Estimate trade size
        t["amount_midpoint"] = _estimate_amount(t.get("amount_range", ""))
        # Delay between trade and disclosure
        if t.get("trade_date") and t.get("disclosure_date"):
            delay = (t["disclosure_date"] - t["trade_date"]).days
            t["disclosure_delay_days"] = max(0, delay)
        else:
            t["disclosure_delay_days"] = None
    return trades


def _estimate_amount(amount_str: str) -> int:
    for pattern, midpoint in AMOUNT_MIDPOINTS.items():
        if pattern.lower() in amount_str.lower():
            return midpoint
    # Try to parse raw numbers
    clean = amount_str.replace("$", "").replace(",", "").strip()
    try:
        return int(float(clean))
    except ValueError:
        pass
    return 0


def _filter_spotlight(trades: list[dict]) -> list[dict]:
    return [t for t in trades if t.get("is_spotlight")]


def _compute_hot_tickers(trades: list[dict]) -> list[tuple[str, int, int]]:
    """Return top tickers by total trade count with buy/sell breakdown."""
    ticker_buys: dict[str, int] = defaultdict(int)
    ticker_sells: dict[str, int] = defaultdict(int)
    for t in trades:
        ticker = t.get("ticker", "")
        if not ticker:
            continue
        if t.get("transaction_type") == "buy":
            ticker_buys[ticker] += 1
        elif t.get("transaction_type") == "sell":
            ticker_sells[ticker] += 1

    all_tickers = set(ticker_buys) | set(ticker_sells)
    ranked = sorted(
        all_tickers,
        key=lambda x: ticker_buys[x] + ticker_sells[x],
        reverse=True,
    )
    return [(t, ticker_buys[t], ticker_sells[t]) for t in ranked[:20]]
