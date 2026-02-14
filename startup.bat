@echo off
REM ============================================
REM Arcade Commander - ACLighter Startup Script
REM ============================================

REM Base directory (this script's location)
set BASEDIR=%~dp0

REM Ensure we are running from ArcadeCommander root
cd /d "%BASEDIR%"

echo.
echo ============================================
echo Starting ACLighter...
echo Working directory:
echo %CD%
echo ============================================
echo.

REM Optional: activate virtual environment here
REM call venv\Scripts\activate

REM Start ACLighter
python ACLighter.py

REM If ACLighter exits, keep window open for diagnostics
echo.
echo ACLighter has stopped.
pause
