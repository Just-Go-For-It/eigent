"""Critical safety tests. If these fail, the system must not trade."""
from datetime import datetime, timezone

import pytest

from src.config import Config, RiskLimits
from src.risk.guard import OrderRequest, RiskGuard, SafetyMode

MARKET_OPEN = lambda: datetime(2024, 1, 8, 14, 0, tzinfo=timezone.utc)   # Monday 14:00 UTC
AFTER_HOURS = lambda: datetime(2024, 1, 8, 22, 0, tzinfo=timezone.utc)   # Monday 22:00 UTC
WEEKEND = lambda: datetime(2024, 1, 6, 14, 0, tzinfo=timezone.utc)       # Saturday


def make_guard(now_fn=MARKET_OPEN, **limit_overrides):
    cfg = Config()
    cfg.trading_mode = "paper"
    cfg.limits = RiskLimits(
        max_position_usd=2000.0,
        max_trade_pct=2.0,
        daily_max_loss_usd=200.0,
        safety_mode_max_consec_losses=3,
        max_options_level=2,
        allowed_symbols=["AAPL", "MSFT", "SPY"],
        market_hours_only=True,
    )
    for k, v in limit_overrides.items():
        setattr(cfg.limits, k, v)
    return RiskGuard(cfg, SafetyMode(cfg.limits.safety_mode_max_consec_losses), now_fn=now_fn), cfg


def test_approves_valid_small_order():
    guard, _ = make_guard()
    order = OrderRequest("AAPL", "buy", qty=10, price=150.0)  # $1500 notional
    decision = guard.check(order, equity=100_000)
    assert decision.approved, decision.reasons


def test_rejects_symbol_not_in_allowlist():
    guard, _ = make_guard()
    order = OrderRequest("TSLA", "buy", qty=1, price=100.0)
    assert not guard.check(order, equity=100_000).approved


def test_rejects_notional_over_max_position():
    guard, _ = make_guard()
    order = OrderRequest("AAPL", "buy", qty=100, price=150.0)  # $15,000 > $2,000
    decision = guard.check(order, equity=100_000)
    assert not decision.approved
    assert any("notional" in r for r in decision.reasons)


def test_rejects_over_max_trade_pct():
    guard, _ = make_guard()
    order = OrderRequest("AAPL", "buy", qty=10, price=150.0)  # $1500 = 15% of $10k equity
    decision = guard.check(order, equity=10_000)
    assert not decision.approved
    assert any("% of equity" in r for r in decision.reasons)


def test_rejects_options_level_over_cap():
    guard, _ = make_guard()
    order = OrderRequest("AAPL", "buy", qty=1, price=2.0, asset_class="option", options_level=3)
    decision = guard.check(order, equity=100_000)
    assert not decision.approved
    assert any("options level" in r for r in decision.reasons)


def test_rejects_outside_market_hours():
    guard, _ = make_guard(now_fn=AFTER_HOURS)
    order = OrderRequest("AAPL", "buy", qty=1, price=150.0)
    assert not guard.check(order, equity=100_000).approved


def test_rejects_on_weekend():
    guard, _ = make_guard(now_fn=WEEKEND)
    order = OrderRequest("AAPL", "buy", qty=1, price=150.0)
    assert not guard.check(order, equity=100_000).approved


def test_daily_loss_killswitch_blocks_new_allows_close():
    guard, _ = make_guard()
    guard.record_fill(-250.0)  # exceeds $200 daily loss limit
    new_order = OrderRequest("AAPL", "buy", qty=1, price=150.0)
    close_order = OrderRequest("AAPL", "sell", qty=1, price=150.0, is_close=True)
    assert not guard.check(new_order, equity=100_000).approved
    assert guard.check(close_order, equity=100_000).approved  # de-risking allowed


def test_safety_mode_trips_after_consecutive_losses():
    guard, _ = make_guard()
    for _ in range(3):
        guard.record_fill(-10.0)
    assert guard.safety.tripped
    new_order = OrderRequest("AAPL", "buy", qty=1, price=150.0)
    decision = guard.check(new_order, equity=100_000)
    assert not decision.approved
    assert any("SAFETY MODE" in r for r in decision.reasons)


def test_safety_mode_resets_on_win():
    guard, _ = make_guard()
    guard.record_fill(-10.0)
    guard.record_fill(-10.0)
    guard.record_fill(50.0)  # a win resets the streak
    assert guard.safety.consecutive_losses == 0
    assert not guard.safety.tripped


def test_live_order_requires_human_approval():
    guard, cfg = make_guard()
    cfg.trading_mode = "live"
    cfg.human_approval = True
    order = OrderRequest("AAPL", "buy", qty=1, price=150.0)
    decision = guard.check(order, equity=100_000)
    assert not decision.approved
    assert any("human approval" in r for r in decision.reasons)
    # Once approved out-of-band, it can pass.
    order._approved = True
    assert guard.check(order, equity=100_000).approved
