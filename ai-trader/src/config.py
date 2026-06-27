"""Central configuration.

Loads from environment variables (and a local .env if python-dotenv is present).
Kept dependency-light on purpose so the safety-critical modules import without any
third-party packages installed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

# Best-effort .env loading; never required.
try:  # pragma: no cover - trivial
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _get_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _get_list(key: str, default: list[str]) -> list[str]:
    raw = os.getenv(key)
    if not raw:
        return list(default)
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


@dataclass
class RiskLimits:
    """Hard, deterministic limits enforced by RiskGuard. The LLM cannot change these."""

    max_position_usd: float = field(default_factory=lambda: _get_float("MAX_POSITION_USD", 2000.0))
    max_trade_pct: float = field(default_factory=lambda: _get_float("MAX_TRADE_PCT", 2.0))
    daily_max_loss_usd: float = field(default_factory=lambda: _get_float("DAILY_MAX_LOSS_USD", 200.0))
    safety_mode_max_consec_losses: int = field(
        default_factory=lambda: _get_int("SAFETY_MODE_MAX_CONSEC_LOSSES", 3)
    )
    max_options_level: int = field(default_factory=lambda: _get_int("MAX_OPTIONS_LEVEL", 2))
    allowed_symbols: list[str] = field(
        default_factory=lambda: _get_list("ALLOWED_SYMBOLS", ["AAPL", "MSFT", "NVDA", "SPY"])
    )
    market_hours_only: bool = field(default_factory=lambda: _get_bool("MARKET_HOURS_ONLY", True))


@dataclass
class Config:
    # Master switches
    trading_mode: str = field(default_factory=lambda: _get("TRADING_MODE", "paper").lower())
    human_approval: bool = field(default_factory=lambda: _get_bool("HUMAN_APPROVAL", True))

    # LLM
    anthropic_api_key: str = field(default_factory=lambda: _get("ANTHROPIC_API_KEY"))
    model_fast: str = field(default_factory=lambda: _get("MODEL_FAST", "claude-haiku-4-5-20251001"))
    model_smart: str = field(default_factory=lambda: _get("MODEL_SMART", "claude-sonnet-4-6"))
    competition_model_api_key: str = field(default_factory=lambda: _get("COMPETITION_MODEL_API_KEY"))

    # Broker (Alpaca)
    alpaca_api_key: str = field(default_factory=lambda: _get("ALPACA_API_KEY"))
    alpaca_secret_key: str = field(default_factory=lambda: _get("ALPACA_SECRET_KEY"))
    alpaca_paper_trade: bool = field(default_factory=lambda: _get_bool("ALPACA_PAPER_TRADE", True))
    execution_backend: str = field(default_factory=lambda: _get("EXECUTION_BACKEND", "paper").lower())

    # Data
    polygon_api_key: str = field(default_factory=lambda: _get("POLYGON_API_KEY"))
    financial_datasets_api_key: str = field(default_factory=lambda: _get("FINANCIAL_DATASETS_API_KEY"))

    # Optional feature flags (all default off)
    enable_personas: bool = field(default_factory=lambda: _get_bool("ENABLE_PERSONAS", False))
    enable_model_competition: bool = field(
        default_factory=lambda: _get_bool("ENABLE_MODEL_COMPETITION", False)
    )
    enable_polymarket: bool = field(default_factory=lambda: _get_bool("ENABLE_POLYMARKET", False))
    enable_finrl: bool = field(default_factory=lambda: _get_bool("ENABLE_FINRL", False))
    enable_fundamentals: bool = field(default_factory=lambda: _get_bool("ENABLE_FUNDAMENTALS", True))

    # Account / sizing
    starting_equity_usd: float = field(
        default_factory=lambda: _get_float("STARTING_EQUITY_USD", 100000.0)
    )

    # Webhook / API auth
    tradingview_webhook_secret: str = field(default_factory=lambda: _get("TRADINGVIEW_WEBHOOK_SECRET"))
    api_auth_token: str = field(default_factory=lambda: _get("API_AUTH_TOKEN"))

    limits: RiskLimits = field(default_factory=RiskLimits)

    @property
    def is_live(self) -> bool:
        return self.trading_mode == "live"

    def summary(self) -> str:
        return (
            f"mode={self.trading_mode} human_approval={self.human_approval} "
            f"paper={self.alpaca_paper_trade} symbols={self.limits.allowed_symbols} "
            f"max_pos=${self.limits.max_position_usd:.0f} daily_loss=${self.limits.daily_max_loss_usd:.0f}"
        )


def load_config() -> Config:
    return Config()
