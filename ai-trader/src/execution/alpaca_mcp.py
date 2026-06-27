"""Alpaca order execution via the official MCP server (alpacahq/alpaca-mcp-server).

This is the requested "MCP order path". The server runs as a local stdio subprocess
(`uvx alpaca-mcp-server`); we connect with langchain-mcp-adapters, load its tools, and call
the relevant tool by name for each order. MCP tool results are LLM-oriented text, so fills
are parsed best-effort and fall back to the order's estimate — for strict deterministic fills
prefer the alpaca-py SDK backend (alpaca_sdk.py). Paper-first and gated by RiskGuard upstream.
"""
from __future__ import annotations

import json
import re

from ..risk.guard import OrderRequest
from .async_bridge import AsyncRunner
from .broker import Broker, Fill


class AlpacaMCPBroker(Broker):
    def __init__(self, config, runner: AsyncRunner | None = None):
        self.config = config
        self._runner = runner or AsyncRunner()
        self._tools: dict | None = None
        # Defense in depth: never touch live unless explicitly un-papered AND in live mode.
        if not config.alpaca_paper_trade and not config.is_live:
            raise RuntimeError("Refusing live MCP broker: set TRADING_MODE=live to go live.")

    # --- connection -----------------------------------------------------------
    def _server_spec(self) -> dict:
        return {
            "alpaca": {
                "transport": "stdio",
                "command": "uvx",
                "args": ["alpaca-mcp-server"],
                "env": {
                    "ALPACA_API_KEY": self.config.alpaca_api_key,
                    "ALPACA_SECRET_KEY": self.config.alpaca_secret_key,
                    "ALPACA_PAPER_TRADE": "true" if self.config.alpaca_paper_trade else "false",
                },
            }
        }

    def _load_tools(self) -> dict:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient(self._server_spec())
        tools = self._runner.run(client.get_tools())
        return {t.name: t for t in tools}

    def _ensure(self) -> None:
        if self._tools is None:
            self._tools = self._load_tools()

    def _call(self, name: str, args: dict):
        self._ensure()
        if name not in self._tools:
            raise RuntimeError(f"Alpaca MCP server does not expose tool '{name}'. Available: "
                               f"{sorted(self._tools)}")
        return self._runner.run(self._tools[name].ainvoke(args))

    # --- order mapping --------------------------------------------------------
    @staticmethod
    def _stock_args(order: OrderRequest) -> dict:
        return {
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.qty,
            "order_type": "market",
            "time_in_force": "day",
        }

    @staticmethod
    def _option_args(order: OrderRequest) -> dict:
        # order.symbol is the OCC option symbol for single-leg option orders.
        return {
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.qty,
            "order_type": "market",
            "time_in_force": "day",
        }

    def submit(self, order: OrderRequest) -> Fill:
        if order.is_close:
            raw = self._call("close_position", {"symbol": order.symbol})
        elif order.asset_class == "option":
            raw = self._call("place_option_order", self._option_args(order))
        else:
            raw = self._call("place_stock_order", self._stock_args(order))
        return self._parse_fill(order, raw)

    # --- response parsing -----------------------------------------------------
    @staticmethod
    def _parse_fill(order: OrderRequest, raw) -> Fill:
        qty, price = order.qty, order.price  # estimates as fallback
        data = AlpacaMCPBroker._as_dict(raw)
        if data:
            qty = float(data.get("filled_qty") or data.get("qty") or qty)
            price = float(data.get("filled_avg_price") or data.get("price") or price)
        else:
            m = re.search(r"filled_avg_price[\"':\s]+([0-9.]+)", str(raw))
            if m:
                price = float(m.group(1))
        mult = 100.0 if order.asset_class == "option" else 1.0
        return Fill(order.symbol, order.side, qty, price, abs(qty) * price * mult)

    @staticmethod
    def _as_dict(raw):
        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(raw if isinstance(raw, str) else str(raw))
            return parsed if isinstance(parsed, dict) else None
        except (ValueError, TypeError):
            return None

    def equity(self) -> float:
        raw = self._call("get_account_info", {})
        data = self._as_dict(raw)
        if data:
            for key in ("equity", "portfolio_value", "cash"):
                if key in data:
                    try:
                        return float(data[key])
                    except (ValueError, TypeError):
                        pass
        m = re.search(r"equity[\"':\s]+([0-9.]+)", str(raw))
        return float(m.group(1)) if m else self.config.starting_equity_usd
