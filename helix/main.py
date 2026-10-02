from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from collections import defaultdict
import time

from .config import settings
from .db import Database
from .security import (
    compute_audit_hash,
    generate_totp_secret,
    get_totp_uri,
    hash_secret,
    hash_token,
    token,
    utcnow,
    verify_secret,
    verify_totp_code,
)


app = FastAPI(title="Glowhaven Helix", version="0.1.0", docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory="helix/static"), name="static")
db = Database(settings.db_path)
SESSION_COOKIE = "helix_session"
CSRF_COOKIE = "helix_csrf"

ALLOWED_ACTIONS = {
    "reboot",
    "shutdown",
    "service_start",
    "service_stop",
    "service_restart",
    "refresh_inventory",
    "collect_diagnostics",
}
SERVICE_RE = re.compile(r"^[A-Za-z0-9_.@-]{1,128}$")


class SimpleRateLimiter:
    def __init__(self):
        self.requests: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        timestamps = [t for t in self.requests[key] if t > cutoff]
        if len(timestamps) >= max_requests:
            return False
        timestamps.append(now)
        self.requests[key] = timestamps
        return True

rate_limiter = SimpleRateLimiter()

def enforce_rate_limit(key: str, max_requests: int = 15, window_seconds: int = 60) -> None:
    if not rate_limiter.check(key, max_requests, window_seconds):
        raise HTTPException(status_code=429, detail="too many requests, please slow down")

def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="password must be at least 8 characters long")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise HTTPException(status_code=422, detail="password must contain both letters and digits")

def audit(actor: str, action: str, target: str, detail: dict[str, Any] | None = None) -> None:
    created_at = utcnow().isoformat()
    detail_json = json.dumps(detail or {}, separators=(",", ":"), sort_keys=True)

    last = db.one("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1")
    prev_hash = last["hash"] if (last and last["hash"]) else "0" * 64
    entry_hash = compute_audit_hash(prev_hash, actor, action, target, detail_json, created_at)

    db.execute(
        "INSERT INTO audit_log(actor, action, target, detail_json, prev_hash, hash, created_at) VALUES(?,?,?,?,?,?,?)",
        (actor, action, target, detail_json, prev_hash, entry_hash, created_at),
    )


def ensure_bootstrap() -> None:
    existing = db.one("SELECT id FROM users LIMIT 1")
    if existing:
        return
    password = settings.bootstrap_password or secrets.token_urlsafe(18)
    username = settings.bootstrap_admin.strip() or "admin"
    db.execute(
        "INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
        (username, hash_secret(password), "admin", utcnow().isoformat()),
    )
    print(f"Helix bootstrap user: {username}")
    if not settings.bootstrap_password:
        print(f"Helix bootstrap password: {password}")


ensure_bootstrap()


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    if settings.secure_cookies:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=512)
    totp_code: str | None = Field(default=None, max_length=12)


class JobRequest(BaseModel):
    action: str = Field(min_length=1, max_length=64)
    params: dict[str, Any] = Field(default_factory=dict)
    stepup_code: str | None = Field(default=None, max_length=12)

    @field_validator("action")
    @classmethod
    def action_allowed(cls, value: str) -> str:
        if value not in ALLOWED_ACTIONS:
            raise ValueError("unsupported action")
        return value


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=512)
    role: str = Field(pattern=r"^(admin|operator|viewer)$")


class UpdateUserRoleRequest(BaseModel):
    role: str = Field(pattern=r"^(admin|operator|viewer)$")


class UpdateUserPasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=512)


class MfaCodeRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6)


