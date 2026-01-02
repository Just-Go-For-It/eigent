@echo off
REM Eigent Production Startup Script for Windows
REM This script starts the Eigent application in production mode
REM Note: The application must be built first using 'npm run build'

setlocal enabledelayedexpansion

echo ========================================
echo Eigent Production Startup
echo ========================================

REM Get the directory where the script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if built application exists
echo [1/3] Checking for built application...
if not exist "dist" if not exist "dist-electron" (
    echo Error: Application has not been built
    echo Please build the application first using: npm run build
    echo Or use start.bat for development mode
    pause
    exit /b 1
)
echo Built application found

REM Check Node.js
echo [2/3] Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Node.js is not installed
    echo Please install Node.js (version 18-22) from: https://nodejs.org/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('node -v') do set NODE_VERSION=%%i
echo Node.js version: %NODE_VERSION%

REM Start production application
echo [3/3] Starting production application...

if exist "dist-electron\main" (
    echo Starting Electron application...
    echo Press Ctrl+C to stop the application
    echo ========================================
    echo.
    
    if exist "node_modules\.bin\electron.cmd" (
        call node_modules\.bin\electron.cmd dist-electron\main\index.js
    ) else if exist "node_modules\.bin\electron" (
        call node_modules\.bin\electron dist-electron\main\index.js
    ) else (
        echo Error: Electron executable not found
        echo Please install Electron: npm install
        pause
        exit /b 1
    )
) else (
    echo No built Electron app found. Checking for release build...
    
    if exist "release" (
        echo Found release build. Please run the executable from the release directory
        echo Or rebuild using: npm run build
    ) else (
        echo Error: No built application found
        echo Please build the application first: npm run build
        pause
        exit /b 1
    )
)

pause

