@echo off
TITLE GATI - Governance-ready AI Traffic Intelligence Platform (1-Click Competition Launcher)
COLOR 0A

echo ==============================================================================
echo  GATI: GOVERNANCE-READY AI TRAFFIC INTELLIGENCE PLATFORM
echo  Nagpur Tier-1 Smart City Adaptive Signal & Proactive Risk Console
echo ==============================================================================
echo.

echo [1/3] Starting Central FastAPI Backend on http://localhost:8000 ...
start "GATI Backend API" cmd /k "cd /d %~dp0 && python -m uvicorn central.api.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo [2/3] Starting Live City Traffic Simulation & Telemetry Streamer ...
start "GATI City Traffic Streamer" cmd /k "cd /d %~dp0 && python -m simulation.city_simulator --interval 3.0 --speed 1.0"

timeout /t 2 /nobreak >nul

echo [3/3] Starting React Operator Dashboard on http://localhost:5173 ...
start "GATI Operator Dashboard" cmd /k "cd /d %~dp0\frontend && npm run dev -- --open"

echo.
echo ==============================================================================
echo  ALL SYSTEMS ONLINE!
echo  - Central API Docs: http://localhost:8000/docs
echo  - React Dashboard:  http://localhost:5173
echo  - Pitch Script:     DEMO_SCRIPT.md
echo  - Pitch Cheat Sheet: PITCH_CHEAT_SHEET.md
echo ==============================================================================
echo.
pause
