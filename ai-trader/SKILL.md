# SKILL: ai-trader

A guide for an AI agent (Replit agent, Claude Code, Codex, Cursor) to operate or extend this
repo. (Pattern inspired by HKUDS/AI-Trader's agent-native skill registration.)

## What this repo is
A paper-first LLM trading agent for US stocks & options. Decisions are grounded in
deterministic, backtested strategies; an LLM layer adds research and risk reasoning; a
non-bypassable `RiskGuard` controls all money.

## Capabilities you can invoke
| Goal | Command |
|---|---|
| Run all tests (safety gate) | `python -m pytest -q` |
| Backtest a strategy | `python -m src.backtest.run --strategy ma_crossover --days 750` |
| Offline dry run (no keys) | `python -m src.main --dry` |
| Paper run (needs ALPACA_* keys) | `python -m src.main` |
| Always-on worker | `python -m src.worker` |
| API server | `uvicorn src.api.app:app --port 8000` |

## How to extend safely
1. **New strategy:** subclass `src/strategies/base.py:Strategy`, implement
   `generate_signals(df) -> Series[{0,1}]`, register it in `src/strategies/__init__.py:REGISTRY`,
   and add a backtest assertion in `tests/test_strategy.py`.
2. **New data source:** subclass `src/data/providers.py:DataProvider`.
3. **New broker:** subclass `src/execution/broker.py:Broker` and wire it into `get_broker`.
   Existing backends: `paper` (sim), `alpaca_mcp` (MCP server), `alpaca_sdk` (direct REST),
   chosen via `EXECUTION_BACKEND`. Keep `ALPACA_PAPER_TRADE=true`.
4. **New analyst signal:** the fundamentals/news node lives in `src/data/fundamentals.py`
   (`FundamentalsProvider`); `score_metrics` maps data to a bounded conviction nudge. Add
   sources by subclassing `FundamentalsProvider` and updating `get_fundamentals`.
5. **Never weaken `src/risk/guard.py`.** All orders must pass `RiskGuard.check`. If you change
   limits, update `tests/test_risk.py` and keep every rejection test passing.

## Hard rules for an autonomous agent
- Default to **paper** (`TRADING_MODE=paper`). Never switch to live without explicit human
  sign-off (`HUMAN_APPROVAL=true` and a human-set `_approved` flag).
- Never commit secrets. `.env` is git-ignored; use platform secret stores.
- Never expose the API without `API_AUTH_TOKEN` (the documented NoFx mistake).
- Treat backtest results as hypotheses, not proof. Surface drawdown and assumptions.
