from src.config import Config
from src.data.fundamentals import (
    FinancialDatasetsProvider,
    MockFundamentalsProvider,
    get_fundamentals,
    score_metrics,
)


def test_mock_is_neutral_and_newsless():
    m = MockFundamentalsProvider()
    adj, _ = score_metrics(m.get_metrics("AAPL"))
    assert adj == 0.0
    assert m.get_news("AAPL") == []


def test_score_positive_for_growth_and_reasonable_pe():
    adj, txt = score_metrics(
        {"revenue_growth": 0.2, "earnings_growth": 0.15, "price_to_earnings_ratio": 18}
    )
    assert adj > 0
    assert "rev_growth" in txt


def test_score_negative_for_decline_and_overvalued():
    adj, _ = score_metrics(
        {"revenue_growth": -0.1, "earnings_growth": -0.2, "price_to_earnings_ratio": 80}
    )
    assert adj < 0


def test_score_is_bounded():
    adj, _ = score_metrics(
        {"revenue_growth": 5, "earnings_growth": 5, "price_to_earnings_ratio": 5}
    )
    assert -1.0 <= adj <= 1.0


def test_financialdatasets_parsing_mocked(monkeypatch):
    p = FinancialDatasetsProvider("key")

    def fake_get(path, params):
        if path == "/financial-metrics/snapshot":
            return {"snapshot": {"revenue_growth": 0.1, "earnings_growth": 0.1,
                                 "price_to_earnings_ratio": 20}}
        if path == "/news":
            return {"news": [{"title": "Beats earnings"}, {"title": "New product"}]}
        return {}

    monkeypatch.setattr(p, "_get", fake_get)
    assert p.get_metrics("AAPL")["revenue_growth"] == 0.1
    assert p.get_news("AAPL")[0]["title"] == "Beats earnings"


def test_get_fundamentals_picks_mock_without_key():
    cfg = Config()
    cfg.financial_datasets_api_key = ""
    assert isinstance(get_fundamentals(cfg), MockFundamentalsProvider)


def test_get_fundamentals_picks_real_with_key():
    cfg = Config()
    cfg.financial_datasets_api_key = "abc"
    assert isinstance(get_fundamentals(cfg), FinancialDatasetsProvider)
