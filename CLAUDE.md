# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

Eigent is a multi-agent workforce desktop application built on [CAMEL-AI](https://github.com/camel-ai/camel). It runs as an Electron app where a React/TypeScript renderer communicates with a locally spawned Python FastAPI backend. Users build, manage, and deploy AI agent workforces that execute complex tasks in parallel.

## Commands

### Frontend / Electron

```bash
npm install
npm run dev          # Start Electron app with Vite dev server (also starts the Python backend)
npm test             # Run all unit tests (Vitest, jsdom environment)
npm run test:watch   # Vitest in watch mode
npm run type-check   # TypeScript type checking only (no emit)
npm run clean-cache  # Clear Vite cache (run before dev if stale)
```

Run a single test file:
```bash
npx vitest run test/unit/store/chatStore.test.ts
```

### Backend (Python)

```bash
cd backend
uv run uvicorn main:api --port 5001   # Start backend standalone
uv run pytest                          # Run all backend tests
uv run pytest tests/unit/             # Run unit tests only
uv run pytest --fast-test-mode        # Skip LLM-dependent tests
uv run pytest --full-test-mode        # Run everything including very slow tests
```

Backend requires **Python 3.10.x** (see `backend/.python-version`). `uv` handles the virtualenv.

### Building Distributables

```bash
npm run build:mac    # macOS only
npm run build:win    # Windows only
npm run build:all    # macOS + Windows
```

### Self-hosted Local Server (optional, separate from the embedded backend)

```bash
cd server
cp .env.example .env
docker compose up -d   # Starts FastAPI + PostgreSQL on port 3001
```

To use it, set in `.env.development`:
```
VITE_USE_LOCAL_PROXY=true
VITE_PROXY_URL=http://localhost:3001
```

## Architecture

### Process Model

Electron spawns two processes at startup:
1. **Main process** (`electron/main/index.ts`): manages window lifecycle, spawns the Python backend as a child process, handles IPC from the renderer, manages the browser WebView for agent browsing tasks, and writes a PID file at `backend/runtime/run.pid`.
2. **Renderer process** (React app): communicates with the main process via the preload bridge (`window.ipcRenderer` / `window.electronAPI`), and communicates with the Python backend over HTTP/SSE at `http://localhost:{backendPort}` (port retrieved via `ipcRenderer.invoke('get-backend-port')`).

The preload bridge is defined in `electron/preload/index.ts` and typed in `src/types/electron.d.ts`. All Electron APIs are accessed through `window.electronAPI` or `window.ipcRenderer` — never import Electron directly in renderer code.

### Backend Request Flow

`src/api/http.ts` is the single fetch wrapper for all backend calls. It lazily resolves the backend port once via `ipcRenderer.invoke('get-backend-port')` and caches it. For SSE streaming (task execution), the frontend uses `@microsoft/fetch-event-source` against `/chat`.

Real-time task state updates are streamed from the backend as SSE events with a typed `Action` enum (defined in `backend/app/service/task.py`). Key actions: `task_state`, `new_task_state`, `decompose_progress`, `create_agent`, `activate_agent`, `assign_task`, `terminal`, `write_file`, `ask`, `end`.

### State Management Pattern

The app uses **Zustand** with a two-level store hierarchy:

- **`projectStore`** (`src/store/projectStore.ts`): Top-level store. Each project contains multiple **vanilla** (non-hook) `ChatStore` instances keyed by chat ID. One chat store per active task.
- **`chatStore`** (`src/store/chatStore.ts`): Per-task state — messages, task info, agents, file list, status, SSE WebView URLs, etc. Created via `createStore` (vanilla) and accessed through `useChatStoreAdapter`.
- **`authStore`** (`src/store/authStore.ts`): Persisted. Holds user token, model preferences (`cloud`/`local`/`custom`), and worker list data.
- **`globalStore`** / **`sidebarStore`** / **`installationStore`**: Minor persisted UI state.

Because `chatStore` is a vanilla (non-hook) Zustand store, components must use `useChatStoreAdapter` (`src/hooks/useChatStoreAdapter.tsx`) to subscribe reactively. Direct `chatStore.getState()` calls work outside React components.

### Backend: CAMEL Integration

The core agent execution lives in `backend/app/service/chat_service.py`. It:
1. Instantiates `Workforce` (subclass of CAMEL's `Workforce` in `backend/app/utils/workforce.py`).
2. Adds `SingleAgentWorker` instances backed by `ListenChatAgent` (subclass of CAMEL's `ChatAgent` in `backend/app/utils/agent.py`).
3. The pre-defined agent types (`search_agent`, `developer_agent`, `document_agent`, `multi_modal_agent`, etc.) are factory functions in `agent.py`.
4. Each `ListenChatAgent` emits SSE events by calling `get_task_lock(api_task_id).put_queue(ActionXxx(...))`.

The `TaskLock` (in `backend/app/service/task.py`) is the coordination primitive between the SSE streaming endpoint and the async CAMEL task execution loop. All inter-process signals (pause, resume, stop, human input, add agent) flow through its asyncio `Queue`.

### Environment / API Keys

User-specific settings are stored at `~/.eigent/<email>/.env`. The backend uses thread-local storage (`_thread_local.env_path` in `backend/app/component/environment.py`) so each request can load its own dotenv without interfering with other concurrent users. The `env()` helper reads from this thread-local path.

MCP server configs are stored at `~/.eigent/<email>/mcp_config.json`.

### Routing and Auth

React Router is configured in `src/routers/index.tsx`. All routes except `/login` and `/signup` are guarded by `ProtectedRoute`, which checks `authStore.token`. If `VITE_USE_LOCAL_PROXY` changes between sessions, the user is logged out automatically to prevent stale proxy states.

### i18n

i18next is initialized in `src/i18n/index.ts` with locale resources in `src/i18n/locales/`. The backend also supports i18n via FastAPI-Babel (Python). To recompile backend translations after modifying `.po` files: `cd backend && uv run pybabel compile -d lang`. Supported frontend locales: en-US, zh-Hans, zh-Hant, de, ko, ja, fr, ru, it, ar, es.

## Key Conventions

- **Do not commit** `package-lock.json`, `yarn.lock`, or `pnpm-lock.yaml` — CI will block the PR.
- **Markdown files** committed in PRs are linted by `markdownlint-cli` in CI.
- **Python style**: Ruff (line length 120) following Google Python Style Guide. Run `uv run ruff check .` before committing backend changes.
- **Backend Python version** is strictly `3.10.x` — do not use syntax or stdlib features from 3.11+.
- **Frontend alias**: `@/` resolves to `src/` (configured in both `vite.config.ts` and `vitest.config.ts`).
- **Test setup**: Frontend tests use jsdom, mock `window.ipcRenderer`, `window.electronAPI`, and `react-i18next`. See `test/setup.ts`. Backend test fixtures and pytest markers (`model_backend`, `very_slow`, `optional`) are in `backend/tests/conftest.py`.
- **SSE timeout**: SSE connections close after 10 minutes of inactivity (configured in `chat_controller.py`).
- **`uv.lock`** (both root-level and `backend/uv.lock`) should be committed when Python dependencies change.
