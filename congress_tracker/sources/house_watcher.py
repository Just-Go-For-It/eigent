"""
House Stock Watcher - free, no API key required.
Data: https://housestockwatcher.com/api
Covers all House member STOCK Act disclosures.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Primary S3 source (faster, full history)
S3_URL = "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"
# Fallback REST API
API_URL = "https://housestockwatcher.com/api"


def fetch(lookback_days: int = 30) -> list[dict]:
    """Return normalized House trades within the lookback window."""
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    raw = _fetch_raw()
    trades = []
    for row in raw:
        trade = _normalize(row)
        if trade and trade["trade_date"] >= cutoff:
            trades.append(trade)
    logger.info("House Watcher: %d trades in last %d days", len(trades), lookback_days)
    return trades


def _fetch_raw() -> list[dict]:
    for url in (S3_URL, API_URL):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as exc:
            logger.warning("House Watcher failed (%s): %s", url, exc)
    return []


def _normalize(row: dict) -> Optional[dict]:
    try:
        date_str = row.get("transaction_date") or row.get("disclosure_date") or ""
        trade_date = _parse_date(date_str)
        if not trade_date:
            return None
        ticker = (row.get("ticker") or "").strip().upper()
        if not ticker or ticker in ("--", "N/A", ""):
            return None
        return {
            "source": "house_watcher",
            "chamber": "House",
            "politician": row.get("representative", "Unknown"),
            "party": row.get("party", ""),
            "state": row.get("state", ""),
            "ticker": ticker,
            "asset_description": row.get("asset_description", ""),
            "transaction_type": _clean_type(row.get("type", "")),
            "amount_range": row.get("amount", ""),
            "trade_date": trade_date,
            "disclosure_date": _parse_date(row.get("disclosure_date", "")),
            "district": row.get("district", ""),
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
