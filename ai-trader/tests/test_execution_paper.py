from src.execution.broker import PaperBroker
from src.risk.guard import OrderRequest


def test_paper_buy_decrements_cash_and_adds_position():
    b = PaperBroker(starting_cash=100_000)
    fill = b.submit(OrderRequest("AAPL", "buy", qty=10, price=150.0))
    assert fill.notional == 1500.0
    assert b.cash == 100_000 - 1500.0
    assert b.positions["AAPL"].qty == 10


def test_paper_sell_increments_cash():
    b = PaperBroker(starting_cash=100_000)
    b.submit(OrderRequest("AAPL", "buy", qty=10, price=150.0))
    b.submit(OrderRequest("AAPL", "sell", qty=5, price=160.0))
    assert b.positions["AAPL"].qty == 5
    assert b.cash == 100_000 - 1500.0 + 800.0


def test_option_notional_uses_100_multiplier():
    b = PaperBroker(starting_cash=100_000)
    fill = b.submit(OrderRequest("AAPL", "buy", qty=1, price=2.5, asset_class="option"))
    assert fill.notional == 250.0  # 1 contract * $2.50 * 100
