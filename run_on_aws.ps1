# PowerShell script to run Cascade on AWS EC2 instance
# Usage: .\run_on_aws.ps1 --mode <mode> [options]
#
# Example: .\run_on_aws.ps1 --mode round_robin_1 --now

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('round_robin_1', 'round_robin_2', 'tournament', 'backend')]
    [string]$Mode,
    
    [switch]$Now,
    [int]$DebugInterval,
    [switch]$NoInstagram,
    [switch]$NoGemini,
    [switch]$NoPodcast,
    [int]$WaitSeconds = 10,
    [switch]$NoShutdown
)

$ErrorActionPreference = "Stop"

# Configuration
$INSTANCE_ID = "i-0547233d79e6016dc"
$REGION = "us-east-1"
$REMOTE_USER = "ubuntu"
$PROJECT_DIR = "~/cascade"

# Load .env file to get KEY_PAIR_LOCATION
$envFile = ".env"
$sshKey = $null

if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match 'KEY_PAIR_LOCATION=(.+)') {
        $sshKey = $matches[1].Trim()
    }
}

# Default SSH key location if not found in .env
if (-not $sshKey -or -not (Test-Path $sshKey)) {
    $defaultKey = "$env:USERPROFILE\.ssh\aws_cascade"
    if (Test-Path $defaultKey) {
        $sshKey = $defaultKey
        Write-Host "Using default SSH key: $sshKey" -ForegroundColor Yellow
    } else {
        Write-Host "ERROR: SSH key not found. Please set KEY_PAIR_LOCATION in .env or ensure key exists at $defaultKey" -ForegroundColor Red
        exit 1
    }
}

# Validate SSH key exists
if (-not (Test-Path $sshKey)) {
    Write-Host "ERROR: SSH key not found at: $sshKey" -ForegroundColor Red
    exit 1
}

# Set SSH key permissions (Windows doesn't enforce, but good practice)
$acl = Get-Acl $sshKey
$acl.SetAccessRuleProtection($true, $false)
Set-Acl -Path $sshKey -AclObject $acl

Write-Host "=== Cascade AWS EC2 Remote Execution ===" -ForegroundColor Cyan
Write-Host "Mode: $Mode" -ForegroundColor Cyan
Write-Host "SSH Key: $sshKey" -ForegroundColor Gray
Write-Host ""

# Check AWS CLI
try {
    $awsVersion = aws --version 2>&1
    Write-Host "AWS CLI: $awsVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: AWS CLI not found. Please install AWS CLI." -ForegroundColor Red
    exit 1
}

# Configure AWS credentials from environment variables
if (-not $env:AWS_CLI_ACCESS_KEY -or -not $env:AWS_CLI_SECRET_KEY) {
    Write-Host "WARNING: AWS_CLI_ACCESS_KEY or AWS_CLI_SECRET_KEY not set in environment." -ForegroundColor Yellow
    Write-Host "Attempting to use existing AWS CLI configuration..." -ForegroundColor Yellow
} else {
    $env:AWS_ACCESS_KEY_ID = $env:AWS_CLI_ACCESS_KEY
    $env:AWS_SECRET_ACCESS_KEY = $env:AWS_CLI_SECRET_KEY
    $env:AWS_DEFAULT_REGION = $REGION
    Write-Host "AWS credentials configured from environment variables" -ForegroundColor Green
}

Write-Host ""
Write-Host "Querying instance state from AWS..." -ForegroundColor Cyan

# Get instance state
try {
    $instanceState = aws ec2 describe-instances `
        --instance-ids $INSTANCE_ID `
        --region $REGION `
        --query 'Reservations[0].Instances[0].State.Name' `
        --output text 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to query instance state. Check AWS credentials and permissions." -ForegroundColor Red
        Write-Host $instanceState -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Instance state: $instanceState" -ForegroundColor Cyan
} catch {
    Write-Host "ERROR: Failed to query instance: $_" -ForegroundColor Red
    exit 1
}

# Start instance if stopped
if ($instanceState -eq "stopped") {
    Write-Host "Instance is stopped. Starting it..." -ForegroundColor Yellow
    try {
        aws ec2 start-instances --instance-ids $INSTANCE_ID --region $REGION | Out-Null
        Write-Host "Waiting for instance to enter running state..." -ForegroundColor Yellow
        aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
        Write-Host "Instance is now running. Waiting for IP assignment..." -ForegroundColor Green
        Start-Sleep -Seconds 15
    } catch {
        Write-Host "ERROR: Failed to start instance: $_" -ForegroundColor Red
        exit 1
    }
} elseif ($instanceState -eq "stopping") {
    Write-Host "Instance is stopping. Waiting for it to stop, then will start it..." -ForegroundColor Yellow
    aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID --region $REGION
    Write-Host "Instance stopped. Starting it..." -ForegroundColor Yellow
    aws ec2 start-instances --instance-ids $INSTANCE_ID --region $REGION | Out-Null
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION
    Write-Host "Instance is now running. Waiting for IP assignment..." -ForegroundColor Green
    Start-Sleep -Seconds 15
} elseif ($instanceState -ne "running") {
    Write-Host "ERROR: Instance is in state '$instanceState'. Cannot proceed." -ForegroundColor Red
    exit 1
}

