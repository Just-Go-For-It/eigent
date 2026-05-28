"""
ARK ETF daily holdings tracker (Cathie Wood).
ARK publishes daily CSV holdings for all their ETFs — completely free.
"""
import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)

ARK_HOLDINGS_URL = "https://ark-funds.com/wp-content/uploads/funds-etf-csv/{ticker}_holdings.csv"

# Alternative direct URLs
ARK_DIRECT_URLS = {
    "ARKK": "https://ark-funds.com/wp-content/uploads/funds-etf-csv/ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv",
    "ARKQ": "https://ark-funds.com/wp-content/uploads/funds-etf-csv/ARK_AUTONOMOUS_TECHNOLOGY_&_ROBOTICS_ETF_ARKQ_HOLDINGS.csv",
    "ARKW": "https://ark-funds.com/wp-content/uploads/funds-etf-csv/ARK_NEXT_GENERATION_INTERNET_ETF_ARKW_HOLDINGS.csv",
    "ARKG": "https://ark-funds.com/wp-content/uploads/funds-etf-csv/ARK_GENOMIC_REVOLUTION_ETF_ARKG_HOLDINGS.csv",
    "ARKF": "https://ark-funds.com/wp-content/uploads/funds-etf-csv/ARK_FINTECH_INNOVATION_ETF_ARKF_HOLDINGS.csv",
    "ARKX": "https://ark-funds.com/wp-content/uploads/funds-etf-csv/ARK_SPACE_EXPLORATION_&_INNOVATION_ETF_ARKX_HOLDINGS.csv",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CongressTracker/1.0)",
    "Accept": "text/csv,*/*",
}


def fetch_all_holdings() -> dict[str, dict]:
    """Fetch current holdings for all ARK ETFs. Returns {ticker: {date, holdings[]}}."""
    results = {}
    for ticker, url in ARK_DIRECT_URLS.items():
        holding = fetch_etf_holdings(ticker, url)
        if holding:
            results[ticker] = holding
    return results


def fetch_etf_holdings(ticker: str, url: Optional[str] = None) -> Optional[dict]:
    url = url or ARK_HOLDINGS_URL.format(ticker=ticker)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        holdings = _parse_csv(resp.text)
        date = holdings[0].get("date", "") if holdings else ""
        logger.info("ARK %s: %d holdings fetched for %s", ticker, len(holdings), date)
        return {"ticker": ticker, "date": date, "holdings": holdings}
    except Exception as exc:
        logger.warning("ARK ETF fetch failed for %s: %s", ticker, exc)
        return None


def _parse_csv(text: str) -> list[dict]:
    holdings = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        # ARK CSV columns: date, fund, company, ticker, cusip, shares, market value ($), weight (%)
        ticker = (row.get("ticker") or "").strip().upper()
        company = (row.get("company") or "").strip()
        if not ticker and not company:
            continue
        try:
            market_value = float((row.get("market value ($)") or row.get("market value") or "0").replace(",", "").replace("$", ""))
        except ValueError:
            market_value = 0.0
        try:
            weight = float((row.get("weight (%)") or row.get("weight") or "0").replace("%", ""))
        except ValueError:
            weight = 0.0
        try:
            shares = float((row.get("shares") or "0").replace(",", ""))
        except ValueError:
            shares = 0.0

        holdings.append({
            "date": row.get("date", "").strip(),
            "company": company,
            "ticker": ticker,
            "cusip": row.get("cusip", "").strip(),
            "shares": shares,
            "market_value": market_value,
            "weight_pct": weight,
        })
    # Sort by weight descending
    holdings.sort(key=lambda x: x["weight_pct"], reverse=True)
    return holdings


def format_ark_summary(etf_data: dict[str, dict], top_n: int = 10) -> str:
    if not etf_data:
        return "  No ARK ETF data available.\n"
    lines = []
    for ticker, data in etf_data.items():
        lines.append(f"\n  {ticker} (as of {data['date']}):")
        for h in data["holdings"][:top_n]:
            sym = f"[{h['ticker']}]" if h["ticker"] else ""
            val = _fmt_usd(h["market_value"])
            lines.append(f"    {h['company']:<35s} {sym:<8s} {h['weight_pct']:>6.2f}%  {val}")
    return "\n".join(lines)


def _fmt_usd(v: float) -> str:
    if v >= 1_000_000_000:
        return f"${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"
