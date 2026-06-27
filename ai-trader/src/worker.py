"""Always-on scheduled worker (the 'brain' that runs on the VPS/Railway, NOT Vercel).

Schedules the trading loop during US market hours. Uses APScheduler if available; otherwise
falls back to a simple sleep loop so it still runs anywhere. Paper-first: it calls the same
pipeline.run_once used by the CLI.
"""
from __future__ import annotations

import time

from .config import load_config
from .execution.broker import PaperBroker
from .pipeline import run_once
from .store import Store


def tick(config, broker, store) -> None:
    report = run_once(config=config, broker=broker, store=store)
    approved = sum(1 for d in report.decisions if d.approved and d.order)
    print(f"[tick] orders={report.fills} approved={approved} equity=${report.equity:,.2f}")


def main() -> int:
    config = load_config()
    broker = PaperBroker(starting_cash=config.starting_equity_usd)
    store = Store()
    print("worker starting —", config.summary())

    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger

        sched = BlockingScheduler(timezone="UTC")
        # Every 15 min during ~RTH (13:30-20:00 UTC), weekdays.
        sched.add_job(
            lambda: tick(config, broker, store),
            CronTrigger(day_of_week="mon-fri", hour="13-20", minute="*/15"),
        )
        print("APScheduler engaged (15-min cadence during market hours, UTC).")
        sched.start()
    except ImportError:
        print("APScheduler not installed; falling back to 15-min sleep loop.")
        while True:
            tick(config, broker, store)
            time.sleep(900)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
