"""Classic fast/slow moving-average crossover (long/flat). Vectorized, no look-ahead:
positions are shifted so today's signal is acted on next bar in the backtester.
"""
from __future__ import annotations

import pandas as pd

from .base import Strategy


class MACrossoverStrategy(Strategy):
    name = "ma_crossover"

    def __init__(self, fast: int = 20, slow: int = 50):
        if fast >= slow:
            raise ValueError("fast window must be < slow window")
        self.fast = fast
        self.slow = slow

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        fast_ma = close.rolling(self.fast).mean()
        slow_ma = close.rolling(self.slow).mean()
        position = (fast_ma > slow_ma).astype(int)  # 1 = long, 0 = flat
        position[slow_ma.isna()] = 0
        return position.rename("position")
