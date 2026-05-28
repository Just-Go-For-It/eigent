#!/usr/bin/env bash
# Install a daily cron job that runs the aggregator at 7:05 AM UTC.
# Run once with: bash congress_tracker/setup_cron.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON="$(which python3)"
LOG_FILE="$SCRIPT_DIR/logs/cron.log"

mkdir -p "$SCRIPT_DIR/logs"

CRON_CMD="5 7 * * * cd \"$REPO_ROOT\" && $PYTHON -m congress_tracker >> \"$LOG_FILE\" 2>&1"

# Check if already installed
(crontab -l 2>/dev/null | grep -qF "congress_tracker") && {
    echo "Cron job already installed."
    crontab -l | grep congress_tracker
    exit 0
}

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
echo "Cron job installed:"
echo "  $CRON_CMD"
echo ""
echo "To remove: crontab -e and delete the congress_tracker line"
echo "Logs: $LOG_FILE"
