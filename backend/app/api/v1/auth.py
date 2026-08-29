from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.core.security import CurrentUser, create_access_token, get_current_user
from app.repositories.user_repository import UserRepository
from app.schemas.auth import CurrentUserResponse, LoginRequest, LoginResponse
from app.services.user_service import UserService

router = APIRouter()


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = UserService(UserRepository(db)).authenticate(req.username, req.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    return ok(LoginResponse(access_token=create_access_token(user), user=CurrentUserResponse(**user.__dict__)))


@router.get("/me")
def me(current_user: CurrentUser = Depends(get_current_user)):
    return ok(CurrentUserResponse(**current_user.__dict__))
