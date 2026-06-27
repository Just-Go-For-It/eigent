"""Options income scanner (cash-secured puts / covered calls).

This is a deliberately simple, transparent heuristic scaffold: it flags when realized
volatility is elevated and trend is non-bearish — a context where selling premium (CSP)
is commonly considered. Real option selection (strike/expiry/greeks) plugs in via the
data provider's option chain + QuantLib pricing. Equity-style signal kept for backtesting.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Signal, Strategy


class OptionsIncomeStrategy(Strategy):
    name = "options_income"

    def __init__(self, vol_window: int = 20, trend_window: int = 50, vol_threshold: float = 0.015):
        self.vol_window = vol_window
        self.trend_window = trend_window
        self.vol_threshold = vol_threshold

    def _features(self, df: pd.DataFrame):
        rets = df["close"].pct_change()
        realized_vol = rets.rolling(self.vol_window).std()
        trend = df["close"] > df["close"].rolling(self.trend_window).mean()
        return realized_vol, trend

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        realized_vol, trend = self._features(df)
        # "1" here means "premium-selling regime favourable" (proxy long-delta exposure).
        position = ((realized_vol > self.vol_threshold) & trend).astype(int)
        position[realized_vol.isna()] = 0
        return position.rename("position")

    def latest_signal(self, symbol: str, df: pd.DataFrame) -> Signal:
        realized_vol, trend = self._features(df)
        if realized_vol.empty or np.isnan(realized_vol.iloc[-1]):
            return Signal(symbol, "hold", 0.0, "insufficient data")
        rv = float(realized_vol.iloc[-1])
        favourable = bool((rv > self.vol_threshold) and bool(trend.iloc[-1]))
        if favourable:
            return Signal(
                symbol,
                "buy",
                min(1.0, rv / self.vol_threshold / 2),
                f"options_income: elevated RV={rv:.3f} & non-bearish trend -> consider CSP",
            )
        return Signal(symbol, "hold", 0.2, f"options_income: RV={rv:.3f} not favourable")
