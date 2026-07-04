"""Minimal Black-Scholes option pricing (stdlib only, no QuantLib dependency).

Used by the option-spread backtest to price legs along a simulated underlying path. This is a
teaching-grade European pricer (no dividends, flat rates, constant vol) — good enough to score
the *shape* of a spread strategy, not to mark a live book. For production greeks/American
exercise, swap in QuantLib (already an optional extra).
"""
from __future__ import annotations

import math


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(S: float, K: float, T: float, r: float, sigma: float, kind: str = "call") -> float:
    """Black-Scholes price of a European call/put.

    S spot, K strike, T years to expiry, r risk-free, sigma annualized vol.
    At/After expiry (T<=0) returns intrinsic value.
    """
    call = kind == "call"
    if T <= 0 or sigma <= 0:
        return max(0.0, S - K) if call else max(0.0, K - S)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if call:
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)
