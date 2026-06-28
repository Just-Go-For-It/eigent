"""The 'trading firm' pipeline (TradingAgents-style, enriched with an ai-hedge-fund-style
Portfolio Manager and a NoFx-style Safety Mode gate).

Flow:  analysts -> bull/bear debate -> trader (proposes order) -> LLM risk note
       -> RiskGuard (DETERMINISTIC, non-bypassable) -> Portfolio Manager (final)

It runs as plain composable functions so it works with or without LangGraph. To use the
LangGraph runtime, wrap each method as a node (see build_langgraph below; optional dep).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..data.fundamentals import FundamentalsProvider, score_metrics
from ..risk.guard import OrderRequest, RiskGuard
from ..strategies.base import Signal, Strategy
from .llm import LLM
from .sentiment import SentimentAnalyzer


@dataclass
class Decision:
    symbol: str
    final_action: str  # "buy" | "sell" | "hold" | "rejected"
    order: OrderRequest | None
    approved: bool
    trace: list[str] = field(default_factory=list)
    risk_reasons: list[str] = field(default_factory=list)

    def log(self, who: str, msg: str) -> None:
        self.trace.append(f"[{who}] {msg}")


class TradingFirm:
    def __init__(
        self,
        llm: LLM,
        guard: RiskGuard,
        strategy: Strategy,
        config,
        fundamentals: FundamentalsProvider | None = None,
        sentiment: SentimentAnalyzer | None = None,
    ):
        self.llm = llm
        self.guard = guard
        self.strategy = strategy
        self.config = config
        self.fundamentals = fundamentals
        self.sentiment = sentiment or SentimentAnalyzer()

    # --- individual agents ----------------------------------------------------
    def _analyst(self, symbol: str, df: pd.DataFrame) -> Signal:
        return self.strategy.latest_signal(symbol, df)

    def _fundamentals_view(self, symbol: str) -> tuple[float, str, list[str]]:
        """Return (bounded score adjustment, rationale, news headlines)."""
        if not self.config.enable_fundamentals or self.fundamentals is None:
            return 0.0, "fundamentals: disabled", []
        metrics = self.fundamentals.get_metrics(symbol)
        score_adj, rationale = score_metrics(metrics)
        news = self.fundamentals.get_news(symbol, limit=3)
        titles = [n.get("title", "") for n in news if n.get("title")][:3]
        return score_adj, rationale, titles

    def _debate(self, signal: Signal, df: pd.DataFrame) -> float:
        """Bull/bear adjustment to conviction using simple momentum confirmation."""
        mom = df["close"].iloc[-1] / df["close"].iloc[-20:].mean() - 1.0 if len(df) >= 20 else 0.0
        bull = max(0.0, mom) + signal.strength
        bear = max(0.0, -mom) + (1.0 - signal.strength)
        return bull - bear  # >0 favours long

    # --- main pipeline --------------------------------------------------------
    def decide(self, symbol: str, df: pd.DataFrame, price: float, equity: float) -> Decision:
        d = Decision(symbol=symbol, final_action="hold", order=None, approved=False)

        signal = self._analyst(symbol, df)
        d.log("analyst", f"{signal.action} (conv={signal.strength:.2f}) — {signal.rationale}")

        score = self._debate(signal, df)
        d.log("debate", f"bull-bear score={score:+.3f}")

        # Fundamentals + news analyst (real Financial Datasets data when a key is set).
        f_adj, f_rationale, headlines = self._fundamentals_view(symbol)
        d.log("fundamentals-analyst", f"{f_rationale} (adj={f_adj:+.2f})")
        if headlines:
            d.log("news", " | ".join(headlines))
        score += f_adj
        d.log("debate", f"score after fundamentals={score:+.3f}")

        # Sentiment sub-agent over the news feed (bounded, secondary weight).
        sent_adj, sent_label = 0.0, "sentiment: disabled"
        if getattr(self.config, "enable_sentiment", True):
            sent_adj, sent_label = self.sentiment.score(headlines)
            d.log("sentiment-analyst", f"{sent_label} (adj={sent_adj:+.2f})")
            score += 0.5 * sent_adj
            d.log("debate", f"score after sentiment={score:+.3f}")

        # LLM narrative (mock or Claude) — reasons over the real data; commentary, not decision.
        note = self.llm.complete(
            system="You are a risk-aware trading analyst. Be concise.",
            prompt=f"Symbol {symbol}: technical signal={signal.action}, combined score={score:+.2f}. "
            f"{f_rationale}. {sent_label}. Headlines: {headlines or 'none'}. "
            f"One sentence: is acting prudent now?",
            model=getattr(self.config, "model_smart", None),
        )
        d.log("llm", note)

        if signal.action == "hold" or score <= 0:
            d.final_action = "hold"
            d.approved = True  # holding is always allowed
            d.log("trader", "no actionable edge -> hold")
            return d

        # Trader sizes the order within the per-trade cap.
        budget = min(
            self.config.limits.max_position_usd,
            equity * self.config.limits.max_trade_pct / 100.0,
        )
        qty = max(0.0, round(budget / price, 4)) if price > 0 else 0.0
        if qty <= 0:
            d.final_action = "hold"
            d.approved = True
            d.log("trader", "computed qty<=0 -> hold")
            return d

        order = OrderRequest(symbol=symbol, side=signal.action, qty=qty, price=price)
        d.log("trader", f"propose {order.side} {order.qty} {symbol} @ {price:.2f} (${order.notional:.0f})")

        # LLM risk officer note (commentary).
        d.log("risk-officer", self.llm.complete(
            system="You are a conservative risk officer.",
            prompt=f"Order: {order.side} {order.qty} {symbol} notional ${order.notional:.0f}. Risks?",
        ))

        # DETERMINISTIC risk gate — the part that actually controls money.
        rd = self.guard.check(order, equity=equity)
        if not rd.approved:
            d.final_action = "rejected"
            d.approved = False
            d.risk_reasons = rd.reasons
            d.log("RISKGUARD", "REJECTED: " + "; ".join(rd.reasons))
            return d

        # Portfolio Manager final say.
        d.order = order
        d.final_action = signal.action
        d.approved = True
        d.log("portfolio-manager", f"APPROVED {order.side} {order.qty} {symbol}")
        return d


def build_langgraph(firm: "TradingFirm"):  # pragma: no cover - optional dependency
    """Optionally wrap the firm as a LangGraph StateGraph. Requires `langgraph`."""
    from langgraph.graph import END, START, StateGraph

    sg = StateGraph(dict)

    def _decide(state: dict) -> dict:
        d = firm.decide(state["symbol"], state["df"], state["price"], state["equity"])
        return {"decision": d}

    sg.add_node("firm", _decide)
    sg.add_edge(START, "firm")
    sg.add_edge("firm", END)
    return sg.compile()
