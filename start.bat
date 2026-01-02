@echo off
REM Eigent Development Startup Script for Windows
REM This script starts the Eigent application in development mode

setlocal enabledelayedexpansion

echo ========================================
echo Eigent Development Startup
echo ========================================

REM Get the directory where the script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check Node.js
echo [1/4] Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Node.js is not installed
    echo Please install Node.js (version 18-22) from: https://nodejs.org/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node -v') do set NODE_VERSION=%%i
echo Node.js version: %NODE_VERSION%

REM Check npm
echo [2/4] Checking npm...
where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: npm is not installed
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('npm -v') do set NPM_VERSION=%%i
echo npm version: %NPM_VERSION%

REM Check if node_modules exists
echo [3/4] Checking dependencies...
if not exist "node_modules" (
    echo node_modules not found. Installing dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo Failed to install dependencies
        pause
        exit /b 1
    )
    echo Dependencies installed successfully
) else (
    echo Dependencies already installed
)

REM Start the development server
echo [4/4] Starting development server...
echo The application will start in development mode
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Run the development command
call npm run dev

pause

