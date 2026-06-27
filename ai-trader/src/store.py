"""Audit log — every decision and fill is persisted. SQLite via stdlib (no dependency).
This is the compliance/debug record: you can always reconstruct *why* a trade happened.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path("ai_trader.db")


class Store:
    def __init__(self, path: str | Path = DEFAULT_DB):
        self.conn = sqlite3.connect(str(path))
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS decisions (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   ts TEXT, symbol TEXT, action TEXT, approved INTEGER,
                   reasons TEXT, trace TEXT)"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS fills (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   ts TEXT, symbol TEXT, side TEXT, qty REAL, price REAL, notional REAL)"""
        )
        self.conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def log_decision(self, decision) -> None:
        self.conn.execute(
            "INSERT INTO decisions (ts, symbol, action, approved, reasons, trace) VALUES (?,?,?,?,?,?)",
            (
                self._now(),
                decision.symbol,
                decision.final_action,
                int(decision.approved),
                json.dumps(decision.risk_reasons),
                json.dumps(decision.trace),
            ),
        )
        self.conn.commit()

    def log_fill(self, fill) -> None:
        self.conn.execute(
            "INSERT INTO fills (ts, symbol, side, qty, price, notional) VALUES (?,?,?,?,?,?)",
            (self._now(), fill.symbol, fill.side, fill.qty, fill.price, fill.notional),
        )
        self.conn.commit()

    def recent_decisions(self, limit: int = 20) -> list[dict]:
        cur = self.conn.execute(
            "SELECT ts, symbol, action, approved FROM decisions ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [
            {"ts": r[0], "symbol": r[1], "action": r[2], "approved": bool(r[3])} for r in cur.fetchall()
        ]

    def close(self) -> None:
        self.conn.close()
