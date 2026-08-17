@echo off
cd /d "%~dp0"
echo ============================================================
echo AUREUS V3 - TOP DOWN MTF BACKTEST
echo ============================================================
python -m compileall strategy backtest scripts
if errorlevel 1 (
  echo.
  echo Compile failed. Fix the Python errors before running the backtest.
  pause
  exit /b 1
)
echo.
python -m backtest.runner
pause
