from src.data.providers import MockDataProvider
from src.strategies import MACrossoverStrategy, OptionsIncomeStrategy


def test_ma_crossover_produces_binary_positions():
    df = MockDataProvider().get_history("AAPL", days=400)
    pos = MACrossoverStrategy(fast=20, slow=50).generate_signals(df)
    assert set(pos.unique()).issubset({0, 1})
    assert (pos.iloc[:50] == 0).all()  # warm-up flat (no look-ahead before slow window)


def test_ma_crossover_validates_windows():
    import pytest

    with pytest.raises(ValueError):
        MACrossoverStrategy(fast=50, slow=20)


def test_latest_signal_actions_valid():
    df = MockDataProvider().get_history("MSFT", days=300)
    sig = MACrossoverStrategy().latest_signal("MSFT", df)
    assert sig.action in {"buy", "sell", "hold"}
    assert 0.0 <= sig.strength <= 1.0


def test_options_income_signal_runs():
    df = MockDataProvider().get_history("SPY", days=300)
    pos = OptionsIncomeStrategy().generate_signals(df)
    assert set(pos.unique()).issubset({0, 1})
    sig = OptionsIncomeStrategy().latest_signal("SPY", df)
    assert sig.action in {"buy", "hold"}
