#!/bin/bash

# Eigent Production Startup Script
# This script starts the Eigent application in production mode
# Note: The application must be built first using 'npm run build'

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${GREEN}========================================"
echo -e "Eigent Production Startup"
echo -e "========================================${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if built application exists
echo -e "${YELLOW}[1/3] Checking for built application...${NC}"
if [ ! -d "dist" ] && [ ! -d "dist-electron" ]; then
    echo -e "${RED}Error: Application has not been built${NC}"
    echo -e "${CYAN}Please build the application first using: npm run build${NC}"
    echo -e "${CYAN}Or use start.sh for development mode${NC}"
    exit 1
fi
echo -e "${GREEN}Built application found${NC}"

# Check Node.js
echo -e "${YELLOW}[2/3] Checking Node.js...${NC}"
if ! command_exists node; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    echo -e "${CYAN}Please install Node.js (version 18-22) from: https://nodejs.org/${NC}"
    exit 1
fi
echo -e "${GREEN}Node.js version: $(node -v)${NC}"

# Check if electron executable exists
echo -e "${YELLOW}[3/3] Starting production application...${NC}"

# Try to find the built Electron app
if [ -d "dist-electron/main" ]; then
    echo -e "${CYAN}Starting Electron application...${NC}"
    echo -e "${CYAN}Press Ctrl+C to stop the application${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    # Check if electron is installed
    if [ -d "node_modules/.bin" ] && [ -f "node_modules/.bin/electron" ]; then
        ./node_modules/.bin/electron dist-electron/main/index.js
    elif command_exists electron; then
        electron dist-electron/main/index.js
    else
        echo -e "${RED}Error: Electron executable not found${NC}"
        echo -e "${CYAN}Please install Electron: npm install${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}No built Electron app found. Checking for release build...${NC}"
    
    # Check for release build (created by electron-builder)
    if [ -d "release" ]; then
        echo -e "${CYAN}Found release build. Please run the executable from the release directory${NC}"
        echo -e "${CYAN}Or rebuild using: npm run build${NC}"
    else
        echo -e "${RED}Error: No built application found${NC}"
        echo -e "${CYAN}Please build the application first: npm run build${NC}"
        exit 1
    fi
fi

