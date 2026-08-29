from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreateRequest, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))


@router.get("")
def list_users(include_disabled: bool = False, service: UserService = Depends(get_service)):
    return ok(service.list(include_disabled=include_disabled))


@router.post("")
def create_user(req: UserCreateRequest, service: UserService = Depends(get_service)):
    try:
        return ok(service.create(req))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/{user_id}")
def update_user(user_id: int, req: UserUpdateRequest, service: UserService = Depends(get_service)):
    try:
        row = service.update(user_id, req)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")
    return ok(row)


@router.delete("/{user_id}")
def delete_user(user_id: int, service: UserService = Depends(get_service)):
    return ok(service.delete(user_id))
