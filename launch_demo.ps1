# GATI Competition 1-Click Demo Launcher (PowerShell)
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host " GATI: GOVERNANCE-READY AI TRAFFIC INTELLIGENCE PLATFORM" -ForegroundColor Green
Write-Host " Nagpur Tier-1 Smart City Adaptive Signal & Proactive Risk Console" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "[1/3] Starting Central FastAPI Backend on http://localhost:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir'; python -m uvicorn central.api.main:app --host 0.0.0.0 --port 8000 --reload"

Start-Sleep -Seconds 3

Write-Host "[2/3] Starting Live City Traffic Simulation & Telemetry Streamer ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir'; python -m simulation.city_simulator --interval 3.0 --speed 1.0"

Start-Sleep -Seconds 2

Write-Host "[3/3] Starting React Operator Dashboard on http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir\frontend'; npm run dev -- --open"

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host " ALL SYSTEMS ONLINE!" -ForegroundColor Green
Write-Host " - Central API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host " - React Dashboard:  http://localhost:5173" -ForegroundColor White
Write-Host " - Pitch Script:     DEMO_SCRIPT.md" -ForegroundColor White
Write-Host " - Pitch Cheat Sheet: PITCH_CHEAT_SHEET.md" -ForegroundColor White
Write-Host "==============================================================================" -ForegroundColor Green
