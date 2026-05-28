"""
Generates the daily digest report in text, markdown, and JSON formats.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .aggregator import AggregatedData
from .sources.sec_edgar import format_holdings_summary, _fmt_usd as _sec_fmt
from .sources.ark_etf import format_ark_summary


def generate(data: AggregatedData, reports_dir: str = "congress_tracker/reports") -> dict[str, str]:
    """Generate report files and return their paths."""
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    date_str = data.generated_at.strftime("%Y-%m-%d")
    ts_str = data.generated_at.strftime("%Y%m%d_%H%M%S")

    md_path = os.path.join(reports_dir, f"digest_{ts_str}.md")
    json_path = os.path.join(reports_dir, f"digest_{ts_str}.json")
    latest_md = os.path.join(reports_dir, "latest.md")
    latest_json = os.path.join(reports_dir, "latest.json")

    md_content = _build_markdown(data, date_str)
    json_content = _build_json(data)

    Path(md_path).write_text(md_content, encoding="utf-8")
    Path(json_path).write_text(json_content, encoding="utf-8")
    Path(latest_md).write_text(md_content, encoding="utf-8")
    Path(latest_json).write_text(json_content, encoding="utf-8")

    return {"markdown": md_path, "json": json_path, "latest_md": latest_md, "latest_json": latest_json}


def _build_markdown(data: AggregatedData, date_str: str) -> str:
    sections = []

    sections.append(f"# Congress & Insider Trading Digest — {date_str}")
    sections.append(f"_Generated at {data.generated_at.strftime('%Y-%m-%d %H:%M UTC')}_\n")

    # --- Summary stats ---
    buy_count = sum(1 for t in data.congress_trades if t.get("transaction_type") == "buy")
    sell_count = sum(1 for t in data.congress_trades if t.get("transaction_type") == "sell")
    total_count = len(data.congress_trades)
    sections.append("## Summary")
    sections.append(f"- **Total congress trades (last {_lookback_label(data)}):** {total_count}")
    sections.append(f"- **Buys:** {buy_count}  |  **Sells:** {sell_count}")
    sections.append(f"- **Spotlight politician trades:** {len(data.spotlight_trades)}")
    sections.append(f"- **Institutional 13F filings loaded:** {len(data.institutional_filings)}")
    if data.errors:
        sections.append(f"\n> ⚠️ Errors: {len(data.errors)} source(s) failed. See JSON for details.")
    sections.append("")

    # --- Spotlight politicians ---
    sections.append("## 🔦 Spotlight Politician Trades")
    sections.append("_Tracking historically top-performing congress members_\n")
    if data.spotlight_trades:
        sections.append(_trades_table(data.spotlight_trades[:50]))
    else:
        sections.append("_No spotlight politician trades in this period._\n")

    # --- Hot tickers ---
    sections.append("## 🔥 Hot Tickers (Most Traded by Congress)")
    if data.hot_tickers:
        sections.append("| Ticker | Buys | Sells | Total |")
        sections.append("|--------|------|-------|-------|")
        for ticker, buys, sells in data.hot_tickers[:15]:
            sections.append(f"| **{ticker}** | {buys} | {sells} | {buys+sells} |")
    else:
        sections.append("_No data._")
    sections.append("")

    # --- All recent congress trades ---
    sections.append("## 📋 All Recent Congress Trades")
    sections.append(f"_Showing latest {min(100, len(data.congress_trades))} of {len(data.congress_trades)} trades_\n")
    if data.congress_trades:
        sections.append(_trades_table(data.congress_trades[:100]))
    else:
        sections.append("_No trades found for this period._\n")

    # --- Buys by amount ---
    large_buys = [t for t in data.congress_trades if t.get("transaction_type") == "buy" and t.get("amount_midpoint", 0) >= 100_000]
    large_buys.sort(key=lambda t: t.get("amount_midpoint", 0), reverse=True)
    sections.append("## 💰 Largest Buy Trades (≥$100K estimated)")
    if large_buys:
        sections.append(_trades_table(large_buys[:25]))
    else:
        sections.append("_No large buys found._\n")

    # --- Institutional investors ---
    sections.append("## 🏦 Institutional Investors — Latest 13F Holdings")
    sections.append("_Quarterly filings from SEC EDGAR (may lag by up to 45 days)_\n")
    if data.institutional_filings:
        for filing in data.institutional_filings:
            sections.append(f"### {filing['investor']}")
            sections.append(f"**Filed:** {filing['filing_date']}  |  **Accession:** `{filing['accession_number']}`\n")
            if filing["holdings"]:
                total_val = sum(h["value_usd"] for h in filing["holdings"])
                sections.append(f"_Portfolio value (top positions): {_fmt_usd(total_val)}_\n")
                sections.append("| # | Issuer | Value | % Portfolio |")
                sections.append("|---|--------|-------|-------------|")
                for i, h in enumerate(filing["holdings"][:20], 1):
                    pct = (h["value_usd"] / total_val * 100) if total_val else 0
                    put_call = f" `{h['put_call']}`" if h.get("put_call") else ""
                    sections.append(f"| {i} | {h['issuer']}{put_call} | {_fmt_usd(h['value_usd'])} | {pct:.1f}% |")
                sections.append("")
            else:
                sections.append("_No holdings data parsed._\n")
    else:
        sections.append("_No institutional filing data available._\n")

    # --- ARK ETF ---
    sections.append("## 🚀 ARK ETF Holdings (Cathie Wood)")
    if data.ark_holdings:
        for etf_ticker, etf_data in data.ark_holdings.items():
            sections.append(f"\n### {etf_ticker}")
            sections.append(f"_As of {etf_data['date']}_\n")
            sections.append("| Company | Ticker | Weight | Market Value |")
            sections.append("|---------|--------|--------|--------------|")
            for h in etf_data["holdings"][:10]:
                sym = h["ticker"] if h["ticker"] else "—"
                sections.append(f"| {h['company']} | {sym} | {h['weight_pct']:.2f}% | {_fmt_usd(h['market_value'])} |")
    else:
        sections.append("_No ARK ETF data available._\n")

    sections.append("")
    sections.append("---")
    sections.append("_Data sources: House Stock Watcher · Senate Stock Watcher · Finnhub · SEC EDGAR · ARK ETF_")
    sections.append("_Congressional data reflects STOCK Act disclosures. Trades may be disclosed up to 45 days after execution._")

    return "\n".join(sections)


def _build_json(data: AggregatedData) -> str:
    def _serialize_trade(t: dict) -> dict:
        out = dict(t)
        for k in ("trade_date", "disclosure_date"):
            if isinstance(out.get(k), datetime):
                out[k] = out[k].isoformat()
        return out

    payload = {
        "generated_at": data.generated_at.isoformat(),
        "stats": {
            "total_congress_trades": len(data.congress_trades),
            "spotlight_trades": len(data.spotlight_trades),
            "buy_count": sum(1 for t in data.congress_trades if t.get("transaction_type") == "buy"),
            "sell_count": sum(1 for t in data.congress_trades if t.get("transaction_type") == "sell"),
        },
        "hot_tickers": [
            {"ticker": t, "buys": b, "sells": s} for t, b, s in data.hot_tickers
        ],
        "spotlight_trades": [_serialize_trade(t) for t in data.spotlight_trades],
        "all_congress_trades": [_serialize_trade(t) for t in data.congress_trades],
        "institutional_filings": data.institutional_filings,
        "ark_holdings": data.ark_holdings,
        "errors": data.errors,
    }
    return json.dumps(payload, indent=2, default=str)


def _trades_table(trades: list[dict]) -> str:
    lines = [
        "| Date | Politician | Chamber | Ticker | Type | Amount | Source |",
        "|------|-----------|---------|--------|------|--------|--------|",
    ]
    for t in trades:
        date = t["trade_date"].strftime("%Y-%m-%d") if isinstance(t.get("trade_date"), datetime) else str(t.get("trade_date", ""))[:10]
        politician = t.get("politician", "")
        chamber = t.get("chamber", "")
        ticker = t.get("ticker", "")
        tx_type = t.get("transaction_type", "").upper()
        amount = t.get("amount_range", "")
        source = t.get("source", "")
        type_emoji = "🟢" if tx_type == "BUY" else "🔴" if tx_type == "SELL" else "🔵"
        lines.append(f"| {date} | {politician} | {chamber} | **{ticker}** | {type_emoji} {tx_type} | {amount} | {source} |")
    lines.append("")
    return "\n".join(lines)


def _fmt_usd(v: int) -> str:
    if v >= 1_000_000_000:
        return f"${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v}"


def _lookback_label(data: AggregatedData) -> str:
    if not data.congress_trades:
        return "N/A days"
    dates = [t["trade_date"] for t in data.congress_trades if isinstance(t.get("trade_date"), datetime)]
    if not dates:
        return "N/A"
    oldest = min(dates)
    days = (data.generated_at - oldest).days
    return f"{days} days"


def print_to_console(data: AggregatedData):
    """Print a concise summary to stdout."""
    print(f"\n{'='*70}")
    print(f"  CONGRESS TRADING DIGEST — {data.generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*70}")
    print(f"\n  Total trades found:    {len(data.congress_trades)}")
    print(f"  Spotlight trades:      {len(data.spotlight_trades)}")
    buy_c = sum(1 for t in data.congress_trades if t.get("transaction_type") == "buy")
    sell_c = sum(1 for t in data.congress_trades if t.get("transaction_type") == "sell")
    print(f"  Buys / Sells:          {buy_c} / {sell_c}")

    if data.spotlight_trades:
        print(f"\n  --- SPOTLIGHT POLITICIANS ({len(data.spotlight_trades)} trades) ---")
        for t in data.spotlight_trades[:20]:
            date_s = t["trade_date"].strftime("%Y-%m-%d") if isinstance(t.get("trade_date"), datetime) else ""
            tx = t.get("transaction_type", "?").upper()
            print(f"  {date_s}  {t.get('politician',''):<25s}  {t.get('ticker',''):>6s}  {tx:<5s}  {t.get('amount_range','')}")

    if data.hot_tickers:
        print(f"\n  --- HOT TICKERS ---")
        for ticker, buys, sells in data.hot_tickers[:10]:
            bar = "B" * buys + "S" * sells
            print(f"  {ticker:<8s}  {buys:3d} buys  {sells:3d} sells  [{bar[:30]}]")

    if data.institutional_filings:
        print(f"\n  --- INSTITUTIONAL 13F FILINGS ---")
        for filing in data.institutional_filings:
            print(f"\n  {filing['investor']} (filed {filing['filing_date']})")
            top5 = filing["holdings"][:5]
            for h in top5:
                print(f"    {h['issuer']:<35s}  {_fmt_usd(h['value_usd'])}")

    if data.errors:
        print(f"\n  --- ERRORS ---")
        for e in data.errors:
            print(f"  [!] {e}")

    print(f"\n{'='*70}\n")
