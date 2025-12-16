# Restart Cascade test with updated code
# Uploads changes and restarts the program

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

$instanceId = "i-0547233d79e6016dc"
$region = "us-east-1"
$sshKey = "$env:USERPROFILE\.ssh\aws_cascade"

Write-Host "Checking instance state..."
$instanceState = aws ec2 describe-instances --instance-ids $instanceId --region $region --query 'Reservations[0].Instances[0].State.Name' --output text
Write-Host "Instance state: $instanceState"

if ($instanceState -eq "stopped") {
    Write-Host "Starting instance..."
    aws ec2 start-instances --instance-ids $instanceId --region $region | Out-Null
    Write-Host "Waiting for instance to start..."
    aws ec2 wait instance-running --instance-ids $instanceId --region $region
    Write-Host "Instance is running. Waiting for IP assignment..."
    Start-Sleep -Seconds 15
}

# Get instance IP
$instanceIP = aws ec2 describe-instances --instance-ids $instanceId --region $region --query 'Reservations[0].Instances[0].PublicIpAddress' --output text

if ([string]::IsNullOrEmpty($instanceIP) -or $instanceIP -eq "None") {
    Write-Host "ERROR: Failed to get instance IP"
    exit 1
}

Write-Host "Instance IP: $instanceIP"

# Stop any running cascade processes
Write-Host "Stopping any running cascade processes..."
ssh -i $sshKey -o StrictHostKeyChecking=no "ubuntu@$instanceIP" "pkill -f 'cascade_main.py' || true"

Write-Host "Waiting for processes to stop..."
Start-Sleep -Seconds 5

# Upload updated cascade_main.py
Write-Host "Uploading updated cascade_main.py..."
scp -i $sshKey -o StrictHostKeyChecking=no cascade_main.py "ubuntu@${instanceIP}:~/cascade/"

# Upload run_and_shutdown.sh if needed
Write-Host "Uploading run_and_shutdown.sh..."
scp -i $sshKey -o StrictHostKeyChecking=no run_and_shutdown.sh "ubuntu@${instanceIP}:~/cascade/"

# Reset game state for fresh start (optional - comment out if you want to keep existing state)
Write-Host "Resetting game state for fresh start..."
ssh -i $sshKey -o StrictHostKeyChecking=no "ubuntu@$instanceIP" "cd ~/cascade && mv game_state.json game_state.json.backup 2>/dev/null || true"

# Start the program in background
Write-Host "Starting Round Robin 1 with 5-minute intervals in background..."
ssh -i $sshKey -o StrictHostKeyChecking=no "ubuntu@$instanceIP" "cd ~/cascade && chmod +x run_and_shutdown.sh && nohup ./run_and_shutdown.sh > round_robin_test.log 2>&1 &"

Write-Host ""
Write-Host "Program started in background. Week 1 should post immediately, then 5-minute intervals between weeks."
Write-Host "To check progress, run: ssh -i $sshKey ubuntu@$instanceIP 'tail -f ~/cascade/round_robin_test.log'"
Write-Host ""

