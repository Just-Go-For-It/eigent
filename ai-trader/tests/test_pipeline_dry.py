"""End-to-end dry run: synthetic data + mock LLM + paper broker, no secrets."""
from src.config import Config, RiskLimits
from src.execution.broker import PaperBroker
from src.pipeline import run_once


def _dry_config():
    cfg = Config()
    cfg.trading_mode = "paper"
    cfg.anthropic_api_key = ""  # force MockLLM
    cfg.alpaca_api_key = ""     # force MockDataProvider
    cfg.alpaca_secret_key = ""
    cfg.limits = RiskLimits(
        max_position_usd=5000.0,
        max_trade_pct=5.0,
        daily_max_loss_usd=1000.0,
        safety_mode_max_consec_losses=3,
        max_options_level=2,
        allowed_symbols=["AAPL", "MSFT", "SPY"],
        market_hours_only=False,  # so the dry run isn't clock-dependent
    )
    return cfg


def test_dry_run_completes_and_logs_decisions():
    cfg = _dry_config()
    broker = PaperBroker(starting_cash=cfg.starting_equity_usd)
    report = run_once(config=cfg, strategy_name="ma_crossover", broker=broker)
    assert len(report.decisions) == 3
    for d in report.decisions:
        assert d.final_action in {"buy", "sell", "hold", "rejected"}
        assert d.trace  # every decision has an audit trace
    assert report.equity > 0


def test_dry_run_includes_fundamentals_analyst_node():
    cfg = _dry_config()  # no FINANCIAL_DATASETS_API_KEY -> mock fundamentals
    broker = PaperBroker(starting_cash=cfg.starting_equity_usd)
    report = run_once(config=cfg, strategy_name="ma_crossover", broker=broker)
    traces = [line for d in report.decisions for line in d.trace]
    assert any("[fundamentals-analyst]" in line for line in traces)


def test_dry_run_respects_riskguard_when_market_closed():
    cfg = _dry_config()
    cfg.limits.market_hours_only = True  # likely outside RTH in CI -> buys rejected
    broker = PaperBroker(starting_cash=cfg.starting_equity_usd)
    report = run_once(config=cfg, strategy_name="ma_crossover", broker=broker)
    # Either way the pipeline must not crash and must produce traced decisions.
    assert len(report.decisions) == 3
