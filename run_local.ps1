# Run Cascade simulation and webapp simultaneously locally
Set-Location $PSScriptRoot

# Set Python to unbuffered for real-time output
$env:PYTHONUNBUFFERED = "1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cascade Local Development" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please create a virtual environment first:" -ForegroundColor Yellow
    Write-Host "  python -m venv venv" -ForegroundColor Yellow
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Check if Flask is installed (quick dependency check)
$venvPython = (Resolve-Path ".\venv\Scripts\python.exe").Path
$venvPip = (Resolve-Path ".\venv\Scripts\pip.exe").Path

# Check if venv is pointing to wrong location (common issue)
$pyvenvCfg = Join-Path "venv" "pyvenv.cfg"
if (Test-Path $pyvenvCfg) {
    $cfgContent = Get-Content $pyvenvCfg -Raw
    $currentDir = (Get-Location).Path
    if ($cfgContent -match "executable = (.+)" -and $matches[1] -notmatch [regex]::Escape($currentDir)) {
        Write-Host "WARNING: Virtual environment appears to be incorrectly configured." -ForegroundColor Yellow
        Write-Host "The venv was created from a different location. Recreating venv..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force "venv"
        python -m venv venv
        $venvPython = (Resolve-Path ".\venv\Scripts\python.exe").Path
        $venvPip = (Resolve-Path ".\venv\Scripts\pip.exe").Path
        Write-Host "Virtual environment recreated. Installing dependencies..." -ForegroundColor Green
    }
}

$flaskInstalled = & $venvPython -c "import flask" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Dependencies not installed in this venv. Installing from requirements.txt..." -ForegroundColor Yellow
    Write-Host "This may take a few minutes..." -ForegroundColor Gray
    # Ensure we're using the correct pip for this venv
    $pipOutput = & $venvPip install -r requirements.txt 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install dependencies!" -ForegroundColor Red
        Write-Host "Please run manually: .\venv\Scripts\pip.exe install -r requirements.txt" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Dependencies installed successfully!" -ForegroundColor Green
    Write-Host ""
    # Verify Flask is now installed
    $verifyFlask = & $venvPython -c "import flask; print(flask.__file__)" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Flask installation may have failed. Please check manually." -ForegroundColor Yellow
    } else {
        Write-Host "Flask verified: $verifyFlask" -ForegroundColor Green
    }
}

# Parse command line arguments for simulation
$simulationArgs = @()
$webappPort = 5000

# Default simulation arguments
$defaultSimArgs = @("--backend", "--wait-seconds", "600")

# Check for custom arguments
if ($args.Count -gt 0) {
    $simulationArgs = $args
} else {
    $simulationArgs = $defaultSimArgs
}

$simArgsString = $simulationArgs -join " "

Write-Host "Configuration:" -ForegroundColor Green
Write-Host "  Webapp Port: $webappPort" -ForegroundColor Gray
Write-Host "  Simulation Args: $simArgsString" -ForegroundColor Gray
Write-Host ""
Write-Host "Starting Flask webapp in separate window..." -ForegroundColor Green
Write-Host "Starting Cascade simulation in this window..." -ForegroundColor Green
Write-Host ""
Write-Host "Webapp URL: http://localhost:$webappPort" -ForegroundColor Yellow
Write-Host "Press Ctrl+C in this window to stop simulation" -ForegroundColor Yellow
Write-Host "Close the webapp window to stop the webapp" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Flask webapp in a new PowerShell window
$webappScript = @"
Set-Location '$PSScriptRoot'
`$env:PYTHONUNBUFFERED = '1'
`$venvPython = (Resolve-Path '.\venv\Scripts\python.exe').Path
Write-Host 'Cascade Webapp - Running on http://localhost:$webappPort' -ForegroundColor Green
Write-Host 'Press Ctrl+C to stop' -ForegroundColor Yellow
Write-Host ''
& `$venvPython -u 'webapp\app.py'
"@

$webappScriptPath = Join-Path $env:TEMP "cascade_webapp.ps1"
$webappScript | Out-File -FilePath $webappScriptPath -Encoding UTF8

# Start webapp in new window
$webappProcess = Start-Process powershell -ArgumentList "-NoExit", "-File", "`"$webappScriptPath`"" -PassThru

# Wait a moment for webapp to start
Start-Sleep -Seconds 2

# Run simulation in current window
Write-Host "Simulation Output:" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

try {
    # Activate virtual environment and run simulation
    & ".\venv\Scripts\Activate.ps1"
    & $venvPython -u "cascade_main.py" @simulationArgs
} catch {
    Write-Host "Simulation error: $_" -ForegroundColor Red
} finally {
    # Clean up webapp window
    Write-Host ""
    Write-Host "Stopping webapp..." -ForegroundColor Yellow
    try {
        Stop-Process -Id $webappProcess.Id -ErrorAction SilentlyContinue
    } catch {
        Write-Host "Webapp process already stopped" -ForegroundColor Gray
    }
    Remove-Item $webappScriptPath -ErrorAction SilentlyContinue
    Write-Host "Both processes stopped." -ForegroundColor Green
}

