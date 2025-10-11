@echo off
echo ========================================
echo Google Rank Tracker - Local Processor
echo ========================================
echo.
echo Starting CONTINUOUS mode...
echo Backend: https://google-scraper-1.onrender.com
echo Frontend: https://google-scraper-frontend.onrender.com
echo.
echo Script will stay running and wait for triggers from website.
echo Press Ctrl+C to stop.
echo ========================================
echo.

python start_local_scraper.py

pause
