"""Lightweight vectorized backtester (pandas only).

Separates signal discovery from execution realism: positions are shifted by one bar to
avoid look-ahead, and a per-trade cost (commission + slippage, in bps) is applied on
position changes. For large parameter sweeps, swap in VectorBT behind this same function;
for execution-parity replay use NautilusTrader (see plan, Section 3).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    total_return: float
    cagr: float
    sharpe: float
    max_drawdown: float
    win_rate: float
    n_trades: int
    equity_curve: pd.Series

    def as_dict(self) -> dict:
        return {
            "total_return": round(self.total_return, 4),
            "cagr": round(self.cagr, 4),
            "sharpe": round(self.sharpe, 3),
            "max_drawdown": round(self.max_drawdown, 4),
            "win_rate": round(self.win_rate, 4),
            "n_trades": self.n_trades,
        }


def run_backtest(
    df: pd.DataFrame,
    positions: pd.Series,
    cost_bps: float = 5.0,
    periods_per_year: int = 252,
) -> BacktestResult:
    """positions: target exposure in {0,1} (or {-1,0,1}) aligned to df.index."""
    close = df["close"].astype(float)
    rets = close.pct_change().fillna(0.0)

    # Act next bar (no look-ahead).
    pos = positions.reindex(df.index).fillna(0.0).shift(1).fillna(0.0)

    # Transaction costs on position changes.
    turnover = pos.diff().abs().fillna(0.0)
    costs = turnover * (cost_bps / 10_000.0)

    strat_rets = pos * rets - costs
    equity = (1.0 + strat_rets).cumprod()

    total_return = float(equity.iloc[-1] - 1.0) if len(equity) else 0.0
    n_years = max(len(equity) / periods_per_year, 1e-9)
    cagr = float(equity.iloc[-1] ** (1.0 / n_years) - 1.0) if len(equity) and equity.iloc[-1] > 0 else 0.0

    std = strat_rets.std()
    sharpe = float(np.sqrt(periods_per_year) * strat_rets.mean() / std) if std > 0 else 0.0

    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    max_drawdown = float(drawdown.min()) if len(drawdown) else 0.0

    # Trade-level win rate: each entry->exit round trip.
    entries = turnover[turnover > 0]
    n_trades = int(len(entries))
    winning_days = (strat_rets[pos > 0] > 0).sum()
    active_days = (pos > 0).sum()
    win_rate = float(winning_days / active_days) if active_days else 0.0

    return BacktestResult(
        total_return=total_return,
        cagr=cagr,
        sharpe=sharpe,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        n_trades=n_trades,
        equity_curve=equity,
    )
