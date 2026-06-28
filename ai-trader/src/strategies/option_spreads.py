"""Builders for common multi-leg (mleg) option orders.

These produce a single ``OrderRequest`` carrying ``legs`` (so it flows through RiskGuard and
the brokers' multi-leg path unchanged). ``price`` is the NET premium per spread (debit > 0,
credit < 0); ``qty`` is the number of spreads. Spreads typically require options level >= 3,
so set ``MAX_OPTIONS_LEVEL`` accordingly or RiskGuard will (correctly) reject them.
"""
from __future__ import annotations

from ..risk.guard import OptionLeg, OrderRequest


def vertical_spread(
    long_symbol: str,
    short_symbol: str,
    qty: int,
    net_price: float,
    options_level: int = 3,
) -> OrderRequest:
    """Generic two-leg vertical: buy ``long_symbol``, sell ``short_symbol``."""
    return OrderRequest(
        symbol="",  # multi-leg orders are defined by their legs, not a single symbol
        side="buy",
        qty=qty,
        price=abs(net_price),
        asset_class="option",
        options_level=options_level,
        legs=[OptionLeg(long_symbol, "buy", 1), OptionLeg(short_symbol, "sell", 1)],
    )


def bull_call_spread(long_call: str, short_call: str, qty: int, net_debit: float) -> OrderRequest:
    """Buy lower-strike call, sell higher-strike call (debit)."""
    return vertical_spread(long_call, short_call, qty, abs(net_debit))


def bear_put_spread(long_put: str, short_put: str, qty: int, net_debit: float) -> OrderRequest:
    """Buy higher-strike put, sell lower-strike put (debit)."""
    return vertical_spread(long_put, short_put, qty, abs(net_debit))
