#!/usr/bin/env bash
# Deploy Cascade to EC2 and run immediately (--now)
set -e

REMOTE_HOST="44.210.233.242"
REMOTE_USER="ubuntu"
# Ensure the SSH key has correct permissions
SSH_KEY="$(pwd)/aws_key.pem"
chmod 600 "$SSH_KEY"
PROJECT_DIR="~/cascade"

# 1. Create project directory on remote
ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $PROJECT_DIR"

# 2. Transfer code (excluding .git, venv, __pycache__)
rsync -avz -e "ssh -i $SSH_KEY" --exclude='.git' --exclude='venv' --exclude='__pycache__' ./ "$REMOTE_USER@$REMOTE_HOST:$PROJECT_DIR/"

# 3. Transfer .env securely (do not modify local)
scp -i "$SSH_KEY" .env "$REMOTE_USER@$REMOTE_HOST:$PROJECT_DIR/.env"

# 4. Install dependencies on remote
ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" "python3 -m venv $PROJECT_DIR/venv && source $PROJECT_DIR/venv/bin/activate && pip install -r $PROJECT_DIR/requirements.txt"

# 5. Run the program immediately with --now (default mode round_robin_1)
ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" "cd $PROJECT_DIR && source venv/bin/activate && python cascade_main.py --mode round_robin_1 --now"
