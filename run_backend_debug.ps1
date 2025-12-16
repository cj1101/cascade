# Run Cascade backend with visible output
Set-Location $PSScriptRoot

# Set Python to unbuffered
$env:PYTHONUNBUFFERED = "1"

Write-Host "Starting Cascade backend mode..." -ForegroundColor Green
Write-Host "Command: python cascade_main.py --backend --no-gemini --wait-seconds 5" -ForegroundColor Yellow
Write-Host ""

# Run Python and capture output in real-time
python -u cascade_main.py --backend --no-gemini --wait-seconds 5

Write-Host ""
Write-Host "Script completed." -ForegroundColor Green
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
