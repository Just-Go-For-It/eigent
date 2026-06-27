"""CLI entrypoint.

    python -m src.main --dry                 # full offline pipeline, no keys needed
    python -m src.main --strategy options_income --dry
    python -m src.main                        # uses real providers if keys are set (paper)

A --dry run uses synthetic data + a mock LLM + the paper broker, so it ALWAYS works with no
secrets and is safe to run anywhere. It prints the full agent trace and a summary.
"""
from __future__ import annotations

import argparse

from .config import load_config
from .execution.broker import PaperBroker
from .pipeline import run_once
from .store import Store


def main() -> int:
    ap = argparse.ArgumentParser(description="ai-trader")
    ap.add_argument("--dry", action="store_true", help="offline dry run (mock data + LLM + paper broker)")
    ap.add_argument("--strategy", default="ma_crossover", choices=["ma_crossover", "options_income"])
    ap.add_argument("--no-db", action="store_true", help="do not write the audit DB")
    args = ap.parse_args()

    config = load_config()
    print("=" * 72)
    print("ai-trader —", config.summary())
    if args.dry:
        print("MODE: DRY RUN (synthetic data, mock LLM, paper broker — no orders leave the box)")
    print("=" * 72)

    store = None if args.no_db else Store()
    broker = PaperBroker(starting_cash=config.starting_equity_usd)

    report = run_once(config=config, strategy_name=args.strategy, broker=broker, store=store)

    for d in report.decisions:
        flag = "OK " if d.approved else "REJ"
        print(f"\n[{flag}] {d.symbol}: {d.final_action.upper()}")
        for line in d.trace:
            print("      " + line)
        if d.risk_reasons:
            print("      risk_reasons: " + "; ".join(d.risk_reasons))

    approved = sum(1 for d in report.decisions if d.approved and d.order)
    print("\n" + "-" * 72)
    print(f"symbols evaluated : {len(report.decisions)}")
    print(f"orders submitted  : {report.fills}")
    print(f"orders approved   : {approved}")
    print(f"ending equity     : ${report.equity:,.2f}")
    print("-" * 72)
    if store:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
