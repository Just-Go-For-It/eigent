"""
Entry point for the Congress Trading Aggregator.

Usage:
    # Run once immediately:
    python -m congress_tracker

    # Run as daily daemon (7 AM UTC by default):
    python -m congress_tracker --daemon

    # Custom schedule:
    python -m congress_tracker --daemon --hour 8 --minute 30

    # Override lookback window:
    python -m congress_tracker --days 14

Environment variables:
    FINNHUB_API_KEY       - Finnhub free-tier key (optional, recommended)
    QUIVER_API_KEY        - Quiver Quantitative key (optional, paid)
    LOOKBACK_DAYS         - Days of history to pull (default 7)
    REPORTS_DIR           - Output directory (default congress_tracker/reports)
    SEND_EMAIL            - "true" to email the digest
    EMAIL_TO              - Recipient address
    SMTP_HOST/PORT/USER/PASSWORD - SMTP config for email
"""
import argparse
import logging
import os
import sys

# Allow running as `python -m congress_tracker` from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from congress_tracker.config import Config
from congress_tracker import aggregator, digest, scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("congress_tracker")


def parse_args():
    p = argparse.ArgumentParser(description="Congress & Insider Trading Daily Digest")
    p.add_argument("--daemon", action="store_true", help="Run as daily scheduled daemon")
    p.add_argument("--hour", type=int, default=None, help="UTC hour to run (0-23)")
    p.add_argument("--minute", type=int, default=None, help="UTC minute to run (0-59)")
    p.add_argument("--days", type=int, default=None, help="Lookback window in days")
    p.add_argument("--no-email", action="store_true", help="Suppress email even if configured")
    return p.parse_args()


def build_config(args) -> Config:
    cfg = Config()
    if args.days is not None:
        cfg.lookback_days = args.days
    if args.hour is not None:
        cfg.run_hour = args.hour
    if args.minute is not None:
        cfg.run_minute = args.minute
    if args.no_email:
        cfg.send_email = False
    return cfg


def run_once(cfg: Config):
    logger.info("Starting one-time aggregation run...")
    data = aggregator.run(cfg)
    digest.print_to_console(data)
    paths = digest.generate(data, cfg.reports_dir)
    logger.info("Reports written:")
    for name, path in paths.items():
        logger.info("  %-12s -> %s", name, path)

    if cfg.send_email and cfg.email_to and cfg.smtp_user and cfg.smtp_password:
        from congress_tracker import emailer
        emailer.send_digest(
            md_path=paths["markdown"],
            to_addr=cfg.email_to,
            smtp_host=cfg.smtp_host,
            smtp_port=cfg.smtp_port,
            smtp_user=cfg.smtp_user,
            smtp_password=cfg.smtp_password,
        )

    return paths


def main():
    args = parse_args()
    cfg = build_config(args)

    if args.daemon:
        logger.info("Starting daily daemon (runs at %02d:%02d UTC)", cfg.run_hour, cfg.run_minute)
        scheduler.run_daily(
            run_fn=lambda: run_once(cfg),
            hour=cfg.run_hour,
            minute=cfg.run_minute,
        )
    else:
        run_once(cfg)


if __name__ == "__main__":
    main()
