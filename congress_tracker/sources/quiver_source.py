"""
Quiver Quantitative congressional trading API.
Paid plan required (~$30/mo): https://www.quiverquant.com/
Set QUIVER_API_KEY env var for access.
Provides the richest dataset including performance metrics.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)
BASE_URL = "https://api.quiverquant.com/beta"


def fetch(api_key: str, lookback_days: int = 30) -> list[dict]:
    if not api_key:
        logger.info("Quiver: no API key, skipping")
        return []

    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    headers = {"Authorization": f"Token {api_key}"}

    all_trades: list[dict] = []
    # Fetch recent trades endpoint
    url = f"{BASE_URL}/live/congresstrading"
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        raw = resp.json()
        for row in raw:
            trade = _normalize(row)
            if trade and trade["trade_date"] >= cutoff:
                all_trades.append(trade)
        logger.info("Quiver: %d trades fetched", len(all_trades))
    except Exception as exc:
        logger.warning("Quiver fetch failed: %s", exc)

    return all_trades


def fetch_politician_performance(api_key: str) -> list[dict]:
    """Fetch per-politician performance metrics (cumulative returns)."""
    if not api_key:
        return []
    headers = {"Authorization": f"Token {api_key}"}
    url = f"{BASE_URL}/live/congressperf"
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("Quiver performance fetch failed: %s", exc)
        return []


def _normalize(row: dict) -> Optional[dict]:
    try:
        ticker = (row.get("Ticker") or "").strip().upper()
        if not ticker:
            return None
        trade_date = _parse_date(row.get("Date", "") or row.get("TransactionDate", ""))
        if not trade_date:
            return None
        return {
            "source": "quiver",
            "chamber": row.get("Chamber", ""),
            "politician": row.get("Representative", "Unknown"),
            "party": row.get("Party", ""),
            "state": row.get("State", ""),
            "ticker": ticker,
            "asset_description": row.get("AssetDescription", ""),
            "transaction_type": _clean_type(row.get("Transaction", "")),
            "amount_range": row.get("Range", ""),
            "trade_date": trade_date,
            "disclosure_date": _parse_date(row.get("ReportDate", "")),
            "district": row.get("District", ""),
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
