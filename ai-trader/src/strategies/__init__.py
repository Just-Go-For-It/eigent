from .base import Signal, Strategy
from .ma_crossover import MACrossoverStrategy
from .options_income import OptionsIncomeStrategy

REGISTRY = {
    "ma_crossover": MACrossoverStrategy,
    "options_income": OptionsIncomeStrategy,
}

__all__ = ["Signal", "Strategy", "MACrossoverStrategy", "OptionsIncomeStrategy", "REGISTRY"]