class Heartbeat(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    platform: str = Field(min_length=1, max_length=64)
    arch: str = Field(min_length=1, max_length=64)
    os_version: str = Field(default="", max_length=255)
    cpu_percent: float = Field(default=0, ge=0, le=100)
    memory_percent: float = Field(default=0, ge=0, le=100)
    disk_percent: float = Field(default=0, ge=0, le=100)
    uptime_seconds: int = Field(default=0, ge=0, le=10**10)
    inventory: dict[str, Any] = Field(default_factory=dict)
    labels: dict[str, str] = Field(default_factory=dict)


class AgentRegister(BaseModel):
    enrollment_token: str = Field(min_length=20, max_length=256)
    name: str = Field(min_length=1, max_length=128)
    hostname: str = Field(min_length=1, max_length=255)
    platform: str = Field(min_length=1, max_length=64)
    arch: str = Field(min_length=1, max_length=64)
    os_version: str = Field(default="", max_length=255)


class AgentJobResult(BaseModel):
    status: str = Field(pattern=r"^(succeeded|failed)$")
    result: dict[str, Any] = Field(default_factory=dict)


def current_session(cookie_session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> sqlite3.Row:
    if not cookie_session_id:
        raise HTTPException(status_code=401, detail="authentication required")
    row = db.one(
        "SELECT s.*, u.username, u.role, u.totp_secret, u.totp_enabled FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.id=?",
        (cookie_session_id,),
    )
    if not row or row["expires_at"] <= utcnow().isoformat():
        raise HTTPException(status_code=401, detail="session expired")
    return row


def require_role(*roles: str):
    def dep(session: sqlite3.Row = Depends(current_session)) -> sqlite3.Row:
        if session["role"] not in roles:
            raise HTTPException(status_code=403, detail="insufficient permissions")
        return session
    return dep


def require_csrf(
    request: Request,
    session: sqlite3.Row = Depends(current_session),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
) -> sqlite3.Row:
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if not csrf_header or not csrf_cookie or not secrets.compare_digest(csrf_header, csrf_cookie):
            raise HTTPException(status_code=403, detail="csrf validation failed")
    return session


def agent_server(agent_key: str | None = Header(default=None, alias="X-Helix-Agent-Key")) -> sqlite3.Row:
    if not agent_key:
        raise HTTPException(status_code=401, detail="agent key required")
    row = db.one("SELECT * FROM servers WHERE agent_key_hash=?", (hash_token(agent_key),))
    if not row:
        raise HTTPException(status_code=401, detail="invalid agent key")
    return row


@app.get("/")
async def home() -> FileResponse:
    return FileResponse("helix/static/index.html")


@app.get("/api/csrf")
async def csrf(response: Response, session: sqlite3.Row = Depends(current_session)):
    response.set_cookie(CSRF_COOKIE, session["csrf_token"], secure=settings.secure_cookies, httponly=False, samesite="strict", max_age=3600)
    return {"csrf_token": session["csrf_token"]}


@app.post("/api/auth/login")
async def login(payload: LoginRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"login:{client_ip}", max_requests=10, window_seconds=60)

    username = payload.username.strip()
    row = db.one("SELECT * FROM users WHERE username=?", (username,))

    if row and row["locked_until"]:
        if row["locked_until"] > utcnow().isoformat():
            audit(username, "auth.login_failed", "lockout", {"reason": "account_locked"})
            raise HTTPException(status_code=429, detail="account is locked due to multiple failed login attempts")

    if not row or not verify_secret(payload.password, row["password_hash"]):
        if row:
            attempts = row["failed_login_attempts"] + 1
            if attempts >= 5:
                locked_time = (utcnow() + timedelta(minutes=15)).isoformat()
                db.execute("UPDATE users SET failed_login_attempts=?, locked_until=? WHERE id=?", (attempts, locked_time, row["id"]))
                audit(username, "auth.account_locked", "user", {"attempts": attempts})
            else:
                db.execute("UPDATE users SET failed_login_attempts=? WHERE id=?", (attempts, row["id"]))
        audit(username or "unknown", "auth.login_failed", "session", {"reason": "invalid_credentials"})
        raise HTTPException(status_code=401, detail="invalid credentials")

    if row["totp_enabled"]:
        if not payload.totp_code or not verify_totp_code(row["totp_secret"], payload.totp_code):
            audit(username, "auth.login_failed", "mfa", {"reason": "mfa_required_or_invalid"})
            raise HTTPException(status_code=401, detail="mfa code required or invalid")

    db.execute("UPDATE users SET failed_login_attempts=0, locked_until=NULL WHERE id=?", (row["id"],))

    sid = token()
    csrf_token = token()
    expires = utcnow() + timedelta(hours=settings.session_ttl_hours)
    db.execute(
        "INSERT INTO sessions(id,user_id,csrf_token,expires_at) VALUES(?,?,?,?)",
        (sid, row["id"], csrf_token, expires.isoformat()),
    )
    response.set_cookie(SESSION_COOKIE, sid, secure=settings.secure_cookies, httponly=True, samesite="strict", max_age=settings.session_ttl_hours * 3600)
    response.set_cookie(CSRF_COOKIE, csrf_token, secure=settings.secure_cookies, httponly=False, samesite="strict", max_age=3600)
    audit(row["username"], "auth.login", "session")
    return {"username": row["username"], "role": row["role"], "totp_enabled": bool(row["totp_enabled"])}


@app.post("/api/auth/mfa/setup")
async def mfa_setup(session: sqlite3.Row = Depends(require_csrf)):
    enforce_rate_limit(f"mfa:{session['user_id']}", max_requests=10, window_seconds=60)
    sec = generate_totp_secret()
    db.execute("UPDATE users SET totp_secret=? WHERE id=?", (sec, session["user_id"]))
    uri = get_totp_uri(sec, session["username"])
    audit(session["username"], "auth.mfa_setup", "user")
    return {"secret": sec, "otpauth_url": uri}


@app.post("/api/auth/mfa/enable")
async def mfa_enable(payload: MfaCodeRequest, session: sqlite3.Row = Depends(require_csrf)):
    enforce_rate_limit(f"mfa:{session['user_id']}", max_requests=10, window_seconds=60)
    row = db.one("SELECT totp_secret FROM users WHERE id=?", (session["user_id"],))
    if not row or not row["totp_secret"]:
        raise HTTPException(status_code=400, detail="mfa not initialized; run setup first")
    if not verify_totp_code(row["totp_secret"], payload.totp_code):
        raise HTTPException(status_code=400, detail="invalid mfa code")
    db.execute("UPDATE users SET totp_enabled=1 WHERE id=?", (session["user_id"],))
    audit(session["username"], "auth.mfa_enabled", "user")
    return {"ok": True}


@app.post("/api/auth/mfa/disable")
async def mfa_disable(payload: MfaCodeRequest, session: sqlite3.Row = Depends(require_csrf)):
    enforce_rate_limit(f"mfa:{session['user_id']}", max_requests=10, window_seconds=60)
    row = db.one("SELECT totp_secret FROM users WHERE id=?", (session["user_id"],))
    if not row or not row["totp_secret"] or not verify_totp_code(row["totp_secret"], payload.totp_code):
        raise HTTPException(status_code=400, detail="invalid mfa code")
    db.execute("UPDATE users SET totp_enabled=0, totp_secret='' WHERE id=?", (session["user_id"],))
    audit(session["username"], "auth.mfa_disabled", "user")
    return {"ok": True}


@app.get("/api/sessions")
async def list_sessions(session: sqlite3.Row = Depends(current_session)):
    rows = db.all("SELECT id, expires_at FROM sessions WHERE user_id=? ORDER BY expires_at DESC", (session["user_id"],))
    return [{"id": r["id"], "expires_at": r["expires_at"], "is_current": r["id"] == session["id"]} for r in rows]


@app.delete("/api/sessions/{session_id}")
async def revoke_session(session_id: str, session: sqlite3.Row = Depends(require_csrf)):
    target_session = db.one("SELECT * FROM sessions WHERE id=?", (session_id,))
    if not target_session:
        raise HTTPException(status_code=404, detail="session not found")
    if target_session["user_id"] != session["user_id"] and session["role"] != "admin":
        raise HTTPException(status_code=403, detail="insufficient permissions to revoke session")
    db.execute("DELETE FROM sessions WHERE id=?", (session_id,))
    audit(session["username"], "session.revoke", session_id)
    return {"ok": True}


@app.get("/api/users")
async def list_users(session: sqlite3.Row = Depends(require_role("admin"))):
    rows = db.all("SELECT id, username, role, totp_enabled, created_at FROM users ORDER BY username")
    return [{"id": r["id"], "username": r["username"], "role": r["role"], "totp_enabled": bool(r["totp_enabled"]), "created_at": r["created_at"]} for r in rows]


@app.post("/api/users")
async def create_user(payload: CreateUserRequest, session: sqlite3.Row = Depends(require_role("admin")), _: sqlite3.Row = Depends(require_csrf)):
    validate_password_strength(payload.password)
    username = payload.username.strip()
    existing = db.one("SELECT id FROM users WHERE username=?", (username,))
    if existing:
        raise HTTPException(status_code=400, detail="username already exists")
    db.execute(
        "INSERT INTO users(username, password_hash, role, created_at) VALUES(?,?,?,?)",
        (username, hash_secret(payload.password), payload.role, utcnow().isoformat()),
    )
    audit(session["username"], "user.create", username, {"role": payload.role})
    return {"username": username, "role": payload.role}


@app.patch("/api/users/{user_id}/role")
async def update_user_role(user_id: int, payload: UpdateUserRoleRequest, session: sqlite3.Row = Depends(require_role("admin")), _: sqlite3.Row = Depends(require_csrf)):
    target_user = db.one("SELECT * FROM users WHERE id=?", (user_id,))
    if not target_user:
        raise HTTPException(status_code=404, detail="user not found")
    if target_user["id"] == session["user_id"] and payload.role != "admin":
        admin_count = db.one("SELECT COUNT(*) as c FROM users WHERE role='admin'")["c"]
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="cannot demote the sole admin user")
    db.execute("UPDATE users SET role=? WHERE id=?", (payload.role, user_id))
    audit(session["username"], "user.update_role", target_user["username"], {"new_role": payload.role})
    return {"ok": True}


@app.post("/api/users/{user_id}/password")
async def update_user_password(user_id: int, payload: UpdateUserPasswordRequest, session: sqlite3.Row = Depends(require_role("admin")), _: sqlite3.Row = Depends(require_csrf)):
    validate_password_strength(payload.password)
    target_user = db.one("SELECT * FROM users WHERE id=?", (user_id,))
    if not target_user:
        raise HTTPException(status_code=404, detail="user not found")
    db.execute("UPDATE users SET password_hash=? WHERE id=?", (hash_secret(payload.password), user_id))
    # Revoke all existing sessions for this user upon password reset
    db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    audit(session["username"], "user.update_password", target_user["username"])
    return {"ok": True}


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, session: sqlite3.Row = Depends(require_role("admin")), _: sqlite3.Row = Depends(require_csrf)):
    target_user = db.one("SELECT * FROM users WHERE id=?", (user_id,))
    if not target_user:
        raise HTTPException(status_code=404, detail="user not found")
    if target_user["id"] == session["user_id"]:
        raise HTTPException(status_code=400, detail="cannot delete your own user account")
    if target_user["role"] == "admin":
        admin_count = db.one("SELECT COUNT(*) as c FROM users WHERE role='admin'")["c"]
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="cannot delete sole admin user")
    db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    db.execute("DELETE FROM users WHERE id=?", (user_id,))
    audit(session["username"], "user.delete", target_user["username"])
    return {"ok": True}


