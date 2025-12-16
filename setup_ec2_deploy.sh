#!/usr/bin/env bash
# Deploy Cascade to EC2 and run immediately (--now)
set -e

INSTANCE_ID="i-0547233d79e6016dc"
REGION="us-east-1"
REMOTE_USER="ubuntu"
# Ensure the SSH key has correct permissions
SSH_KEY="$(pwd)/aws_key.pem"
chmod 600 "$SSH_KEY"
PROJECT_DIR="~/cascade"

echo "Querying instance IP from AWS..."

# Get instance state
INSTANCE_STATE=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text)

echo "Instance state: $INSTANCE_STATE"

if [ "$INSTANCE_STATE" = "stopped" ]; then
    echo "Instance is stopped. Starting it..."
    aws ec2 start-instances --instance-ids "$INSTANCE_ID" --region "$REGION" > /dev/null
    echo "Waiting for instance to enter running state..."
    aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"
    echo "Instance is now running. Waiting for IP assignment..."
    sleep 10
fi

# Get the current public IP
REMOTE_HOST=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

if [ -z "$REMOTE_HOST" ] || [ "$REMOTE_HOST" = "None" ]; then
    echo "Waiting for public IP assignment..."
    sleep 15
    REMOTE_HOST=$(aws ec2 describe-instances \
        --instance-ids "$INSTANCE_ID" \
        --region "$REGION" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)
fi

if [ -z "$REMOTE_HOST" ] || [ "$REMOTE_HOST" = "None" ]; then
    echo "ERROR: Failed to get public IP. Check instance in AWS Console."
    exit 1
fi

echo "Instance IP: $REMOTE_HOST"

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
