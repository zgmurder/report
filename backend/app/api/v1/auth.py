from fastapi import APIRouter, Depends

from app.core.response import ok
from app.core.security import CurrentUser, get_current_user
from app.schemas.auth import CurrentUserResponse, LoginRequest, LoginResponse

router = APIRouter()


@router.post("/login")
def login(req: LoginRequest):
    # TODO: 接入真实用户表和 JWT 签发。第一阶段仅提供前端联调 token。
    return ok(LoginResponse(access_token=f"dev-token-{req.username}"))


@router.get("/me")
def me(current_user: CurrentUser = Depends(get_current_user)):
    return ok(CurrentUserResponse(**current_user.__dict__))