@app.post("/api/auth/logout")
async def logout(response: Response, session: sqlite3.Row = Depends(require_csrf)):
    db.execute("DELETE FROM sessions WHERE id=?", (session["id"],))
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(CSRF_COOKIE)
    return {"ok": True}


@app.get("/api/me")
async def me(session: sqlite3.Row = Depends(current_session)):
    return {"username": session["username"], "role": session["role"], "totp_enabled": bool(session["totp_enabled"])}


@app.get("/api/summary")
async def summary(_: sqlite3.Row = Depends(current_session)):
    rows = db.all("SELECT * FROM servers")
    now = utcnow()
    # Cache timestamp across iteration and count statuses efficiently
    statuses = [effective_status(row, now=now) for row in rows]
    queued = db.one("SELECT COUNT(*) AS c FROM jobs WHERE status='queued'")["c"]
    failed = db.one("SELECT COUNT(*) AS c FROM jobs WHERE status='failed' AND created_at >= ?", ((now - timedelta(hours=24)).isoformat(),))["c"]
    return {"servers": len(rows), "online": statuses.count("online"), "warning": statuses.count("warning"), "queued_jobs": queued, "failed_jobs_24h": failed}


def effective_status(row: sqlite3.Row, now: datetime | None = None) -> str:
    """
    Computes effective server status (online, warning, or offline).
    Accepts an optional pre-computed `now` timestamp to avoid repeated system clock calls
    when batch-evaluating multiple servers.
    """
    last_seen = row["last_seen"]
    if not last_seen:
        return "offline"
    if now is None:
        now = utcnow()
    try:
        age = (now - datetime.fromisoformat(last_seen)).total_seconds()
    except ValueError:
        return "offline"
    if age > 90:
        return "offline"
    # Direct numeric check avoids string/float conversion overhead and list creation
    if row["cpu_percent"] >= 90 or row["memory_percent"] >= 90 or row["disk_percent"] >= 90:
        return "warning"
    return "online"


