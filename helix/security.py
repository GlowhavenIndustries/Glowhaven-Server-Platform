from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone

SALT_BYTES = 16
KEY_BYTES = 32
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def hash_secret(secret: str) -> str:
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.scrypt(
        secret.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=KEY_BYTES
    )
    return f"scrypt\${SCRYPT_N}\${SCRYPT_R}\${SCRYPT_P}\${salt.hex()}\${digest.hex()}"

def verify_secret(secret: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, digest_hex = encoded.split("$", 5)
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            secret.encode("utf-8"), salt=bytes.fromhex(salt_hex),
            n=int(n), r=int(r), p=int(p), dklen=KEY_BYTES
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

def token() -> str:
    return secrets.token_urlsafe(32)

def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
