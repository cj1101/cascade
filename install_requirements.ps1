# PowerShell script to install requirements and verify Pillow installation
Write-Host "Installing requirements from requirements.txt..." -ForegroundColor Cyan
python -m pip install -r requirements.txt

Write-Host "`nVerifying Pillow installation..." -ForegroundColor Cyan
python -c "from PIL import Image; print('✓ Pillow is installed successfully!'); print(f'  Version: {Image.__version__ if hasattr(Image, \"__version__\") else \"unknown\"}')"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ All requirements installed successfully!" -ForegroundColor Green
} else {
    Write-Host "`n✗ Installation or verification failed. Please check the output above." -ForegroundColor Red
    exit 1
}
