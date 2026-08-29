from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login", auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: int
    username: str
    display_name: str
    roles: list[str]
    unit_code: str | None = None


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return f"pbkdf2_sha256$120000${salt}${digest}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        scheme, iterations, salt, expected = password_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user: CurrentUser) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user.username,
        "uid": user.id,
        "display_name": user.display_name,
        "roles": user.roles,
        "unit_code": user.unit_code,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(token: str | None = Depends(oauth2_scheme)) -> CurrentUser:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录已过期")
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录") from exc

    username = payload.get("sub")
    user_id = payload.get("uid")
    if not username or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的登录凭证")

    return CurrentUser(
        id=int(user_id),
        username=str(username),
        display_name=str(payload.get("display_name") or username),
        roles=list(payload.get("roles") or []),
        unit_code=payload.get("unit_code"),
    )
