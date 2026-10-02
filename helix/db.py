from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'operator', 'viewer')),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf_token TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS enrollment_tokens (
    token_hash TEXT PRIMARY KEY,
    created_by INTEGER NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL,
    used_at TEXT
);
CREATE TABLE IF NOT EXISTS servers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    hostname TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'unknown',
    arch TEXT NOT NULL DEFAULT 'unknown',
    os_version TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'offline',
    last_seen TEXT,
    cpu_percent REAL NOT NULL DEFAULT 0,
    memory_percent REAL NOT NULL DEFAULT 0,
    disk_percent REAL NOT NULL DEFAULT 0,
    uptime_seconds INTEGER NOT NULL DEFAULT 0,
    inventory_json TEXT NOT NULL DEFAULT '{}',
    labels_json TEXT NOT NULL DEFAULT '{}',
    agent_key_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    server_id TEXT NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    params_json TEXT NOT NULL DEFAULT '{}',
    requested_by INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL DEFAULT 'queued',
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status);
CREATE INDEX IF NOT EXISTS idx_servers_last_seen ON servers(last_seen);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
"""

def _json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)

class Database:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def one(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(query, params).fetchone()

    def all(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(query, params).fetchall()

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        with self.connect() as conn:
            conn.execute(query, params)

    @staticmethod
    def json(value: str | None) -> Any:
        try:
            return json.loads(value or "{}")
        except json.JSONDecodeError:
            return {}