def serialize_server(row: sqlite3.Row, now: datetime | None = None) -> dict[str, Any]:
    return {
        "id": row["id"], "name": row["name"], "hostname": row["hostname"],
        "platform": row["platform"], "arch": row["arch"], "os_version": row["os_version"],
        "status": effective_status(row, now=now), "last_seen": row["last_seen"],
        "cpu_percent": row["cpu_percent"], "memory_percent": row["memory_percent"],
        "disk_percent": row["disk_percent"], "uptime_seconds": row["uptime_seconds"],
        "inventory": db.json(row["inventory_json"]), "labels": db.json(row["labels_json"]),
        "created_at": row["created_at"],
    }


@app.get("/api/servers")
async def servers(_: sqlite3.Row = Depends(current_session)):
    rows = db.all("SELECT * FROM servers ORDER BY name COLLATE NOCASE")
    now = utcnow()
    return [serialize_server(row, now=now) for row in rows]


@app.get("/api/servers/{server_id}")
async def server(server_id: str, _: sqlite3.Row = Depends(current_session)):
    row = db.one("SELECT * FROM servers WHERE id=?", (server_id,))
    if not row:
        raise HTTPException(status_code=404, detail="server not found")
    jobs = db.all("SELECT * FROM jobs WHERE server_id=? ORDER BY created_at DESC LIMIT 20", (server_id,))
    result = serialize_server(row)
    result["jobs"] = [serialize_job(j) for j in jobs]
    return result


