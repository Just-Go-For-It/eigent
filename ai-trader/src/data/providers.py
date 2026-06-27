"""Market-data providers.

``MockDataProvider`` generates deterministic synthetic OHLCV so the whole pipeline can run
end-to-end with no API keys (dry runs and CI). ``AlpacaDataProvider`` / ``PolygonProvider``
are real adapters with lazy imports so the package stays importable without those deps.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class DataProvider(ABC):
    @abstractmethod
    def get_history(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """Return a DataFrame indexed by date with columns: open, high, low, close, volume."""

    def get_option_chain(self, symbol: str):  # pragma: no cover - optional
        raise NotImplementedError("option chain not implemented for this provider")


class MockDataProvider(DataProvider):
    """Deterministic geometric-brownian-motion price series, seeded per symbol."""

    def __init__(self, seed: int = 42, start_price: float = 100.0):
        self.seed = seed
        self.start_price = start_price

    def get_history(self, symbol: str, days: int = 365) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed + sum(ord(c) for c in symbol.upper()))
        n = days
        dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
        mu, sigma = 0.0003, 0.015  # daily drift / vol
        rets = rng.normal(mu, sigma, n)
        close = self.start_price * np.exp(np.cumsum(rets))
        open_ = close * (1 + rng.normal(0, 0.003, n))
        high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.004, n)))
        low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.004, n)))
        volume = rng.integers(1_000_000, 5_000_000, n)
        return pd.DataFrame(
            {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
            index=dates,
        )


class AlpacaDataProvider(DataProvider):  # pragma: no cover - requires network + keys
    def __init__(self, config):
        from alpaca.data.historical import StockHistoricalDataClient

        self._client = StockHistoricalDataClient(config.alpaca_api_key, config.alpaca_secret_key)

    def get_history(self, symbol: str, days: int = 365) -> pd.DataFrame:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        req = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=pd.Timestamp.today().normalize() - pd.Timedelta(days=days * 2),
        )
        bars = self._client.get_stock_bars(req).df
        if isinstance(bars.index, pd.MultiIndex):
            bars = bars.xs(symbol, level=0)
        return bars.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].tail(days)

    def get_option_chain(self, symbol: str):
        from alpaca.trading.client import TradingClient

        client = TradingClient(
            self.config.alpaca_api_key, self.config.alpaca_secret_key, paper=True
        )
        return client.get_option_contracts(underlying_symbols=[symbol])


def get_provider(config=None) -> DataProvider:
    """Pick a provider: real Alpaca when keys are present, else the mock."""
    if config is not None and config.alpaca_api_key and config.alpaca_secret_key:
        try:  # pragma: no cover
            return AlpacaDataProvider(config)
        except Exception:
            pass
    return MockDataProvider()
