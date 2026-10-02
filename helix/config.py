from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    env: str = os.getenv("HELIX_ENV", "development")
    host: str = os.getenv("HELIX_HOST", "127.0.0.1")
    port: int = int(os.getenv("HELIX_PORT", "8700"))
    db_path: str = os.getenv("HELIX_DB_PATH", "./helix.db")
    session_ttl_hours: int = int(os.getenv("HELIX_SESSION_TTL_HOURS", "8"))
    secure_cookies: bool = os.getenv("HELIX_SECURE_COOKIES", "false").lower() == "true"
    bootstrap_admin: str = os.getenv("HELIX_BOOTSTRAP_ADMIN", "admin")
    bootstrap_password: str = os.getenv("HELIX_BOOTSTRAP_PASSWORD", "")
    enrollment_ttl_minutes: int = int(os.getenv("HELIX_ENROLLMENT_TTL_MINUTES", "30"))


settings = Settings()
