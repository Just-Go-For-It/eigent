"""Backtest CLI.

    python -m src.backtest.run                              # equity strategy backtest
    python -m src.backtest.run --asset spread --kind call   # score vertical option spreads

Uses real data when keys are set, otherwise synthetic data (still validates the engine math).
"""
from __future__ import annotations

import argparse

from ..config import load_config
from ..data.providers import get_provider
from ..strategies import REGISTRY
from .engine import run_backtest
from .options import backtest_vertical_spread


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="ma_crossover", choices=list(REGISTRY))
    ap.add_argument("--days", type=int, default=750)
    ap.add_argument("--asset", default="equity", choices=["equity", "spread"])
    ap.add_argument("--kind", default="call", choices=["call", "put"], help="spread option type")
    ap.add_argument("--dte", type=int, default=30, help="days to expiry (spread)")
    ap.add_argument("--width", type=float, default=0.05, help="short-strike offset (spread)")
    args = ap.parse_args()

    config = load_config()
    provider = get_provider(config)
    strat = REGISTRY[args.strategy]()
    symbols = config.limits.allowed_symbols

    if args.asset == "spread":
        print(f"Spread backtest: {args.kind} verticals off {args.strategy} signals "
              f"(dte={args.dte}, width={args.width:.0%}) over {symbols}")
        print("-" * 72)
        for symbol in symbols:
            df = provider.get_history(symbol, days=args.days)
            signals = strat.generate_signals(df)
            res = backtest_vertical_spread(
                df, signals, dte=args.dte, width_pct=args.width, kind=args.kind
            )
            m = res.as_dict()
            print(f"{symbol:6s} pnl=${m['total_pnl']:>10.2f} trades={m['n_trades']:>3} "
                  f"win={m['win_rate']:.1%} avg=${m['avg_pnl']:>8.2f} maxDD=${m['max_drawdown']:>10.2f}")
        print("-" * 72)
        print("NOTE: spread P&L is Black-Scholes-modeled on the underlying path, not real "
              "chains. Synthetic data unless keys set. Backtest != live results.")
        return 0

    print(f"Backtest: {args.strategy} over {symbols} ({args.days} bars)")
    print("-" * 72)
    for symbol in symbols:
        df = provider.get_history(symbol, days=args.days)
        positions = strat.generate_signals(df)
        res = run_backtest(df, positions)
        m = res.as_dict()
        print(f"{symbol:6s} ret={m['total_return']:+.2%} cagr={m['cagr']:+.2%} "
              f"sharpe={m['sharpe']:+.2f} maxDD={m['max_drawdown']:.2%} "
              f"win={m['win_rate']:.1%} trades={m['n_trades']}")
    print("-" * 72)
    print("NOTE: synthetic data unless ALPACA keys are set. Backtest != live results.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
