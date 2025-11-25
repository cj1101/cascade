# PowerShell script to upload Cascade codebase to AWS EC2 instance
# Usage: .\deploy_to_aws.ps1 -SSHKey "path\to\key.pem" -InstanceIP "x.x.x.x" -Username "ubuntu"

param(
    [Parameter(Mandatory = $true)]
    [string]$SSHKey,
    
    [Parameter(Mandatory = $true)]
    [string]$InstanceIP,
    
    [Parameter(Mandatory = $false)]
    [string]$Username = "ubuntu"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Cascade Upload Script to AWS EC2 ===" -ForegroundColor Cyan

# Get current directory
$sourceDir = $PSScriptRoot
if (-not $sourceDir) {
    $sourceDir = (Get-Location).Path
}

Write-Host "`nSource directory: $sourceDir" -ForegroundColor Cyan

# Files to exclude
$excludePatterns = @("venv", "__pycache__", "*.png", "desktop.ini", ".git", "*.pyc", ".env")

# Create temporary directory for files to upload
$tempDir = Join-Path $env:TEMP "cascade_aws_upload_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
Write-Host "Created temporary directory: $tempDir" -ForegroundColor Cyan

# Copy files (excluding patterns)
Write-Host "`nPreparing files for upload..." -ForegroundColor Cyan
Get-ChildItem -Path $sourceDir -Recurse | Where-Object {
    $exclude = $false
    foreach ($pattern in $excludePatterns) {
        if ($_.FullName -like "*\$pattern\*" -or $_.Name -like $pattern) {
            $exclude = $true
            break
        }
    }
    return -not $exclude
} | ForEach-Object {
    $relativePath = $_.FullName.Substring($sourceDir.Length + 1)
    $destPath = Join-Path $tempDir $relativePath
    $destDir = Split-Path $destPath -Parent
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    Copy-Item $_.FullName -Destination $destPath -Force
    Write-Host "  Prepared: $relativePath" -ForegroundColor Gray
}

Write-Host "`nFiles prepared. Starting upload..." -ForegroundColor Cyan

# Upload to instance
$remoteDir = "/home/$Username/cascade"

Write-Host "Creating remote directory..." -ForegroundColor Cyan
ssh -i $SSHKey -o StrictHostKeyChecking=no "$Username@$InstanceIP" "mkdir -p $remoteDir" 2>&1 | Out-Null

Write-Host "Uploading files..." -ForegroundColor Cyan
$scpResult = scp -i $SSHKey -r -o StrictHostKeyChecking=no "$tempDir\*" "$Username@$InstanceIP`:$remoteDir/" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "Upload completed successfully!" -ForegroundColor Green
}
else {
    Write-Host "Upload failed!" -ForegroundColor Red
    Write-Host $scpResult -ForegroundColor Red
    Remove-Item -Path $tempDir -Recurse -Force
    exit 1
}

# Clean up temp directory
Remove-Item -Path $tempDir -Recurse -Force
Write-Host "`nTemporary files cleaned up." -ForegroundColor Cyan

# Upload logos directory separately if it exists
$logosDir = "C:\Users\charl\CodingProjets\logos"
if (Test-Path $logosDir) {
    Write-Host "`nUploading logos directory..." -ForegroundColor Cyan
    # Create logos directory on remote
    ssh -i $SSHKey -o StrictHostKeyChecking=no "$Username@$InstanceIP" "mkdir -p $remoteDir/logos" 2>&1 | Out-Null
    # Upload logos to the correct location
    $logosResult = scp -i $SSHKey -r -o StrictHostKeyChecking=no "$logosDir\*" "$Username@$InstanceIP`:$remoteDir/logos/" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Logos uploaded successfully to $remoteDir/logos/" -ForegroundColor Green
    }
    else {
        Write-Host "Logos upload failed (non-critical): $logosResult" -ForegroundColor Yellow
    }
}
else {
    Write-Host "`nWarning: Logos directory not found at $logosDir" -ForegroundColor Yellow
    Write-Host "  Make sure logos are uploaded manually to $remoteDir/logos/ on the AWS instance" -ForegroundColor Yellow
}

Write-Host "`n=== Upload Complete ===" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. SSH into instance: ssh -i `"$SSHKey`" $Username@$InstanceIP" -ForegroundColor White
Write-Host "2. Run setup script: cd cascade && chmod +x setup_aws_instance.sh && ./setup_aws_instance.sh" -ForegroundColor White
