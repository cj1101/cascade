#!/bin/bash
# Cascade Auto-Start Script
# Detects current day and runs appropriate mode
# Runs on boot via systemd service

set -e

cd ~/cascade
source venv/bin/activate

# Get current day of week (0=Sunday, 1=Monday, ..., 5=Friday, 6=Saturday)
DAY_OF_WEEK=$(date +%w)

echo "=========================================="
echo "Cascade Auto-Start Script"
echo "Start time: $(date)"
echo "Day of week: $DAY_OF_WEEK"
echo "=========================================="

# Determine which mode to run based on day
case $DAY_OF_WEEK in
    5)  # Friday
        echo "Running Round Robin 1..."
        python cascade_main.py --mode round_robin_1
        ;;
    6)  # Saturday
        echo "Running Round Robin 2..."
        python cascade_main.py --mode round_robin_2
        ;;
    0)  # Sunday
        echo "Running Tournament..."
        python cascade_main.py --mode tournament
        ;;
    *)
        echo "ERROR: This script should only run on Friday, Saturday, or Sunday"
        echo "Current day: $DAY_OF_WEEK ($(date +%A))"
        exit 1
        ;;
esac

echo "=========================================="
echo "Cascade program completed at: $(date)"
echo "Shutting down instance..."
echo "=========================================="

# Shutdown the instance after completion
sudo shutdown -h now

