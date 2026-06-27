"""Unit tests for the Alpaca MCP order path — no network, MCP tools are faked."""
import pytest

from src.config import Config
from src.execution.alpaca_mcp import AlpacaMCPBroker
from src.risk.guard import OrderRequest


class FakeTool:
    def __init__(self, name, response):
        self.name = name
        self.response = response
        self.calls = []

    async def ainvoke(self, args):
        self.calls.append(args)
        return self.response


def make_broker(responses):
    cfg = Config()
    cfg.trading_mode = "paper"
    cfg.alpaca_paper_trade = True
    cfg.alpaca_api_key = "k"
    cfg.alpaca_secret_key = "s"
    broker = AlpacaMCPBroker(cfg)
    tools = {name: FakeTool(name, resp) for name, resp in responses.items()}
    broker._tools = tools  # skip real MCP connection
    return broker, tools


def test_stock_buy_routes_to_place_stock_order_and_parses_fill():
    broker, tools = make_broker(
        {"place_stock_order": '{"filled_qty": "10", "filled_avg_price": "151.0"}'}
    )
    fill = broker.submit(OrderRequest("AAPL", "buy", qty=10, price=150.0))
    assert tools["place_stock_order"].calls, "place_stock_order was not called"
    args = tools["place_stock_order"].calls[0]
    assert args["symbol"] == "AAPL" and args["side"] == "buy" and args["quantity"] == 10
    assert fill.price == 151.0
    assert fill.notional == 1510.0
    broker._runner.close()


def test_option_order_routes_to_place_option_order_with_100x_multiplier():
    broker, tools = make_broker(
        {"place_option_order": '{"filled_qty": "1", "filled_avg_price": "2.5"}'}
    )
    fill = broker.submit(
        OrderRequest("AAPL240920C00150000", "buy", qty=1, price=2.0, asset_class="option")
    )
    assert tools["place_option_order"].calls
    assert fill.notional == 250.0  # 1 * 2.5 * 100
    broker._runner.close()


def test_close_routes_to_close_position():
    broker, tools = make_broker({"close_position": "{}"})
    broker.submit(OrderRequest("AAPL", "sell", qty=5, price=150.0, is_close=True))
    assert tools["close_position"].calls[0] == {"symbol": "AAPL"}
    broker._runner.close()


def test_equity_parses_account_info():
    broker, _ = make_broker({"get_account_info": '{"equity": "98765.0"}'})
    assert broker.equity() == 98765.0
    broker._runner.close()


def test_refuses_live_when_not_explicitly_live():
    cfg = Config()
    cfg.trading_mode = "paper"
    cfg.alpaca_paper_trade = False  # un-papered but still paper mode -> must refuse
    with pytest.raises(RuntimeError):
        AlpacaMCPBroker(cfg)
