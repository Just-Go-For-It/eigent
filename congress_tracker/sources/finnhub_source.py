"""
Finnhub congressional trading endpoint.
Free tier API key required: https://finnhub.io/register
Set FINNHUB_API_KEY env var.
Covers both House and Senate with richer metadata.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)
BASE_URL = "https://finnhub.io/api/v1"


def fetch(api_key: str, lookback_days: int = 30) -> list[dict]:
    if not api_key:
        logger.info("Finnhub: no API key, skipping")
        return []

    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    from_date = cutoff.strftime("%Y-%m-%d")
    to_date = datetime.utcnow().strftime("%Y-%m-%d")

    url = f"{BASE_URL}/stock/congressional-trading"
    params = {"token": api_key, "from": from_date, "to": to_date}

    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        raw = data if isinstance(data, list) else data.get("data", [])
        trades = [t for t in (_normalize(r) for r in raw) if t]
        logger.info("Finnhub: %d trades fetched", len(trades))
        return trades
    except Exception as exc:
        logger.warning("Finnhub fetch failed: %s", exc)
        return []


def _normalize(row: dict) -> Optional[dict]:
    try:
        ticker = (row.get("symbol") or "").strip().upper()
        if not ticker:
            return None
        trade_date = _parse_date(row.get("transactionDate", ""))
        if not trade_date:
            return None
        return {
            "source": "finnhub",
            "chamber": row.get("chamber", ""),
            "politician": row.get("name", "Unknown"),
            "party": row.get("party", ""),
            "state": row.get("state", ""),
            "ticker": ticker,
            "asset_description": row.get("assetDescription", ""),
            "transaction_type": _clean_type(row.get("transactionType", "")),
            "amount_range": _format_amount(row.get("amount", 0)),
            "trade_date": trade_date,
            "disclosure_date": _parse_date(row.get("filingDate", "")),
            "district": "",
            "link": "",
        }
    except Exception:
        return None


def _parse_date(s: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
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
    return t or "unknown"


def _format_amount(amount) -> str:
    try:
        v = float(amount)
        if v >= 1_000_000:
            return f"${v/1_000_000:.1f}M"
        if v >= 1_000:
            return f"${v/1_000:.0f}K"
        return f"${v:.0f}"
    except (TypeError, ValueError):
        return str(amount) if amount else ""
