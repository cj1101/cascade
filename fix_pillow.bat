@echo off
echo Installing Pillow...
python -m pip install pillow
echo.
echo Testing import...
python -c "from PIL import Image; print('Pillow is working!')"
echo.
echo If you see 'Pillow is working!' above, the installation was successful.
pause
