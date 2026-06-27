"""Strategy interface. Deterministic strategies generate signals; the LLM layer reasons
about them but never replaces the math. New strategies (incl. an optional FinRL policy)
implement this same interface and drop into ``strategies.REGISTRY``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


@dataclass
class Signal:
    symbol: str
    action: str  # "buy" | "sell" | "hold"
    strength: float  # 0..1 conviction
    rationale: str = ""


class Strategy(ABC):
    name: str = "base"

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Return a Series aligned to df.index of target positions in {-1, 0, 1}."""

    def latest_signal(self, symbol: str, df: pd.DataFrame) -> Signal:
        positions = self.generate_signals(df)
        if positions.empty:
            return Signal(symbol, "hold", 0.0, "no data")
        pos = int(positions.iloc[-1])
        prev = int(positions.iloc[-2]) if len(positions) > 1 else 0
        if pos > prev:
            return Signal(symbol, "buy", 0.7, f"{self.name}: position {prev}->{pos}")
        if pos < prev:
            return Signal(symbol, "sell", 0.7, f"{self.name}: position {prev}->{pos}")
        return Signal(symbol, "hold", 0.3, f"{self.name}: steady ({pos})")
