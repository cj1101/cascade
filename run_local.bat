@echo off
REM Run Cascade simulation and webapp simultaneously locally
cd /d "%~dp0"

echo ========================================
echo Cascade Local Development
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo ERROR: Virtual environment not found!
    echo Please create a virtual environment first:
    echo   python -m venv venv
    echo   venv\Scripts\activate.bat
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if Flask is installed (quick dependency check)
venv\Scripts\python.exe -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Dependencies not installed. Installing from requirements.txt...
    echo This may take a few minutes...
    venv\Scripts\pip.exe install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies!
        echo Please run manually: venv\Scripts\pip.exe install -r requirements.txt
        pause
        exit /b 1
    )
    echo Dependencies installed successfully!
    echo.
)

REM Set default simulation arguments
set SIM_ARGS=--backend --wait-seconds 5

REM Allow override via command line
if not "%1"=="" set SIM_ARGS=%*

echo Starting Flask webapp in separate window...
echo Starting Cascade simulation in this window...
echo.
echo Webapp URL: http://localhost:5000
echo Press Ctrl+C to stop simulation
echo Close the webapp window to stop the webapp
echo.
echo ========================================
echo.

REM Start Flask webapp in a new window
start "Cascade Webapp" cmd /k "cd /d %~dp0 && set PYTHONUNBUFFERED=1 && venv\Scripts\python.exe -u webapp\app.py"

REM Wait a moment for webapp to start
timeout /t 2 /nobreak >nul

REM Run simulation in current window
echo Simulation Output:
echo ----------------------------------------
echo.

REM Activate virtual environment and run simulation
call venv\Scripts\activate.bat
python -u cascade_main.py %SIM_ARGS%

echo.
echo Both processes stopped.
pause

