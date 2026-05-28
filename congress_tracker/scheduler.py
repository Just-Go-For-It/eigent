"""
Daily scheduler — runs the aggregation at a configured time each day.
Uses the stdlib `sched` module for simplicity (no extra dependencies).
For production, use cron or systemd instead (see README).
"""
import logging
import sched
import signal
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _next_run_time(hour: int, minute: int) -> datetime:
    now = datetime.utcnow()
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def run_daily(run_fn, hour: int = 7, minute: int = 0):
    """
    Block forever, calling `run_fn()` once a day at UTC hour:minute.
    Handles SIGINT/SIGTERM for clean shutdown.
    """
    scheduler = sched.scheduler(time.time, time.sleep)
    running = True

    def _shutdown(signum, frame):
        nonlocal running
        logger.info("Shutdown signal received, exiting after current run.")
        running = False

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    def _schedule_next():
        next_dt = _next_run_time(hour, minute)
        delay = (next_dt - datetime.utcnow()).total_seconds()
        logger.info("Next run scheduled at %s UTC (in %.0fs)", next_dt.strftime("%Y-%m-%d %H:%M"), delay)
        scheduler.enter(delay, 1, _execute)

    def _execute():
        logger.info("--- Scheduled run starting ---")
        try:
            run_fn()
        except Exception as exc:
            logger.exception("Run failed: %s", exc)
        if running:
            _schedule_next()

    _schedule_next()
    scheduler.run()
    logger.info("Scheduler exited.")
