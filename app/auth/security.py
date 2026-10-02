from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.config import get_settings

ALGO = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(subject: str, purpose: str = "access", minutes: int | None = None, **claims) -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + (timedelta(minutes=minutes) if minutes else timedelta(hours=s.jwt_expiry_hours))
    payload = {"sub": subject, "purpose": purpose, "exp": exp, **claims}
    return jwt.encode(payload, s.app_secret_key, algorithm=ALGO)


def decode_token(token: str, purpose: str = "access") -> dict:
    payload = jwt.decode(token, get_settings().app_secret_key, algorithms=[ALGO])
    if payload.get("purpose") != purpose:
        raise jwt.InvalidTokenError("wrong token purpose")
    return payload


def _fernet() -> Fernet:
    key = hashlib.sha256(("fernet:" + get_settings().app_secret_key).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_json(data: dict) -> str:
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_json(token: str) -> dict:
    return json.loads(_fernet().decrypt(token.encode()))
