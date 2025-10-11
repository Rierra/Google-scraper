@echo off
echo ========================================
echo Google Rank Tracker - Local Setup
echo ========================================
echo.
echo Installing required packages...
echo.

pip install -r local_requirements.txt

echo.
echo ========================================
echo Setup complete!
echo.
echo To start the local scraper, run:
echo   start_scraper.bat
echo.
echo Or manually run:
echo   python start_local_scraper.py
echo ========================================
echo.

pause
