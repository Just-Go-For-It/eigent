import math

from src.backtest.bs import bs_price
from src.backtest.options import backtest_vertical_spread
from src.data.providers import MockDataProvider
from src.strategies import OptionsIncomeStrategy


# ---- Black-Scholes sanity ----
def test_bs_call_intrinsic_at_expiry():
    assert bs_price(110, 100, 0, 0.04, 0.2, "call") == 10
    assert bs_price(90, 100, 0, 0.04, 0.2, "call") == 0
    assert bs_price(90, 100, 0, 0.04, 0.2, "put") == 10


def test_bs_call_increases_with_spot():
    low = bs_price(95, 100, 0.5, 0.04, 0.25, "call")
    high = bs_price(105, 100, 0.5, 0.04, 0.25, "call")
    assert high > low > 0


def test_put_call_parity():
    S, K, T, r, sig = 100, 100, 0.5, 0.04, 0.25
    call = bs_price(S, K, T, r, sig, "call")
    put = bs_price(S, K, T, r, sig, "put")
    # C - P == S - K*e^{-rT}
    assert math.isclose(call - put, S - K * math.exp(-r * T), rel_tol=1e-6)


def test_debit_vertical_costs_premium():
    # long lower strike call worth more than short higher strike -> positive debit
    long_leg = bs_price(100, 100, 30 / 252, 0.04, 0.25, "call")
    short_leg = bs_price(100, 105, 30 / 252, 0.04, 0.25, "call")
    assert long_leg - short_leg > 0


# ---- Spread backtest harness ----
def test_spread_backtest_produces_trades_and_metrics():
    df = MockDataProvider().get_history("AAPL", days=500)
    signals = OptionsIncomeStrategy().generate_signals(df)
    res = backtest_vertical_spread(df, signals, dte=30, width_pct=0.05, kind="call")
    m = res.as_dict()
    for key in ("total_pnl", "n_trades", "win_rate", "avg_pnl", "max_drawdown"):
        assert key in m
    assert res.n_trades > 0
    assert 0.0 <= res.win_rate <= 1.0
    assert res.max_drawdown <= 0.0
    assert len(res.trades) == res.n_trades


def test_spread_backtest_no_signals_no_trades():
    df = MockDataProvider().get_history("SPY", days=300)
    flat = OptionsIncomeStrategy().generate_signals(df) * 0
    res = backtest_vertical_spread(df, flat)
    assert res.n_trades == 0
    assert res.total_pnl == 0.0
