# Script to check if AWS instance is up and restart the cascade script
$sshKey = "$env:USERPROFILE\.ssh\aws_cascade"
$instanceId = "i-0547233d79e6016dc"
$region = "us-east-1"

Write-Host "Querying instance status from AWS..." -ForegroundColor Cyan

# Get instance state
$instanceState = aws ec2 describe-instances `
    --instance-ids $instanceId `
    --region $region `
    --query 'Reservations[0].Instances[0].State.Name' `
    --output text

Write-Host "Instance state: $instanceState"

if ($instanceState -eq "stopped") {
    Write-Host "Instance is stopped. Starting it..." -ForegroundColor Yellow
    aws ec2 start-instances --instance-ids $instanceId --region $region | Out-Null
    Write-Host "Waiting for instance to enter running state..."
    aws ec2 wait instance-running --instance-ids $instanceId --region $region
    Write-Host "Instance is now running. Waiting for IP assignment..." -ForegroundColor Green
    Start-Sleep -Seconds 10
}

# Get the current public IP of the instance
$instanceIP = aws ec2 describe-instances `
    --instance-ids $instanceId `
    --region $region `
    --query 'Reservations[0].Instances[0].PublicIpAddress' `
    --output text

if (-not $instanceIP -or $instanceIP -eq "None") {
    Write-Host "No public IP assigned yet. Waiting..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15
    $instanceIP = aws ec2 describe-instances `
        --instance-ids $instanceId `
        --region $region `
        --query 'Reservations[0].Instances[0].PublicIpAddress' `
        --output text
}

if (-not $instanceIP -or $instanceIP -eq "None") {
    Write-Host "Failed to get public IP. Please check the instance in AWS Console." -ForegroundColor Red
    exit 1
}

Write-Host "Instance IP: $instanceIP" -ForegroundColor Green
Write-Host ""

$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    Write-Host "Attempt $attempt / $maxAttempts : Checking SSH connection..."
    
    try {
        $result = ssh -i $sshKey -o StrictHostKeyChecking=no -o ConnectTimeout=5 "ubuntu@$instanceIP" "echo Connected" 2>&1
        if ($result -match "Connected") {
            Write-Host "Instance is accessible!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Restarting the cascade script..."
            
            # Restart the script
            ssh -i $sshKey -o StrictHostKeyChecking=no "ubuntu@$instanceIP" "cd ~/cascade; nohup ./run_and_shutdown.sh > round_robin.log 2>&1 &"
            
            Start-Sleep -Seconds 3
            
            Write-Host "Checking initial output..."
            ssh -i $sshKey -o StrictHostKeyChecking=no "ubuntu@$instanceIP" "tail -30 ~/cascade/round_robin.log"
            
            Write-Host ""
            Write-Host "Script restarted! Monitor with:" -ForegroundColor Green
            Write-Host "ssh -i `$sshKey -o StrictHostKeyChecking=no ubuntu@$instanceIP 'tail -f ~/cascade/round_robin.log'" -ForegroundColor Yellow
            break
        }
    } catch {
        Write-Host "  Not accessible yet, waiting 10 seconds..."
        Start-Sleep -Seconds 10
    }
    
    if ($attempt -lt $maxAttempts) {
        Write-Host "  Not accessible yet, waiting 10 seconds..."
        Start-Sleep -Seconds 10
    }
}

if ($attempt -eq $maxAttempts) {
    Write-Host ""
    Write-Host "Instance still not accessible after $maxAttempts attempts." -ForegroundColor Red
    Write-Host "Please check:" -ForegroundColor Yellow
    Write-Host "1. Security groups allow SSH (port 22) from your IP"
    Write-Host "2. Instance has finished booting (can take 1-2 minutes)"
}
