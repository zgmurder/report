from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

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


def get_current_user(token: str | None = Depends(oauth2_scheme)) -> CurrentUser:
    """当前用户占位实现。

    第一阶段先提供稳定依赖入口；接入真实登录后在此处完成 JWT 解析、权限和数据范围加载。
    """
    return CurrentUser(id=1, username="admin", display_name="管理员", roles=["admin"])
