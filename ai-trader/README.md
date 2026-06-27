# ai-trader

An LLM-driven **stock & options** trading agent — research → strategy → backtest →
**paper/live** execution — built **paper-first** with hard, code-enforced risk controls.

- **Agent design:** a TradingAgents-style "firm" (analysts → bull/bear debate → trader →
  risk → portfolio manager), enriched with an ai-hedge-fund-style Portfolio Manager and a
  **NoFx-style Safety Mode** (auto-halt after N consecutive losses).
- **Execution:** [Alpaca](https://alpaca.markets) (commission-free stocks + options, free
  paper account) via its **official MCP server**.
- **The decision is grounded in deterministic, backtested signals.** The LLM adds research
  synthesis and risk reasoning — it is *not* treated as an oracle.

> ⚠️ **Not financial advice. Educational scaffold.** Backtests never guarantee live results.
> Options can lose 100%. **Paper-trade for weeks** before risking a cent. Hard limits live in
> code (`src/risk/guard.py`), never only in prompts.

---

## Quickstart (no secrets needed)

```bash
cd ai-trader
pip install ".[dev]"            # or: pip install pandas numpy python-dotenv pytest
python -m pytest -q            # 23 tests, incl. the RiskGuard safety gate
python -m src.backtest.run     # backtest metrics (synthetic data until keys are set)
python -m src.main --dry       # full offline pipeline: mock data + mock LLM + paper broker
```

`--dry` runs the entire agent loop with **synthetic data, a mock LLM, and an in-memory paper
broker** — it works anywhere, places no real orders, and prints the full agent trace.

## Running with real (paper) data + Claude

```bash
cp .env.example .env           # fill ANTHROPIC_API_KEY + ALPACA_* (paper) [+ FINANCIAL_DATASETS_API_KEY]
pip install ".[live]"
python -m src.main             # uses real Alpaca paper data; ALPACA_PAPER_TRADE=true
python -m src.worker           # always-on scheduled loop (15-min cadence in market hours)
```

Keys are read from the environment / `.env`. With no keys, every component falls back to a
safe mock, so the project is always runnable.

### Execution backends (`EXECUTION_BACKEND`)
| Value | Path | Notes |
|---|---|---|
| `paper` (default) | in-memory simulator | no network, used by tests/dry runs |
| `alpaca_mcp` | official Alpaca **MCP server** | `uvx alpaca-mcp-server` (stdio); the LLM-native order path |
| `alpaca_sdk` | `alpaca-py` direct REST | **recommended for live** — structured fills, robust parsing |

For `alpaca_mcp`, start the server (it reads the same `ALPACA_*` env, paper by default):
```bash
uvx alpaca-mcp-server          # see mcp.json; or: pipx run alpaca-mcp-server
```
Both real backends **refuse to trade live** unless `ALPACA_PAPER_TRADE=false` **and**
`TRADING_MODE=live`, and RiskGuard still gates every order. A missing dep/credential safely
falls back to the paper simulator.

### Fundamentals & news analyst
When `FINANCIAL_DATASETS_API_KEY` is set (and `ENABLE_FUNDAMENTALS=true`, the default), the
firm adds a real fundamentals/news node (`src/data/fundamentals.py`) that pulls company
metrics + headlines from the [Financial Datasets API](https://docs.financialdatasets.ai) and
nudges the bull/bear conviction (bounded; it never bypasses risk). Without a key it uses a
neutral mock so dry runs stay offline.

---

## Architecture

```
Scheduler / TradingView webhook (optional signal)
        │
        ▼
 LangGraph-style "firm":
   analysts → bull/bear debate → trader (proposes order)
        → LLM risk note → ⛔ RiskGuard (deterministic code) → Portfolio Manager
        │
        ▼
   Alpaca MCP server → Alpaca (paper → live)
        │
        ▼
   SQLite audit log (every decision + fill)
```

| Module | Purpose |
|---|---|
| `src/config.py` | Env-driven config + hard risk limits + PAPER/LIVE switch |
| `src/risk/guard.py` | **RiskGuard + Safety Mode — the non-bypassable money gate** |
| `src/data/` | Mock provider (offline) + Alpaca/Polygon adapters (lazy) |
| `src/strategies/` | `Strategy` interface + MA-crossover + options-income scanner |
| `src/backtest/` | Vectorized backtester (no look-ahead, costs) + CLI |
| `src/agents/` | LLM wrapper (Claude/mock) + the trading-firm pipeline |
| `src/data/fundamentals.py` | Fundamentals + news analyst (Financial Datasets API; lazy) |
| `src/execution/` | Paper sim + `alpaca_mcp.py` (MCP) + `alpaca_sdk.py` (direct) + async bridge |
| `src/pipeline.py` | One wired pass of the loop (shared by CLI + worker) |
| `src/worker.py` | APScheduler always-on loop (the VPS/Railway brain) |
| `src/api/app.py` | FastAPI status/approve/webhook (bearer-auth) |
| `dashboard/` | Static read-only dashboard (Vercel) |

## Deployment (Vercel **and** VPS, both from GitHub)

- **VPS / Railway = the always-on brain.** Serverless (Vercel) functions time out and have no
  persistent scheduler, so the trading loop must run here.
  ```bash
  # on a $5–6/mo VPS with Docker:
  git clone <repo> && cd ai-trader && cp .env.example .env   # fill secrets
  docker compose up -d        # worker + api, restart: unless-stopped
  ```
  Railway: deploy from GitHub → add a **Worker** service → set env vars → restart-on-crash.
- **Vercel = read-only dashboard only.** Import the repo, set root to `dashboard/` (static).
  Point it at your VPS API URL + token. Do **not** run the loop on Vercel.

## Test / dry-run tiers (do these in order)

| Tier | Command | Gate |
|---|---|---|
| 0 Unit | `python -m pytest -q` | RiskGuard + Safety Mode must pass |
| 1 Backtest | `python -m src.backtest.run` | review CAGR/Sharpe/maxDD/win-rate 🧑 |
| 2 Paper | `python -m src.main` (paper keys) | run **weeks**; compare vs backtest 🧑 |
| 3 Live | `TRADING_MODE=live HUMAN_APPROVAL=true` | tiny size, explicit human sign-off 🧑 |

## Optional modules (off by default)

Toggle via env flags: `ENABLE_PERSONAS` (ai-hedge-fund investor personas),
`ENABLE_MODEL_COMPETITION` (run a 2nd model on a segregated paper account),
`ENABLE_POLYMARKET` (prediction-market sub-agent), `ENABLE_FINRL` (deep-RL strategy plugin).
Each plugs into the existing `Strategy` / firm interfaces.

## Full strategy & build guide

See [`plan/`](plan/) for the complete research-backed plan (v1) and the optimized,
agent-ready build guide (v2), including sources and the projects this design draws from.