# Get the current public IP
Write-Host "Getting instance IP address..." -ForegroundColor Cyan
$maxRetries = 5
$retryCount = 0
$instanceIP = $null

while ($retryCount -lt $maxRetries -and (-not $instanceIP -or $instanceIP -eq "None")) {
    try {
        $instanceIP = aws ec2 describe-instances `
            --instance-ids $INSTANCE_ID `
            --region $REGION `
            --query 'Reservations[0].Instances[0].PublicIpAddress' `
            --output text 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            throw "AWS CLI error"
        }
        
        if (-not $instanceIP -or $instanceIP -eq "None") {
            $retryCount++
            if ($retryCount -lt $maxRetries) {
                Write-Host "Waiting for public IP assignment... (attempt $retryCount/$maxRetries)" -ForegroundColor Yellow
                Start-Sleep -Seconds 10
            }
        }
    } catch {
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host "Error getting IP, retrying... (attempt $retryCount/$maxRetries)" -ForegroundColor Yellow
            Start-Sleep -Seconds 10
        }
    }
}

if (-not $instanceIP -or $instanceIP -eq "None") {
    Write-Host "ERROR: Failed to get public IP after $maxRetries attempts. Check instance in AWS Console." -ForegroundColor Red
    exit 1
}

Write-Host "Instance IP: $instanceIP" -ForegroundColor Green
Write-Host ""

# Wait for SSH to be available
Write-Host "Waiting for SSH to be available..." -ForegroundColor Cyan
$sshAvailable = $false
$sshRetries = 30
$sshRetryCount = 0

while (-not $sshAvailable -and $sshRetryCount -lt $sshRetries) {
    try {
        $testConnection = ssh -i $sshKey -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$REMOTE_USER@$instanceIP" "echo 'SSH ready'" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $sshAvailable = $true
            Write-Host "SSH connection established" -ForegroundColor Green
        } else {
            $sshRetryCount++
            if ($sshRetryCount -lt $sshRetries) {
                Start-Sleep -Seconds 2
            }
        }
    } catch {
        $sshRetryCount++
        if ($sshRetryCount -lt $sshRetries) {
            Start-Sleep -Seconds 2
        }
    }
}

