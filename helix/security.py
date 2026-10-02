from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
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
    # Delimiters in the stored hash string must be unescaped '$' so verify_secret can parse scheme and params
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"

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

def generate_totp_secret() -> str:
    # 20 random bytes encoded in base32
    return base64.b32encode(os.urandom(20)).decode("utf-8").replace("=", "")

def _totp_at(secret: str, counter: int) -> str:
    # Pad secret if needed for base32 decoding
    secret_clean = secret.upper().replace(" ", "")
    missing_padding = len(secret_clean) % 8
    if missing_padding:
        secret_clean += "=" * (8 - missing_padding)
    key = base64.b32decode(secret_clean)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    binary = ((h[offset] & 0x7F) << 24) | ((h[offset + 1] & 0xFF) << 16) | ((h[offset + 2] & 0xFF) << 8) | (h[offset + 3] & 0xFF)
    otp = binary % 1000000
    return f"{otp:06d}"

def verify_totp_code(secret: str, code: str, window: int = 1) -> bool:
    if not secret or not code:
        return False
    code_clean = code.strip()
    if not code_clean.isdigit() or len(code_clean) != 6:
        return False
    now_counter = int(time.time() // 30)
    for delta in range(-window, window + 1):
        if hmac.compare_digest(_totp_at(secret, now_counter + delta), code_clean):
            return True
    return False

def get_totp_uri(secret: str, username: str, issuer: str = "Helix Platform") -> str:
    from urllib.parse import quote
    return f"otpauth://totp/{quote(issuer)}:{quote(username)}?secret={secret}&issuer={quote(issuer)}"

def compute_audit_hash(prev_hash: str, actor: str, action: str, target: str, detail_json: str, created_at: str) -> str:
    raw = f"{prev_hash}|{actor}|{action}|{target}|{detail_json}|{created_at}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
