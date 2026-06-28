"""Deterministic risk control — the single most important safety component.

Every order, whether proposed by an LLM, a webhook, or a strategy, MUST pass through
``RiskGuard.check``. The guard is pure Python with zero third-party dependencies so it is
trivially testable and impossible for the LLM layer to talk its way around.

It implements:
  * per-order notional cap (max_position_usd)
  * per-trade % of equity cap (max_trade_pct)
  * daily loss kill-switch (daily_max_loss_usd)
  * allowed-symbol allow-list
  * options trading-level cap
  * market-hours-only gate
  * Safety Mode: auto-halt after N consecutive losing trades (NoFx-inspired)
  * paper/live master switch + human-approval requirement for live orders
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timezone

# Approximate US equity regular session in US/Eastern. We compare in UTC to avoid a
# tz database dependency; 13:30-20:00 UTC ~= 09:30-16:00 ET (ignores DST edge by design,
# acceptable because this is a coarse safety gate, not an exchange clock).
_RTH_OPEN_UTC = time(13, 30)
_RTH_CLOSE_UTC = time(20, 0)


@dataclass
class OptionLeg:
    """One leg of a multi-leg (mleg) option order."""

    symbol: str  # OCC option symbol, e.g. AAPL240920C00150000
    side: str  # "buy" | "sell"
    ratio_qty: int = 1


@dataclass
class OrderRequest:
    symbol: str
    side: str  # "buy" | "sell"
    qty: float
    price: float  # estimated fill price (per share, or NET premium per spread for mleg)
    asset_class: str = "equity"  # "equity" | "option"
    options_level: int = 0  # required options level for this order (0 for equities)
    is_close: bool = False  # closing/reducing an existing position (risk-reducing)
    legs: list = field(default_factory=list)  # list[OptionLeg] for multi-leg option orders

    @property
    def is_multileg(self) -> bool:
        return bool(self.legs)

    @property
    def notional(self) -> float:
        # For a defined-risk spread this is a coarse premium-based cap (net debit/credit *
        # 100 * qty), not the structure's max loss. Tighten per-strategy if needed.
        mult = 100.0 if self.asset_class == "option" else 1.0
        return abs(self.qty) * self.price * mult


@dataclass
class RiskDecision:
    approved: bool
    reasons: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:  # allows: if guard.check(...):
        return self.approved


class SafetyMode:
    """Tracks consecutive losing trades and trips a halt (regime-change circuit breaker)."""

    def __init__(self, max_consecutive_losses: int):
        self.max_consecutive_losses = max_consecutive_losses
        self.consecutive_losses = 0
        self.tripped = False

    def record_trade_result(self, pnl: float) -> None:
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.tripped = True

    def reset(self) -> None:
        self.consecutive_losses = 0
        self.tripped = False


class RiskGuard:
    def __init__(self, config, safety: SafetyMode | None = None, *, now_fn=None):
        self.config = config
        self.limits = config.limits
        self.safety = safety or SafetyMode(self.limits.safety_mode_max_consec_losses)
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self.realized_pnl_today = 0.0

    # --- state updates --------------------------------------------------------
    def record_fill(self, pnl: float) -> None:
        """Call after a trade closes to update daily PnL and Safety Mode."""
        self.realized_pnl_today += pnl
        self.safety.record_trade_result(pnl)

    def start_new_day(self) -> None:
        self.realized_pnl_today = 0.0

    # --- the gate -------------------------------------------------------------
    def check(self, order: OrderRequest, equity: float) -> RiskDecision:
        reasons: list[str] = []

        # Safety Mode halt (closing orders are still allowed so we can de-risk).
        if self.safety.tripped and not order.is_close:
            reasons.append(
                f"SAFETY MODE tripped after {self.safety.consecutive_losses} consecutive losses"
            )

        # Daily loss kill-switch (closing orders allowed to reduce exposure).
        if self.realized_pnl_today <= -abs(self.limits.daily_max_loss_usd) and not order.is_close:
            reasons.append(
                f"daily loss limit hit ({self.realized_pnl_today:.2f} <= "
                f"-{self.limits.daily_max_loss_usd:.2f})"
            )

        # Allowed-symbol allow-list.
        if order.symbol.upper() not in self.limits.allowed_symbols:
            reasons.append(f"symbol {order.symbol} not in allow-list {self.limits.allowed_symbols}")

        # Per-order notional cap (skip for risk-reducing closes).
        if not order.is_close and order.notional > self.limits.max_position_usd:
            reasons.append(
                f"notional ${order.notional:.0f} exceeds max ${self.limits.max_position_usd:.0f}"
            )

        # Per-trade % of equity cap.
        if not order.is_close and equity > 0:
            pct = 100.0 * order.notional / equity
            if pct > self.limits.max_trade_pct:
                reasons.append(
                    f"trade is {pct:.2f}% of equity, exceeds max {self.limits.max_trade_pct:.2f}%"
                )

        # Options level cap.
        if order.asset_class == "option" and order.options_level > self.limits.max_options_level:
            reasons.append(
                f"options level {order.options_level} exceeds max {self.limits.max_options_level}"
            )

        # Market-hours gate.
        if self.limits.market_hours_only and not order.is_close and not self._is_market_hours():
            reasons.append("outside regular trading hours")

        # Live-trading guard: refuse live orders unless explicitly enabled + approved.
        if self.config.is_live and self.config.human_approval and not getattr(order, "_approved", False):
            reasons.append("live order requires human approval (HUMAN_APPROVAL=true)")

        return RiskDecision(approved=not reasons, reasons=reasons)

    def _is_market_hours(self) -> bool:
        now = self._now_fn()
        if now.weekday() >= 5:  # Sat/Sun
            return False
        return _RTH_OPEN_UTC <= now.timetz().replace(tzinfo=None) <= _RTH_CLOSE_UTC
