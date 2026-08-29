from __future__ import annotations

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


def verify_password(plain_password: str, expected_password: str) -> bool:
    """开发期轻量密码校验。

    当前系统先使用环境变量中的管理员账号，避免引入重型用户/权限框架；
    后续接入真实用户表时可在 auth service 中替换校验来源。
    """
    return plain_password == expected_password


def authenticate_user(username: str, password: str) -> CurrentUser | None:
    if username != settings.admin_username:
        return None
    if not verify_password(password, settings.admin_password):
        return None
    return CurrentUser(
        id=1,
        username=settings.admin_username,
        display_name=settings.admin_display_name,
        roles=["admin"],
        unit_code="330782000000",
    )


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
