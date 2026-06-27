"""Backtest CLI:  python -m src.backtest.run [--strategy ma_crossover] [--days 750]

Runs the selected strategy over each allowed symbol and prints metrics. Uses real data when
keys are set, otherwise synthetic data (still useful to validate the engine + strategy math).
"""
from __future__ import annotations

import argparse

from ..config import load_config
from ..data.providers import get_provider
from ..strategies import REGISTRY
from .engine import run_backtest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="ma_crossover", choices=list(REGISTRY))
    ap.add_argument("--days", type=int, default=750)
    args = ap.parse_args()

    config = load_config()
    provider = get_provider(config)
    strat = REGISTRY[args.strategy]()

    print(f"Backtest: {args.strategy} over {config.limits.allowed_symbols} ({args.days} bars)")
    print("-" * 72)
    for symbol in config.limits.allowed_symbols:
        df = provider.get_history(symbol, days=args.days)
        positions = strat.generate_signals(df)
        res = run_backtest(df, positions)
        m = res.as_dict()
        print(
            f"{symbol:6s} ret={m['total_return']:+.2%} cagr={m['cagr']:+.2%} "
            f"sharpe={m['sharpe']:+.2f} maxDD={m['max_drawdown']:.2%} "
            f"win={m['win_rate']:.1%} trades={m['n_trades']}"
        )
    print("-" * 72)
    print("NOTE: synthetic data unless ALPACA keys are set. Backtest != live results.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
