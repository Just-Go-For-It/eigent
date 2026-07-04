"""Option-spread backtest harness.

Scores a vertical-spread strategy on an underlying price path. Because tick-level historical
option chains are expensive, we *model* each spread's entry debit and exit value with
Black-Scholes (src/backtest/bs.py), using realized vol at entry. On each entry signal (while
flat) we open a vertical (long ATM, short OTM by ``width_pct``), hold for ``hold_days`` trading
bars (or to expiry), and book P&L. This scores strategy shape/edge, not live fills — validate
against real chains before trading.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .bs import bs_price


@dataclass
class SpreadBacktestResult:
    total_pnl: float
    n_trades: int
    win_rate: float
    avg_pnl: float
    max_drawdown: float
    trades: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "total_pnl": round(self.total_pnl, 2),
            "n_trades": self.n_trades,
            "win_rate": round(self.win_rate, 4),
            "avg_pnl": round(self.avg_pnl, 2),
            "max_drawdown": round(self.max_drawdown, 2),
        }


def _annualized_vol(log_rets: np.ndarray, i: int, window: int = 20, floor: float = 0.05) -> float:
    w = log_rets[max(0, i - window):i]
    if len(w) < 2:
        return 0.25
    return max(floor, float(np.std(w) * np.sqrt(252)))


def backtest_vertical_spread(
    df: pd.DataFrame,
    signals: pd.Series,
    dte: int = 30,
    width_pct: float = 0.05,
    r: float = 0.04,
    hold_days: int | None = None,
    kind: str = "call",
    contracts: int = 1,
) -> SpreadBacktestResult:
    """Enter a debit vertical on each signal (while flat); exit after hold_days or at expiry."""
    close = df["close"].to_numpy(dtype=float)
    sig = signals.reindex(df.index).fillna(0).to_numpy()
    log_rets = np.diff(np.log(close), prepend=np.log(close[0]))
    n = len(close)
    hold = hold_days or dte

    trades: list[float] = []
    i = 0
    while i < n - 1:
        if sig[i] >= 1:
            S0 = close[i]
            sigma = _annualized_vol(log_rets, i)
            long_k = S0
            short_k = S0 * (1 + width_pct) if kind == "call" else S0 * (1 - width_pct)
            T0 = dte / 252.0
            debit = bs_price(S0, long_k, T0, r, sigma, kind) - bs_price(S0, short_k, T0, r, sigma, kind)

            exit_i = min(i + hold, n - 1)
            t_left = max(0.0, (dte - (exit_i - i)) / 252.0)
            S1 = close[exit_i]
            value = bs_price(S1, long_k, t_left, r, sigma, kind) - bs_price(S1, short_k, t_left, r, sigma, kind)

            trades.append((value - debit) * 100.0 * contracts)
            i = exit_i + 1  # no overlapping positions
        else:
            i += 1

    if not trades:
        return SpreadBacktestResult(0.0, 0, 0.0, 0.0, 0.0, [])

    arr = np.array(trades)
    equity = np.cumsum(arr)
    running_max = np.maximum.accumulate(equity)
    max_dd = float((equity - running_max).min())
    return SpreadBacktestResult(
        total_pnl=float(arr.sum()),
        n_trades=len(trades),
        win_rate=float((arr > 0).mean()),
        avg_pnl=float(arr.mean()),
        max_drawdown=max_dd,
        trades=trades,
    )