def validate_job_params(action: str, params: dict[str, Any]) -> dict[str, Any]:
    if action.startswith("service_"):
        service = params.get("service")
        if not isinstance(service, str) or not SERVICE_RE.fullmatch(service):
            raise HTTPException(status_code=422, detail="invalid service name")
        return {"service": service}
    if params:
        raise HTTPException(status_code=422, detail="this action accepts no parameters")
    return {}


def serialize_job(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"], "server_id": row["server_id"], "action": row["action"],
        "params": db.json(row["params_json"]), "status": row["status"],
        "result": db.json(row["result_json"]), "created_at": row["created_at"],
        "started_at": row["started_at"], "finished_at": row["finished_at"],
    }


@app.post("/api/servers/{server_id}/jobs")
async def create_job(
    server_id: str,
    payload: JobRequest,
    request: Request,
    session: sqlite3.Row = Depends(require_role("admin", "operator")),
    _: sqlite3.Row = Depends(require_csrf),
):
    server_row = db.one("SELECT * FROM servers WHERE id=?", (server_id,))
    if not server_row:
        raise HTTPException(status_code=404, detail="server not found")

    # Step-up authentication enforcement for high impact actions (reboot, shutdown)
    if payload.action in {"reboot", "shutdown"} and session["totp_enabled"]:
        stepup_header = request.headers.get("X-StepUp-TOTP")
        code = payload.stepup_code or stepup_header
        if not code or not verify_totp_code(session["totp_secret"], code):
            raise HTTPException(status_code=403, detail="step-up mfa code required for this action")

    params = validate_job_params(payload.action, payload.params)
    job_id = str(uuid.uuid4())
    now = utcnow().isoformat()
    db.execute(
        "INSERT INTO jobs(id,server_id,action,params_json,requested_by,status,result_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (job_id, server_id, payload.action, json.dumps(params), session["user_id"], "queued", "{}", now),
    )
    audit(session["username"], "job.create", server_id, {"job_id": job_id, "action": payload.action, "params": params})
    return {"id": job_id, "status": "queued"}


@app.get("/api/jobs")
async def jobs(_: sqlite3.Row = Depends(current_session)):
    rows = db.all("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 200")
    return [serialize_job(row) for row in rows]


@app.post("/api/enrollment-tokens")
async def create_enrollment(request: Request, session: sqlite3.Row = Depends(require_role("admin")), _: sqlite3.Row = Depends(require_csrf)):
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"enrollment:{client_ip}", max_requests=10, window_seconds=60)
    raw = token()
    expires = utcnow() + timedelta(minutes=settings.enrollment_ttl_minutes)
    db.execute(
        "INSERT INTO enrollment_tokens(token_hash,created_by,expires_at) VALUES(?,?,?)",
        (hash_token(raw), session["user_id"], expires.isoformat()),
    )
    audit(session["username"], "enrollment.create", "fleet", {"expires_at": expires.isoformat()})
    return {"token": raw, "expires_at": expires.isoformat()}