if (-not $sshAvailable) {
    Write-Host "ERROR: SSH connection failed after $sshRetries attempts" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Create project directory on remote
Write-Host "Creating project directory on remote instance..." -ForegroundColor Cyan
ssh -i $sshKey -o StrictHostKeyChecking=no "$REMOTE_USER@$instanceIP" "mkdir -p $PROJECT_DIR" 2>&1 | Out-Null

# Upload code (excluding venv, __pycache__, .git, .env, *.png)
Write-Host "Uploading codebase to instance..." -ForegroundColor Cyan
$excludePatterns = @(
    '--exclude=venv',
    '--exclude=__pycache__',
    '--exclude=.git',
    '--exclude=.env',
    '--exclude=*.png',
    '--exclude=*.pyc',
    '--exclude=desktop.ini',
    '--exclude=.cursor'
)

$rsyncArgs = @(
    '-avz',
    '-e', "ssh -i `"$sshKey`" -o StrictHostKeyChecking=no"
) + $excludePatterns + @(
    './',
    "$REMOTE_USER@${instanceIP}:$PROJECT_DIR/"
)

# Check if rsync is available, otherwise use scp
$rsyncAvailable = $false
try {
    $rsyncVersion = rsync --version 2>&1
    $rsyncAvailable = $true
} catch {
    $rsyncAvailable = $false
}

if ($rsyncAvailable) {
    Write-Host "Using rsync for file transfer..." -ForegroundColor Gray
    & rsync @rsyncArgs 2>&1 | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
} else {
    Write-Host "rsync not available, using SCP for file transfer..." -ForegroundColor Yellow
    Write-Host "This may take longer. Consider installing rsync for better performance." -ForegroundColor Yellow
    
    # Create temp directory for files to upload
    $tempDir = Join-Path $env:TEMP "cascade_aws_upload_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    
    # Copy files excluding patterns
    Get-ChildItem -Path . -Recurse -File | Where-Object {
        $exclude = $false
        $excludePatterns = @('venv', '__pycache__', '.git', '.env', '.png', '.pyc', 'desktop.ini', '.cursor')
        foreach ($pattern in $excludePatterns) {
            if ($_.FullName -like "*\$pattern\*" -or $_.Name -like "*$pattern*") {
                $exclude = $true
                break
            }
        }
        return -not $exclude
    } | ForEach-Object {
        $relativePath = $_.FullName.Substring((Get-Location).Path.Length + 1)
        $destPath = Join-Path $tempDir $relativePath
        $destDir = Split-Path $destPath -Parent
        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
        Copy-Item $_.FullName -Destination $destPath -Force
    }
    
    # Upload via SCP
    scp -i $sshKey -r -o StrictHostKeyChecking=no "$tempDir\*" "$REMOTE_USER@${instanceIP}:$PROJECT_DIR/" 2>&1 | Out-Null
    
    # Cleanup
    Remove-Item -Path $tempDir -Recurse -Force
}

# Upload .env file separately and securely
if (Test-Path $envFile) {
    Write-Host "Uploading .env file..." -ForegroundColor Cyan
    scp -i $sshKey -o StrictHostKeyChecking=no $envFile "$REMOTE_USER@${instanceIP}:$PROJECT_DIR/.env" 2>&1 | Out-Null
    Write-Host ".env file uploaded" -ForegroundColor Green
} else {
    Write-Host "WARNING: .env file not found. Application may not have required credentials." -ForegroundColor Yellow
}

Write-Host ""

# Setup Python environment on remote
Write-Host "Setting up Python environment on remote instance..." -ForegroundColor Cyan
$setupCommands = @"
cd $PROJECT_DIR
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "Installing/updating dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "Python environment ready"
"@

ssh -i $sshKey -o StrictHostKeyChecking=no "$REMOTE_USER@$instanceIP" $setupCommands 2>&1 | ForEach-Object {
    Write-Host $_ -ForegroundColor Gray
}

Write-Host ""

# Build command arguments for Cascade
$cascadeArgs = @()
if ($Now) {
    $cascadeArgs += "--now"
}
if ($DebugInterval) {
    $cascadeArgs += "--debug-interval"
    $cascadeArgs += $DebugInterval.ToString()
}
if ($NoInstagram) {
    $cascadeArgs += "--no-instagram"
}
if ($NoGemini) {
    $cascadeArgs += "--no-gemini"
}
if ($NoPodcast) {
    $cascadeArgs += "--no-podcast"
}
if ($Mode -eq "backend") {
    $cascadeArgs += "--backend"
    $cascadeArgs += "--wait-seconds"
    $cascadeArgs += $WaitSeconds.ToString()
} else {
    $cascadeArgs += "--mode"
    $cascadeArgs += $Mode
}

# Create remote execution script
$logFile = "$PROJECT_DIR/cascade.log"
$remoteScript = @"
#!/bin/bash
set -e
cd $PROJECT_DIR
source venv/bin/activate

# Log to file and stdout
exec > >(tee -a "$logFile") 2>&1

echo "=========================================="
echo "Cascade Remote Execution"
echo "Mode: $Mode"
echo "Start time: \$(date)"
echo "Working directory: \$(pwd)"
echo "=========================================="

# Run Cascade
python cascade_main.py $($cascadeArgs -join ' ')

EXIT_CODE=\$?

echo ""
echo "=========================================="
echo "Cascade execution completed at: \$(date)"
echo "Exit code: \$EXIT_CODE"
echo "=========================================="
"@

if (-not $NoShutdown) {
    $remoteScript += @"

echo "Shutting down instance..."
sudo shutdown -h now
"@
} else {
    $remoteScript += @"

echo "Instance will remain running (--no-shutdown specified)"
"@
}

# Upload remote script
$remoteScriptPath = Join-Path $env:TEMP "remote_run_cascade_$(Get-Date -Format 'yyyyMMdd_HHmmss').sh"
$remoteScript | Out-File -FilePath $remoteScriptPath -Encoding ASCII -NoNewline

scp -i $sshKey -o StrictHostKeyChecking=no $remoteScriptPath "$REMOTE_USER@${instanceIP}:$PROJECT_DIR/remote_run_cascade.sh" 2>&1 | Out-Null

# Make script executable and run it
Write-Host "Starting Cascade execution on remote instance..." -ForegroundColor Cyan
Write-Host "Command: python cascade_main.py $($cascadeArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

Write-Host "To monitor progress in real-time, run:" -ForegroundColor Cyan
Write-Host "  ssh -i `"$sshKey`" $REMOTE_USER@$instanceIP 'tail -f $PROJECT_DIR/cascade.log'" -ForegroundColor White
Write-Host ""

if ($NoShutdown) {
    Write-Host "Running in foreground (instance will remain running)..." -ForegroundColor Yellow
    Write-Host "Press Ctrl+C to disconnect (execution will continue on instance)" -ForegroundColor Yellow
    Write-Host ""
    ssh -i $sshKey -o StrictHostKeyChecking=no "$REMOTE_USER@$instanceIP" "cd $PROJECT_DIR && chmod +x remote_run_cascade.sh && ./remote_run_cascade.sh"
} else {
    Write-Host "Running in background. Instance will shutdown automatically when complete." -ForegroundColor Yellow
    Write-Host ""
    
    # Run in background (script handles its own logging)
    ssh -i $sshKey -o StrictHostKeyChecking=no "$REMOTE_USER@$instanceIP" "cd $PROJECT_DIR && chmod +x remote_run_cascade.sh && nohup ./remote_run_cascade.sh > /dev/null 2>&1 &"
    
    Write-Host "Execution started in background." -ForegroundColor Green
    Write-Host "Instance will automatically shutdown when Cascade completes." -ForegroundColor Green
    Write-Host "You can safely close this terminal." -ForegroundColor Green
}

# Cleanup local temp file
Remove-Item -Path $remoteScriptPath -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green

