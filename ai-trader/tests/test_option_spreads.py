from datetime import datetime, timezone

from src.config import Config, RiskLimits
from src.risk.guard import RiskGuard, SafetyMode
from src.strategies.option_spreads import bull_call_spread, vertical_spread

MARKET_OPEN = lambda: datetime(2024, 1, 8, 14, 0, tzinfo=timezone.utc)


def test_vertical_spread_builds_two_legs():
    order = vertical_spread("AAPL240920C00150000", "AAPL240920C00160000", qty=2, net_price=3.0)
    assert order.is_multileg
    assert len(order.legs) == 2
    assert order.legs[0].side == "buy" and order.legs[1].side == "sell"
    assert order.asset_class == "option"
    # NET premium per spread * 100 * qty
    assert order.notional == 600.0  # 2 * 3.0 * 100


def test_bull_call_spread_is_debit_positive():
    order = bull_call_spread("AAPL_C150", "AAPL_C160", qty=1, net_debit=-2.5)
    assert order.price == 2.5  # normalized to positive debit


def test_spread_rejected_when_options_level_too_low():
    cfg = Config()
    cfg.limits = RiskLimits(
        max_position_usd=10000, max_trade_pct=50, daily_max_loss_usd=1000,
        safety_mode_max_consec_losses=3, max_options_level=2,  # spread needs level 3
        allowed_symbols=[""], market_hours_only=False,
    )
    guard = RiskGuard(cfg, SafetyMode(3), now_fn=MARKET_OPEN)
    order = vertical_spread("AAPL_C150", "AAPL_C160", qty=1, net_price=2.0)  # options_level=3
    decision = guard.check(order, equity=100_000)
    assert not decision.approved
    assert any("options level" in r for r in decision.reasons)
