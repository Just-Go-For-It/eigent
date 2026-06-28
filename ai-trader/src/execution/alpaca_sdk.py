"""Alpaca order execution via the alpaca-py SDK (direct REST).

Recommended default for *live/paper* deterministic execution: responses are structured
objects, so fills and equity parse reliably (unlike LLM-oriented MCP text). Paper-first:
``TradingClient(paper=...)`` is driven by ``ALPACA_PAPER_TRADE``. RiskGuard still gates
every order upstream.
"""
from __future__ import annotations

from ..risk.guard import OrderRequest
from .broker import Broker, Fill


class AlpacaBroker(Broker):
    def __init__(self, config):
        self.config = config
        if not config.alpaca_paper_trade and not config.is_live:
            raise RuntimeError("Refusing live SDK broker: set TRADING_MODE=live to go live.")
        from alpaca.trading.client import TradingClient

        self._client = TradingClient(
            config.alpaca_api_key, config.alpaca_secret_key, paper=config.alpaca_paper_trade
        )

    def submit(self, order: OrderRequest) -> Fill:
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        if order.is_close:
            self._client.close_position(order.symbol)
            return Fill(order.symbol, order.side, order.qty, order.price,
                        order.qty * order.price)

        if order.is_multileg:  # pragma: no cover - requires alpaca-py + network
            from alpaca.trading.enums import OrderClass
            from alpaca.trading.requests import OptionLegRequest

            legs = [
                OptionLegRequest(
                    symbol=leg.symbol,
                    side=OrderSide.BUY if leg.side == "buy" else OrderSide.SELL,
                    ratio_qty=leg.ratio_qty,
                )
                for leg in order.legs
            ]
            req = MarketOrderRequest(
                qty=order.qty, order_class=OrderClass.MLEG,
                time_in_force=TimeInForce.DAY, legs=legs,
            )
            resp = self._client.submit_order(req)
            qty = float(getattr(resp, "filled_qty", None) or order.qty)
            price = float(getattr(resp, "filled_avg_price", None) or order.price)
            return Fill(order.symbol or "mleg", order.side, qty, price, abs(qty) * price * 100.0)

        side = OrderSide.BUY if order.side == "buy" else OrderSide.SELL
        req = MarketOrderRequest(
            symbol=order.symbol, qty=order.qty, side=side, time_in_force=TimeInForce.DAY
        )
        resp = self._client.submit_order(req)
        qty = float(getattr(resp, "filled_qty", None) or order.qty)
        price = float(getattr(resp, "filled_avg_price", None) or order.price)
        mult = 100.0 if order.asset_class == "option" else 1.0
        return Fill(order.symbol, order.side, qty, price, abs(qty) * price * mult)

    def equity(self) -> float:
        acct = self._client.get_account()
        return float(getattr(acct, "equity", None) or getattr(acct, "cash", 0.0))
