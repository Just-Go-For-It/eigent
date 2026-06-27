"""Sync <-> async bridge.

MCP tools (via langchain-mcp-adapters) are async, but the trading pipeline is synchronous.
``AsyncRunner`` keeps a single asyncio event loop alive on a daemon thread so synchronous
code can drive coroutines without spinning up a new loop per call (which would break the
persistent MCP stdio session).
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any, Coroutine


class AsyncRunner:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="async-runner")
        self._thread.start()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro: Coroutine[Any, Any, Any], timeout: float = 30.0) -> Any:
        """Run a coroutine on the background loop from synchronous code and return its result."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def close(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
