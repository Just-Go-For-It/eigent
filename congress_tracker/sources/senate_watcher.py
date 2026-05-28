"""
Senate Stock Watcher - free, no API key required.
Data: https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com
Covers all Senate STOCK Act disclosures (eFD system).
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)

S3_URL = "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/aggregate/all_transactions.json"
FALLBACK_URL = "https://efts.sec.gov/LATEST/search-index?q=%22purchase%22+%22senator%22&forms=4&dateRange=custom"


def fetch(lookback_days: int = 30) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    raw = _fetch_raw()
    trades = []
    for row in raw:
        trade = _normalize(row)
        if trade and trade["trade_date"] >= cutoff:
            trades.append(trade)
    logger.info("Senate Watcher: %d trades in last %d days", len(trades), lookback_days)
    return trades


def _fetch_raw() -> list[dict]:
    try:
        resp = requests.get(S3_URL, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("Senate Watcher S3 failed: %s", exc)
    return []


def _normalize(row: dict) -> Optional[dict]:
    try:
        trade_date = _parse_date(row.get("transaction_date", ""))
        if not trade_date:
            return None
        ticker = (row.get("ticker") or "").strip().upper()
        if not ticker or ticker in ("--", "N/A", ""):
            return None
        senator = row.get("senator") or row.get("first_name", "") + " " + row.get("last_name", "")
        return {
            "source": "senate_watcher",
            "chamber": "Senate",
            "politician": senator.strip(),
            "party": row.get("party", ""),
            "state": row.get("state", ""),
            "ticker": ticker,
            "asset_description": row.get("asset_description", ""),
            "transaction_type": _clean_type(row.get("type", "")),
            "amount_range": row.get("amount", ""),
            "trade_date": trade_date,
            "disclosure_date": _parse_date(row.get("disclosure_date", "")),
            "district": "",
            "link": row.get("ptr_link", ""),
        }
    except Exception:
        return None


def _parse_date(s: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except (ValueError, AttributeError):
            pass
    return None


def _clean_type(t: str) -> str:
    t = t.lower()
    if "purchase" in t or "buy" in t:
        return "buy"
    if "sale" in t or "sell" in t:
        return "sell"
    if "exchange" in t:
        return "exchange"
    return t or "unknown"
