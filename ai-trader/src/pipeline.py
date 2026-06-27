"""One pass of the trading loop, wired together. Used by both the CLI dry run and the
scheduled worker so paper and live share the exact same code path.
"""
from __future__ import annotations

from dataclasses import dataclass

from .agents.firm import Decision, TradingFirm
from .agents.llm import get_llm
from .config import Config, load_config
from .data.providers import get_provider
from .execution.broker import PaperBroker, get_broker
from .risk.guard import RiskGuard, SafetyMode
from .store import Store
from .strategies import REGISTRY


@dataclass
class RunReport:
    decisions: list[Decision]
    fills: int
    equity: float


def run_once(
    config: Config | None = None,
    strategy_name: str = "ma_crossover",
    broker=None,
    store: Store | None = None,
    history_days: int = 365,
) -> RunReport:
    config = config or load_config()
    provider = get_provider(config)
    llm = get_llm(config)
    safety = SafetyMode(config.limits.safety_mode_max_consec_losses)
    guard = RiskGuard(config, safety)
    strategy = REGISTRY[strategy_name]()
    broker = broker or get_broker(config)

    firm = TradingFirm(llm=llm, guard=guard, strategy=strategy, config=config)

    decisions: list[Decision] = []
    fills = 0
    for symbol in config.limits.allowed_symbols:
        df = provider.get_history(symbol, days=history_days)
        price = float(df["close"].iloc[-1])
        equity = broker.equity()
        decision = firm.decide(symbol, df, price, equity)
        decisions.append(decision)
        if store:
            store.log_decision(decision)
        if decision.approved and decision.order is not None:
            fill = broker.submit(decision.order)
            fills += 1
            if store:
                store.log_fill(fill)

    return RunReport(decisions=decisions, fills=fills, equity=broker.equity())
