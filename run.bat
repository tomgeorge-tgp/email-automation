@echo off
setlocal EnableDelayedExpansion
title Bulk Email Sender

echo.
echo  ===========================================
echo    Bulk Email Sender  ^|  Azure ACS
echo  ===========================================
echo.

REM ── Locate uv ──────────────────────────────────────────────────────────────
set UV=
if exist "%~dp0uv.exe"      set UV=%~dp0uv.exe
if "%UV%"=="" where uv >nul 2>&1 && set UV=uv

if "%UV%"=="" (
    echo  [ERROR] uv.exe not found.
    echo  Download it from https://github.com/astral-sh/uv/releases
    echo  and place it in the same folder as this script.
    echo.
    pause
    exit /b 1
)

REM ── First-run: configure .env ───────────────────────────────────────────────
if not exist "%~dp0.env" (
    if not exist "%~dp0.env.example" (
        echo  [ERROR] .env.example is missing.
        pause
        exit /b 1
    )
    copy "%~dp0.env.example" "%~dp0.env" >nul
    echo  First-time setup detected.
    echo  Your Azure credentials are required to send emails.
    echo.
    echo  Opening .env in Notepad — fill in:
    echo    ACS_CONNECTION_STRING
    echo    ACS_SENDER_EMAIL
    echo.
    echo  Save and close Notepad, then press any key to continue.
    echo.
    notepad "%~dp0.env"
    pause >nul
)

REM ── Sync dependencies ──────────────────────────────────────────────────────
echo  Checking dependencies...
cd /d "%~dp0"
"%UV%" sync --quiet
if errorlevel 1 (
    echo.
    echo  [ERROR] Dependency install failed.
    echo  Make sure you have an internet connection for the first run.
    pause
    exit /b 1
)

REM ── Kill anything already on the ports ─────────────────────────────────────
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":9000 "') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8501 "') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM ── Start backend ──────────────────────────────────────────────────────────
echo  Starting backend  ^(http://localhost:9000^)...
start "Email Sender - Backend" /B "%UV%" run uvicorn main:app --host 0.0.0.0 --port 9000

REM ── Wait briefly then open browser ────────────────────────────────────────
timeout /t 2 >nul
echo  Opening browser at http://localhost:8501 ...
start http://localhost:8501

REM ── Start frontend (blocks until user closes the window) ──────────────────
echo  Starting frontend  ^(http://localhost:8501^)...
echo.
echo  Close this window to stop the application.
echo.
"%UV%" run streamlit run app.py ^
    --server.address=0.0.0.0 ^
    --server.port=8501 ^
    --server.headless=true ^
    --browser.gatherUsageStats=false

REM ── Cleanup on exit ────────────────────────────────────────────────────────
echo.
echo  Shutting down backend...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":9000 "') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo  Done.
