from src.backtest.engine import run_backtest
from src.data.providers import MockDataProvider
from src.strategies import MACrossoverStrategy


def test_backtest_returns_metrics():
    df = MockDataProvider().get_history("AAPL", days=500)
    pos = MACrossoverStrategy().generate_signals(df)
    res = run_backtest(df, pos)
    d = res.as_dict()
    for key in ("total_return", "cagr", "sharpe", "max_drawdown", "win_rate", "n_trades"):
        assert key in d
    assert -1.0 <= d["max_drawdown"] <= 0.0
    assert d["n_trades"] >= 0
    assert len(res.equity_curve) == len(df)


def test_no_lookahead_flat_positions_give_zero_return():
    df = MockDataProvider().get_history("AAPL", days=300)
    pos = MACrossoverStrategy().generate_signals(df) * 0  # force all-flat
    res = run_backtest(df, pos)
    assert abs(res.total_return) < 1e-9


def test_costs_reduce_returns():
    df = MockDataProvider().get_history("SPY", days=500)
    pos = MACrossoverStrategy().generate_signals(df)
    cheap = run_backtest(df, pos, cost_bps=0.0).total_return
    pricey = run_backtest(df, pos, cost_bps=50.0).total_return
    assert pricey <= cheap
