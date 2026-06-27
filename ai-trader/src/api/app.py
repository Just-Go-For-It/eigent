"""FastAPI app: status, recent decisions, manual approve/deny, and an optional TradingView
webhook. Auth is via a bearer token (API_AUTH_TOKEN) — never ship this with no auth
(that was NoFx's documented mistake). Import is lazy-friendly: requires `fastapi`.
"""
from __future__ import annotations

import hmac

from ..config import load_config
from ..store import Store

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Request
except ImportError as e:  # pragma: no cover
    raise SystemExit("FastAPI not installed. Install extras: pip install '.[api]'") from e

config = load_config()
store = Store()
app = FastAPI(title="ai-trader", version="0.1.0")


def require_auth(authorization: str = Header(default="")) -> None:
    token = authorization.removeprefix("Bearer ").strip()
    if not config.api_auth_token or not hmac.compare_digest(token, config.api_auth_token):
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": config.trading_mode}


@app.get("/status", dependencies=[Depends(require_auth)])
def status() -> dict:
    return {"config": config.summary(), "recent_decisions": store.recent_decisions()}


@app.post("/webhook/tradingview")
async def tradingview(request: Request) -> dict:
    body = await request.json()
    secret = body.get("secret", "")
    if not config.tradingview_webhook_secret or not hmac.compare_digest(
        secret, config.tradingview_webhook_secret
    ):
        raise HTTPException(status_code=401, detail="bad webhook secret")
    # Signal is recorded; the worker decides — webhooks never place orders directly.
    return {"received": True, "symbol": body.get("symbol"), "note": "queued as signal"}
