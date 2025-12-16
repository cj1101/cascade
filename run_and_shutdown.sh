#!/bin/bash
cd ~/cascade
source venv/bin/activate

echo "Starting Round Robin 1 with 5-minute intervals..."
echo "Start time: $(date)"

# Run the round robin with 5-minute debug intervals
python cascade_main.py --mode round_robin_1 --now --debug-interval 5

echo "Round Robin 1 completed at: $(date)"
echo "Shutting down instance..."

# Shutdown the instance after completion
sudo shutdown -h now





