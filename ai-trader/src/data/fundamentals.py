"""Fundamentals & news analyst data source (Financial Datasets API).

Provides company metrics + recent news headlines for the fundamentals analyst node. Uses the
stdlib (urllib) so it adds no dependency and is easy to mock. A ``MockFundamentalsProvider``
keeps dry runs / CI fully offline and deterministic. All network failures degrade gracefully
to neutral data — fundamentals only *nudge* conviction; they never gate risk.

API: https://api.financialdatasets.ai  (auth header: X-API-KEY)
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod

BASE_URL = "https://api.financialdatasets.ai"


class FundamentalsProvider(ABC):
    @abstractmethod
    def get_metrics(self, ticker: str) -> dict:
        ...

    @abstractmethod
    def get_news(self, ticker: str, limit: int = 5) -> list[dict]:
        ...


class MockFundamentalsProvider(FundamentalsProvider):
    """Neutral, deterministic data so the pipeline runs with no API key."""

    def get_metrics(self, ticker: str) -> dict:
        return {
            "ticker": ticker,
            "revenue_growth": 0.0,
            "earnings_growth": 0.0,
            "price_to_earnings_ratio": 20.0,
            "_mock": True,
        }

    def get_news(self, ticker: str, limit: int = 5) -> list[dict]:
        return []


class FinancialDatasetsProvider(FundamentalsProvider):
    def __init__(self, api_key: str, timeout: float = 8.0):
        self.api_key = api_key
        self.timeout = timeout

    def _get(self, path: str, params: dict) -> dict:
        url = f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"X-API-KEY": self.api_key})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, ValueError, TimeoutError) as e:  # pragma: no cover
            return {"_error": str(e)}

    def get_metrics(self, ticker: str) -> dict:
        # Snapshot first; fall back to latest historical TTM metric.
        data = self._get("/financial-metrics/snapshot", {"ticker": ticker})
        snap = data.get("snapshot") if isinstance(data, dict) else None
        if snap:
            return snap
        hist = self._get("/financial-metrics", {"ticker": ticker, "period": "ttm", "limit": 1})
        metrics = hist.get("financial_metrics") if isinstance(hist, dict) else None
        if metrics:
            return metrics[0]
        return MockFundamentalsProvider().get_metrics(ticker)

    def get_news(self, ticker: str, limit: int = 5) -> list[dict]:
        data = self._get("/news", {"ticker": ticker, "limit": limit})
        return data.get("news", []) if isinstance(data, dict) else []


def score_metrics(metrics: dict) -> tuple[float, str]:
    """Map fundamentals to a bounded conviction adjustment in [-1, 1] + a one-line rationale."""
    if not metrics or metrics.get("_mock"):
        return 0.0, "fundamentals: neutral (no data)"

    score = 0.0
    notes: list[str] = []

    rev = metrics.get("revenue_growth")
    if isinstance(rev, (int, float)):
        score += 0.4 if rev > 0 else -0.4
        notes.append(f"rev_growth={rev:+.1%}" if abs(rev) < 100 else f"rev_growth={rev:+.2f}")

    eps = metrics.get("earnings_growth")
    if isinstance(eps, (int, float)):
        score += 0.4 if eps > 0 else -0.4
        notes.append(f"eps_growth={eps:+.1%}" if abs(eps) < 100 else f"eps_growth={eps:+.2f}")

    pe = metrics.get("price_to_earnings_ratio")
    if isinstance(pe, (int, float)) and pe > 0:
        if pe > 50:
            score -= 0.3
        elif pe < 25:
            score += 0.2
        notes.append(f"P/E={pe:.1f}")

    score = max(-1.0, min(1.0, score))
    return score, "fundamentals: " + ", ".join(notes) if notes else "fundamentals: neutral"


def get_fundamentals(config=None) -> FundamentalsProvider:
    if config is not None and config.financial_datasets_api_key:
        return FinancialDatasetsProvider(config.financial_datasets_api_key)
    return MockFundamentalsProvider()
