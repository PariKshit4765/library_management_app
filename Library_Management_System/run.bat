@echo off
setlocal
cd /d "%~dp0"
title Library Management System

echo ==============================================
echo   Library Management System
echo ==============================================
echo.

rem ---- find Python -------------------------------------------------
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY (
    python --version >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [ERROR] Python 3 was not found on this computer.
    echo.
    echo Please install Python 3.9 or newer from https://www.python.org/downloads/
    echo IMPORTANT: tick "Add python.exe to PATH" on the first installer screen.
    echo Then double-click run.bat again.
    echo.
    pause
    exit /b 1
)

rem ---- create virtual environment (first run only) ------------------
if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    %PY% -m venv venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment.
        pause
        exit /b 1
    )
)

rem ---- install dependencies (first run only) ------------------------
if not exist "venv\.deps_installed" (
    echo [2/3] Installing dependencies ^(needs internet, first run only^)...
    "venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed. Check your internet connection.
        pause
        exit /b 1
    )
    echo done> "venv\.deps_installed"
)

rem ---- create database + sample data (safe to repeat) ---------------
echo [3/3] Preparing database...
"venv\Scripts\python.exe" database.py
if errorlevel 1 (
    echo [ERROR] Database setup failed.
    pause
    exit /b 1
)

echo.
echo Starting server at http://127.0.0.1:5000
echo Login:  admin  /  admin123
echo Keep this window open while using the app. Press Ctrl+C to stop.
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:5000"
"venv\Scripts\python.exe" app.py

echo.
echo Server stopped.
pause
