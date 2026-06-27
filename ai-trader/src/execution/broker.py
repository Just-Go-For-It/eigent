"""Execution adapters.

``PaperBroker`` is a self-contained in-memory simulator used for dry runs and tests.
``AlpacaMCPBroker`` connects to Alpaca's official MCP server (alpacahq/alpaca-mcp-server)
via langchain-mcp-adapters; it is lazy-imported so the package runs without those deps.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..risk.guard import OrderRequest


@dataclass
class Fill:
    symbol: str
    side: str
    qty: float
    price: float
    notional: float


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0


class Broker(ABC):
    @abstractmethod
    def submit(self, order: OrderRequest) -> Fill:
        ...

    @abstractmethod
    def equity(self) -> float:
        ...


class PaperBroker(Broker):
    """Deterministic in-memory paper account. No network. Fills at the order's est. price."""

    def __init__(self, starting_cash: float = 100_000.0):
        self.cash = starting_cash
        self.positions: dict[str, Position] = {}
        self.fills: list[Fill] = []

    def submit(self, order: OrderRequest) -> Fill:
        mult = 100.0 if order.asset_class == "option" else 1.0
        notional = abs(order.qty) * order.price * mult
        signed_qty = order.qty if order.side == "buy" else -order.qty

        pos = self.positions.setdefault(order.symbol, Position(order.symbol))
        if order.side == "buy":
            new_qty = pos.qty + order.qty
            if new_qty != 0:
                pos.avg_price = (pos.avg_price * pos.qty + order.price * order.qty) / new_qty
            pos.qty = new_qty
            self.cash -= notional
        else:
            pos.qty -= order.qty
            self.cash += notional

        fill = Fill(order.symbol, order.side, order.qty, order.price, notional)
        self.fills.append(fill)
        return fill

    def mark_to_market(self, prices: dict[str, float]) -> float:
        mv = sum(p.qty * prices.get(s, p.avg_price) for s, p in self.positions.items())
        return self.cash + mv

    def equity(self) -> float:
        # Without live marks, approximate with cash + positions at avg price.
        mv = sum(p.qty * p.avg_price for p in self.positions.values())
        return self.cash + mv


def get_broker(config=None) -> Broker:
    """Select the execution backend from config.execution_backend.

    * ``paper`` (default)  -> in-memory PaperBroker (no network)
    * ``alpaca_sdk``       -> direct alpaca-py client (robust deterministic fills)
    * ``alpaca_mcp``       -> official Alpaca MCP server (the LLM-native order path)

    Any missing optional dependency or credential falls back to the paper simulator, so the
    app never hard-crashes on a misconfigured broker.
    """
    start = config.starting_equity_usd if config else 100_000.0
    backend = getattr(config, "execution_backend", "paper") if config else "paper"

    if backend == "alpaca_sdk":
        try:
            from .alpaca_sdk import AlpacaBroker

            return AlpacaBroker(config)
        except Exception as e:  # pragma: no cover - depends on env
            print(f"[broker] alpaca_sdk unavailable ({e}); falling back to paper.")
    elif backend == "alpaca_mcp":
        try:
            import langchain_mcp_adapters  # noqa: F401  ensure dep before connecting

            from .alpaca_mcp import AlpacaMCPBroker

            return AlpacaMCPBroker(config)
        except Exception as e:  # pragma: no cover - depends on env
            print(f"[broker] alpaca_mcp unavailable ({e}); falling back to paper.")

    return PaperBroker(starting_cash=start)
