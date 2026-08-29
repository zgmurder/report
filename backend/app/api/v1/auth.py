from fastapi import APIRouter, Depends, HTTPException, status

from app.core.response import ok
from app.core.security import CurrentUser, authenticate_user, create_access_token, get_current_user
from app.schemas.auth import CurrentUserResponse, LoginRequest, LoginResponse

router = APIRouter()


@router.post("/login")
def login(req: LoginRequest):
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    return ok(LoginResponse(access_token=create_access_token(user), user=CurrentUserResponse(**user.__dict__)))


@router.get("/me")
def me(current_user: CurrentUser = Depends(get_current_user)):
    return ok(CurrentUserResponse(**current_user.__dict__))
