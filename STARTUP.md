# Eigent Application Startup Guide

This guide explains how to start the Eigent application using the provided startup scripts.

## Prerequisites

Before running the application, ensure you have:

- **Node.js** (version 18-22) - [Download](https://nodejs.org/)
- **npm** (comes with Node.js)

The application will automatically handle:
- Python backend setup (via `uv` package manager)
- Dependency installation
- Backend service startup

## Quick Start

### Development Mode

**macOS/Linux:**
```bash
./start.sh
```

**Windows:**
```batch
start.bat
```

This will:
1. Check prerequisites (Node.js, npm)
2. Install dependencies if needed
3. Start the development server with hot-reload
4. Automatically start the Electron app

### Production Mode

First, build the application:
```bash
npm run build
```

Then start it:

**macOS/Linux:**
```bash
./start-production.sh
```

**Windows:**
```batch
start-production.bat
```

## Manual Startup

If you prefer to start manually:

### Development
```bash
npm install          # Install dependencies (first time only)
npm run dev          # Start development server
```

### Production
```bash
npm install          # Install dependencies
npm run build        # Build the application
npm run preview      # Preview the built application
```

## Application Architecture

The Eigent application consists of:

1. **Frontend**: React/TypeScript application (Vite)
2. **Electron**: Desktop application wrapper
3. **Backend**: Python FastAPI service (auto-started by Electron)
   - Located in `backend/` directory
   - Uses `uv` package manager
   - Runs on port 5001 (or next available port)

## Troubleshooting

### Port Already in Use

If you see an error about a port being in use:

1. The backend automatically finds an available port (starting from 5001)
2. If issues persist, check for running processes:
   ```bash
   # macOS/Linux
   lsof -i :5001
   kill -9 <PID>
   
   # Windows
   netstat -ano | findstr :5001
   taskkill /PID <PID> /F
   ```

### Dependencies Not Installing

If dependencies fail to install:

1. Clear npm cache:
   ```bash
   npm cache clean --force
   ```

2. Remove node_modules and reinstall:
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

### Backend Not Starting

The backend is automatically managed by Electron. If it fails to start:

1. Check Electron logs (usually in `~/.eigent/logs/` on macOS/Linux)
2. Ensure Python 3.10 is available (the app will install it via `uv`)
3. Check that `uv` and `bun` are installed (the app will install them automatically)

### Build Errors

If you encounter build errors:

1. Ensure all dependencies are installed:
   ```bash
   npm install
   ```

2. Check Node.js version (should be 18-22):
   ```bash
   node -v
   ```

3. Clear build cache:
   ```bash
   npm run clean-cache
   ```

## Script Details

### Development Scripts (`start.sh` / `start.bat`)

- Checks Node.js and npm versions
- Installs dependencies if needed
- Starts Vite development server
- Opens Electron app with hot-reload

### Production Scripts (`start-production.sh` / `start-production.bat`)

- Verifies the application has been built
- Checks Node.js installation
- Starts the built Electron application
- Requires `npm run build` to be run first

## Additional Commands

- `npm run build` - Build for production
- `npm run build:mac` - Build macOS app
- `npm run build:win` - Build Windows app
- `npm run test` - Run tests
- `npm run type-check` - TypeScript type checking

## Server Mode (Self-Hosting)

If you want to run the server separately (for self-hosting):

See `server/README_EN.md` for detailed instructions.

Quick start:
```bash
cd server
./start_server.sh    # macOS/Linux
start_server.bat     # Windows
```

## Support

For more information:
- [Main README](./README.md)
- [Server Documentation](./server/README_EN.md)
- [GitHub Issues](https://github.com/eigent-ai/eigent/issues)

