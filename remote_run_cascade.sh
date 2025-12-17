#!/bin/bash
# Remote execution script for Cascade on EC2
# This script is uploaded and executed on the EC2 instance
# It handles running Cascade and optionally shutting down the instance

set -e

PROJECT_DIR="$HOME/cascade"
LOG_FILE="$PROJECT_DIR/cascade.log"

cd "$PROJECT_DIR"

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found. Setup may have failed."
    exit 1
fi

source venv/bin/activate

# Log execution
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=========================================="
echo "Cascade Remote Execution"
echo "Start time: $(date)"
echo "Working directory: $(pwd)"
echo "=========================================="

# Get command arguments from script invocation
# This script expects to be called with: ./remote_run_cascade.sh <mode> [args...]
MODE="${1:-backend}"
shift || true

# Build Python command
PYTHON_CMD="python cascade_main.py"

if [ "$MODE" = "backend" ]; then
    PYTHON_CMD="$PYTHON_CMD --backend"
else
    PYTHON_CMD="$PYTHON_CMD --mode $MODE"
fi

# Add remaining arguments
PYTHON_CMD="$PYTHON_CMD $@"

echo "Executing: $PYTHON_CMD"
echo ""

# Run Cascade
$PYTHON_CMD

EXIT_CODE=$?

echo ""
echo "=========================================="
echo "Cascade execution completed at: $(date)"
echo "Exit code: $EXIT_CODE"
echo "=========================================="

# Shutdown instance if script was called with shutdown flag
# (This is handled by the PowerShell script that generates this file)
# If we reach here and should shutdown, it means the script was generated with shutdown enabled

exit $EXIT_CODE

