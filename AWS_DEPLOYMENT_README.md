# AWS EC2 Remote Execution Guide

This guide explains how to run the Cascade application on an AWS EC2 instance directly from your local Windows console.

## Prerequisites

1. **AWS CLI installed** - Download from [AWS CLI](https://aws.amazon.com/cli/)
2. **SSH client** - Usually comes with Windows 10/11 or Git for Windows
3. **AWS Credentials** - Set as environment variables:
   ```powershell
   $env:AWS_CLI_ACCESS_KEY = "your-access-key"
   $env:AWS_CLI_SECRET_KEY = "your-secret-key"
   ```
4. **SSH Key** - Your EC2 key pair (default location: `C:\Users\<username>\.ssh\aws_cascade`)
5. **.env file** - Contains your application credentials (GEMINI_API_KEY, CASCADIA_ACCESS_TOKEN, etc.)

## Quick Start

### 1. Set AWS Credentials (One-time setup)

```powershell
# Set in current PowerShell session
$env:AWS_CLI_ACCESS_KEY = "your-access-key"
$env:AWS_CLI_SECRET_KEY = "your-secret-key"

# Or set permanently (requires admin)
[System.Environment]::SetEnvironmentVariable("AWS_CLI_ACCESS_KEY", "your-access-key", "User")
[System.Environment]::SetEnvironmentVariable("AWS_CLI_SECRET_KEY", "your-secret-key", "User")
```

### 2. Configure SSH Key Location

Option A: Set in `.env` file:
```
KEY_PAIR_LOCATION=C:\Users\charl\.ssh\aws_cascade
```

Option B: Place key at default location: `C:\Users\<username>\.ssh\aws_cascade`

### 3. Run Cascade on AWS

```powershell
# Run Round Robin 1 immediately
.\run_on_aws.ps1 --mode round_robin_1 --now

# Run Round Robin 2 immediately
.\run_on_aws.ps1 --mode round_robin_2 --now

# Run Tournament immediately
.\run_on_aws.ps1 --mode tournament --now

# Run full backend mode (all phases) with 5-second waits
.\run_on_aws.ps1 --mode backend --wait-seconds 5

# Run without Instagram posting
.\run_on_aws.ps1 --mode round_robin_1 --now --no-instagram

# Run without Gemini image generation
.\run_on_aws.ps1 --mode round_robin_1 --now --no-gemini

# Run and keep instance running (don't auto-shutdown)
.\run_on_aws.ps1 --mode round_robin_1 --now --no-shutdown
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `--mode` | Execution mode: `round_robin_1`, `round_robin_2`, `tournament`, or `backend` (required) |
| `--now` | Run immediately without waiting for schedule |
| `--debug-interval` | Debug mode with interval in minutes between stages |
| `--no-instagram` | Disable Instagram posting |
| `--no-gemini` | Disable Gemini image generation |
| `--no-podcast` | Disable podcast generation |
| `--wait-seconds` | Seconds to wait between weeks (backend mode, default: 10) |
| `--no-shutdown` | Don't auto-shutdown instance after completion |

## How It Works

1. **Instance Management**: Script checks EC2 instance state and starts it if stopped
2. **Code Deployment**: Uploads codebase (excluding venv, __pycache__, .git, .env, *.png)
3. **Environment Setup**: Creates Python virtual environment and installs dependencies
4. **Secure Upload**: Uploads `.env` file separately with credentials
5. **Execution**: Runs Cascade application on remote instance
6. **Auto-Shutdown**: Instance automatically shuts down when complete (unless `--no-shutdown`)

## Monitoring Execution

### View Logs in Real-Time

```powershell
# SSH into instance and tail the log
ssh -i C:\Users\charl\.ssh\aws_cascade ubuntu@<instance-ip> 'tail -f ~/cascade/cascade.log'
```

### Check Instance Status

```powershell
aws ec2 describe-instances --instance-ids i-0547233d79e6016dc --region us-east-1 --query 'Reservations[0].Instances[0].State.Name' --output text
```

## Troubleshooting

### AWS CLI Not Found
- Install AWS CLI from [aws.amazon.com/cli](https://aws.amazon.com/cli/)
- Verify installation: `aws --version`

### SSH Key Not Found
- Ensure key exists at path specified in `.env` or default location
- Check key permissions (should be readable only by owner)

### Instance Won't Start
- Check AWS credentials are set correctly
- Verify IAM permissions allow EC2 start/stop operations
- Check instance state in AWS Console

### Connection Timeout
- Verify security group allows SSH (port 22) from your IP
- Check instance has public IP address
- Wait a few minutes after instance starts for SSH to be ready

### Application Errors
- Check `.env` file is uploaded correctly
- Verify all required environment variables are set
- Check logs on instance: `ssh ... 'cat ~/cascade/cascade.log'`

## Cost Optimization

- Instance automatically shuts down when execution completes (default behavior)
- Use `--no-shutdown` only when you need to keep instance running
- Instance only runs when actively executing Cascade
- Stopped instances only incur EBS storage costs (minimal)

## Security Notes

- AWS credentials stored as environment variables (not in files)
- `.env` file uploaded securely via SCP
- SSH key permissions validated before use
- All sensitive data excluded from code uploads
- Instance auto-shutdown minimizes exposure window

## Instance Details

- **Instance ID**: `i-0547233d79e6016dc`
- **Region**: `us-east-1`
- **Remote User**: `ubuntu`
- **Project Directory**: `~/cascade`

