# Startup Scripts Summary

## Overview

I've created comprehensive startup scripts to make it easy to run the Eigent application. The scripts handle all prerequisites, dependency installation, and startup automatically.

## Created Files

### Development Scripts
- **`start.sh`** - macOS/Linux development startup script
- **`start.bat`** - Windows development startup script

### Production Scripts
- **`start-production.sh`** - macOS/Linux production startup script
- **`start-production.bat`** - Windows production startup script

### Documentation
- **`STARTUP.md`** - Comprehensive startup guide with troubleshooting
- **`README.md`** - Updated to reference the new startup scripts

## Quick Usage

### Development
```bash
# macOS/Linux
./start.sh

# Windows
start.bat
```

### Production
```bash
# First build the app
npm run build

# Then run
# macOS/Linux
./start-production.sh

# Windows
start-production.bat
```

## What the Scripts Do

### Development Scripts (`start.sh` / `start.bat`)
1. ✅ Check Node.js version (18-22)
2. ✅ Check npm installation
3. ✅ Install dependencies if needed (`npm install`)
4. ✅ Start development server (`npm run dev`)

### Production Scripts (`start-production.sh` / `start-production.bat`)
1. ✅ Verify application has been built
2. ✅ Check Node.js installation
3. ✅ Start the built Electron application

## Application Architecture

The Eigent application consists of:
- **Frontend**: React/TypeScript (Vite) - Auto-started by scripts
- **Electron**: Desktop wrapper - Auto-started by scripts
- **Backend**: Python FastAPI - Auto-started by Electron on port 5001

## Key Features

✅ **Automatic Prerequisites Check** - Verifies Node.js and npm versions
✅ **Automatic Dependency Installation** - Installs npm packages if needed
✅ **Error Handling** - Clear error messages with solutions
✅ **Cross-Platform** - Works on macOS, Linux, and Windows
✅ **Production Ready** - Separate scripts for production builds

## Troubleshooting

Common issues and solutions are documented in `STARTUP.md`.

## Next Steps

1. Test the scripts on your system:
   ```bash
   ./start.sh  # or start.bat on Windows
   ```

2. If you encounter issues, check:
   - Node.js version (should be 18-22)
   - Network connection (for dependency downloads)
   - Port availability (backend uses port 5001+)

3. For production builds:
   ```bash
   npm run build
   ./start-production.sh  # or start-production.bat
   ```

## Notes

- The backend Python service is automatically managed by Electron
- Dependencies (`uv`, `bun`, Python) are automatically installed by the app
- The scripts are designed to be idempotent (safe to run multiple times)

