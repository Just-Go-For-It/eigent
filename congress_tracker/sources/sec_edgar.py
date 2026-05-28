"""
SEC EDGAR 13F filing tracker for institutional investors.
Completely free — uses the public EDGAR full-text search and data APIs.
Tracks Warren Buffett, Michael Burry, Druckenmiller, Tepper, Ackman, etc.
"""
import logging
from datetime import datetime
from typing import Optional
import xml.etree.ElementTree as ET

import requests

logger = logging.getLogger(__name__)

# SEC EDGAR requires a 10-digit zero-padded CIK in submissions URLs
EDGAR_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_FILING_DOC = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{doc_name}"
EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index?q=%22{query}%22&forms=13F-HR&dateRange=custom&startdt={start}&enddt={end}"

HEADERS = {
    "User-Agent": "CongressTracker research@example.com",
    "Accept-Encoding": "gzip, deflate",
}


def fetch_latest_13f(cik: str, investor_name: str) -> Optional[dict]:
    """Fetch the most recent 13F filing for a given CIK and return top holdings."""
    # EDGAR submissions API requires 10-digit zero-padded CIK
    padded_cik = cik.lstrip("0").zfill(10)
    url = EDGAR_SUBMISSIONS.format(cik=padded_cik)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("EDGAR submissions fetch failed for %s: %s", investor_name, exc)
        return None

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accessions = filings.get("accessionNumber", [])
    dates = filings.get("filingDate", [])
    primary_docs = filings.get("primaryDocument", [])

    # Find the most recent 13F-HR
    for i, form in enumerate(forms):
        if form == "13F-HR":
            accession = accessions[i].replace("-", "")
            filing_date = dates[i]
            primary_doc = primary_docs[i]
            holdings = _parse_13f_holdings(cik, accession, primary_doc)
            return {
                "investor": investor_name,
                "cik": cik,
                "filing_date": filing_date,
                "accession_number": accessions[i],
                "holdings": holdings[:30],  # top 30 positions
            }

    logger.info("No 13F-HR found for %s (CIK %s)", investor_name, cik)
    return None


def _parse_13f_holdings(cik: str, accession: str, primary_doc: str) -> list[dict]:
    """Download the 13F XML/HTML and extract holdings table."""
    cik_clean = cik.lstrip("0")
    base_url = f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{accession}/"

    # Try to find the info table XML document
    index_url = base_url + "index.json"
    try:
        resp = requests.get(index_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        index = resp.json()
        files = index.get("directory", {}).get("item", [])
    except Exception:
        files = []

    xml_doc = None
    for f in files:
        name = f.get("name", "").lower()
        if "infotable" in name and name.endswith(".xml"):
            xml_doc = f["name"]
            break
    if not xml_doc:
        for f in files:
            name = f.get("name", "").lower()
            if name.endswith(".xml") and name != "primary_doc.xml":
                xml_doc = f["name"]
                break

    if not xml_doc:
        return []

    xml_url = base_url + xml_doc
    try:
        resp = requests.get(xml_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return _parse_infotable_xml(resp.text)
    except Exception as exc:
        logger.warning("Failed to parse 13F XML for CIK %s: %s", cik, exc)
        return []


def _parse_infotable_xml(xml_text: str) -> list[dict]:
    """Parse the SEC 13F infotable XML into a list of holdings dicts."""
    holdings = []
    # Strip namespace for easier parsing
    xml_text = xml_text.replace(' xmlns="', ' xmlnsx="')
    xml_text = xml_text.replace("xmlns:", "xmlnsx:")
    # Remove all namespace prefixes
    import re
    xml_text = re.sub(r'<(/?)n\d+:', r'<\1', xml_text)
    xml_text = re.sub(r' n\d+:', ' ', xml_text)

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("XML parse error: %s", exc)
        return []

    for info in root.iter("infoTable"):
        try:
            name_el = info.find("nameOfIssuer")
            cusip_el = info.find("cusip")
            value_el = info.find("value")
            shares_el = info.find("sshPrnamt") or info.find("shrsOrPrnAmt")
            put_call_el = info.find("putCall")
            type_el = info.find("sshPrnamtType")

            name = name_el.text.strip() if name_el is not None and name_el.text else ""
            cusip = cusip_el.text.strip() if cusip_el is not None and cusip_el.text else ""
            value_k = int(value_el.text.strip()) if value_el is not None and value_el.text else 0
            shares = int(shares_el.text.strip()) if shares_el is not None and shares_el.text else 0
            put_call = put_call_el.text.strip() if put_call_el is not None and put_call_el.text else ""
            share_type = type_el.text.strip() if type_el is not None and type_el.text else "SH"

            holdings.append({
                "issuer": name,
                "cusip": cusip,
                "value_thousands": value_k,
                "value_usd": value_k * 1000,
                "shares": shares,
                "share_type": share_type,
                "put_call": put_call,
            })
        except Exception:
            continue

    # Sort by value descending
    holdings.sort(key=lambda x: x["value_usd"], reverse=True)
    return holdings


def format_holdings_summary(filing: dict) -> str:
    """Return a human-readable summary of a 13F filing."""
    lines = [
        f"  {filing['investor']} (CIK: {filing['cik']})",
        f"  Filed: {filing['filing_date']}",
        f"  Accession: {filing['accession_number']}",
        "",
        "  Top Holdings:",
    ]
    total = sum(h["value_usd"] for h in filing["holdings"])
    for i, h in enumerate(filing["holdings"][:15], 1):
        pct = (h["value_usd"] / total * 100) if total else 0
        value_str = _fmt_usd(h["value_usd"])
        put_call = f" ({h['put_call']})" if h["put_call"] else ""
        lines.append(f"    {i:2d}. {h['issuer']:<30s} {value_str:>12s} ({pct:.1f}%){put_call}")
    return "\n".join(lines)


def _fmt_usd(v: int) -> str:
    if v >= 1_000_000_000:
        return f"${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v}"
