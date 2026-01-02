#!/bin/bash

# Eigent Development Startup Script
# This script starts the Eigent application in development mode

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
echo -e "Eigent Development Startup"
echo -e "========================================${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Node.js
echo -e "${YELLOW}[1/4] Checking Node.js...${NC}"
if ! command_exists node; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    echo -e "${CYAN}Please install Node.js (version 18-22) from: https://nodejs.org/${NC}"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ] || [ "$NODE_VERSION" -gt 22 ]; then
    echo -e "${YELLOW}Warning: Node.js version should be 18-22. Current: $(node -v)${NC}"
else
    echo -e "${GREEN}Node.js version: $(node -v)${NC}"
fi

# Check npm
echo -e "${YELLOW}[2/4] Checking npm...${NC}"
if ! command_exists npm; then
    echo -e "${RED}Error: npm is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}npm version: $(npm -v)${NC}"

# Check if node_modules exists
echo -e "${YELLOW}[3/4] Checking dependencies...${NC}"
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}node_modules not found. Installing dependencies...${NC}"
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install dependencies${NC}"
        exit 1
    fi
    echo -e "${GREEN}Dependencies installed successfully${NC}"
else
    echo -e "${GREEN}Dependencies already installed${NC}"
fi

# Start the development server
echo -e "${YELLOW}[4/4] Starting development server...${NC}"
echo -e "${CYAN}The application will start in development mode${NC}"
echo -e "${CYAN}Press Ctrl+C to stop the server${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Run the development command
npm run dev

