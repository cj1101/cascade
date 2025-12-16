# Start Cascade program now on EC2 for immediate testing
# Runs round_robin_1 with 5-minute debug intervals

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

# Upload run_and_shutdown.sh if needed
Write-Host "Uploading run_and_shutdown.sh..."
scp -i $sshKey -o StrictHostKeyChecking=no run_and_shutdown.sh "ubuntu@${instanceIP}:~/cascade/"

# Make script executable and run in background
Write-Host "Starting Round Robin 1 with 5-minute intervals in background..."
ssh -i $sshKey -o StrictHostKeyChecking=no "ubuntu@$instanceIP" "cd ~/cascade && chmod +x run_and_shutdown.sh && nohup ./run_and_shutdown.sh > round_robin_test.log 2>&1 &"

Write-Host ""
Write-Host "Program started in background. Instance will shutdown automatically after completion."
Write-Host "To check progress, run: ssh -i $sshKey ubuntu@$instanceIP 'tail -f ~/cascade/round_robin_test.log'"
Write-Host ""