@app.post("/api/agent/register")
async def agent_register(payload: AgentRegister, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"agent_register:{client_ip}", max_requests=20, window_seconds=60)
    enrollment = db.one("SELECT * FROM enrollment_tokens WHERE token_hash=?", (hash_token(payload.enrollment_token),))
    if not enrollment or enrollment["used_at"] or enrollment["expires_at"] <= utcnow().isoformat():
        raise HTTPException(status_code=401, detail="invalid or expired enrollment token")
    server_id = str(uuid.uuid4())
    raw_key = token()
    db.execute("UPDATE enrollment_tokens SET used_at=? WHERE token_hash=?", (utcnow().isoformat(), enrollment["token_hash"]))
    db.execute(
        "INSERT INTO servers(id,name,hostname,platform,arch,os_version,status,last_seen,agent_key_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (server_id, payload.name, payload.hostname, payload.platform, payload.arch, payload.os_version, "online", utcnow().isoformat(), hash_token(raw_key), utcnow().isoformat()),
    )
    audit("agent", "server.register", server_id, {"hostname": payload.hostname, "platform": payload.platform})
    return {"server_id": server_id, "agent_key": raw_key, "heartbeat_interval_seconds": 15}


@app.post("/api/agent/heartbeat")
async def agent_heartbeat(payload: Heartbeat, server_row: sqlite3.Row = Depends(agent_server)):
    now = utcnow().isoformat()
    db.execute(
        "UPDATE servers SET hostname=?,platform=?,arch=?,os_version=?,status='online',last_seen=?,cpu_percent=?,memory_percent=?,disk_percent=?,uptime_seconds=?,inventory_json=?,labels_json=? WHERE id=?",
        (payload.hostname, payload.platform, payload.arch, payload.os_version, now, payload.cpu_percent, payload.memory_percent, payload.disk_percent, payload.uptime_seconds, json.dumps(payload.inventory, separators=(",", ":")), json.dumps(payload.labels, separators=(",", ":")), server_row["id"]),
    )
    return {"ok": True}


@app.post("/api/agent/jobs/poll")
async def agent_jobs_poll(server_row: sqlite3.Row = Depends(agent_server)):
    job = db.one("SELECT * FROM jobs WHERE server_id=? AND status='queued' ORDER BY created_at LIMIT 1", (server_row["id"],))
    if not job:
        return {"job": None}
    db.execute("UPDATE jobs SET status='running',started_at=? WHERE id=?", (utcnow().isoformat(), job["id"]))
    return {"job": {"id": job["id"], "action": job["action"], "params": db.json(job["params_json"])}}


@app.post("/api/agent/jobs/{job_id}/report")
async def agent_job_report(job_id: str, payload: AgentJobResult, server_row: sqlite3.Row = Depends(agent_server)):
    job = db.one("SELECT * FROM jobs WHERE id=? AND server_id=?", (job_id, server_row["id"]))
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    finished = utcnow().isoformat()
    db.execute("UPDATE jobs SET status=?,result_json=?,finished_at=? WHERE id=?", (payload.status, json.dumps(payload.result, separators=(",", ":")), finished, job_id))
    audit("agent", f"job.{payload.status}", server_row["id"], {"job_id": job_id, "action": job["action"]})
    return {"ok": True}


@app.get("/api/audit")
async def audit_log(session: sqlite3.Row = Depends(require_role("admin"))):
    rows = db.all("SELECT id, actor, action, target, detail_json, prev_hash, hash, created_at FROM audit_log ORDER BY id DESC LIMIT 250")
    return [
        {
            "id": r["id"],
            "actor": r["actor"],
            "action": r["action"],
            "target": r["target"],
            "detail": db.json(r["detail_json"]),
            "prev_hash": r["prev_hash"],
            "hash": r["hash"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@app.get("/api/audit/verify")
async def verify_audit_trail(session: sqlite3.Row = Depends(require_role("admin"))):
    rows = db.all("SELECT id, actor, action, target, detail_json, prev_hash, hash, created_at FROM audit_log ORDER BY id ASC")
    expected_prev = "0" * 64
    for r in rows:
        if r["prev_hash"] != expected_prev:
            return {
                "verified": False,
                "tampered_id": r["id"],
                "reason": f"prev_hash mismatch on record {r['id']}",
            }
        recomputed = compute_audit_hash(
            r["prev_hash"], r["actor"], r["action"], r["target"], r["detail_json"], r["created_at"]
        )
        if r["hash"] != recomputed:
            return {
                "verified": False,
                "tampered_id": r["id"],
                "reason": f"hash verification failed on record {r['id']}",
            }
        expected_prev = r["hash"]
    return {"verified": True, "total_records": len(rows)}


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "glowhaven-helix"}


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    print(f"Unhandled error: {exc!r}")
    return JSONResponse(status_code=500, content={"detail": "internal server error"})
