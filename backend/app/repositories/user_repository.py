from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.system import User
from app.schemas.user import UserCreateRequest, UserUpdateRequest


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def ensure_seed_data(self) -> None:
        settings = get_settings()
        exists = self.db.scalar(select(User.id).where(User.username == settings.admin_username).limit(1))
        if exists:
            return
        row = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            display_name=settings.admin_display_name,
            roles="admin",
            unit_code="330782000000",
            status="enabled",
        )
        self.db.add(row)
        self.db.commit()

    def list(self, include_disabled: bool = False) -> list[User]:
        stmt = select(User)
        if not include_disabled:
            stmt = stmt.where(User.status == "enabled")
        stmt = stmt.order_by(User.id.asc())
        return list(self.db.scalars(stmt).all())

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username).limit(1))

    def create(self, req: UserCreateRequest) -> User:
        row = User(
            username=req.username.strip(),
            password_hash=hash_password(req.password),
            display_name=req.display_name.strip(),
            roles=",".join(req.roles or ["user"]),
            unit_code=req.unit_code,
            status=req.status,
        )
        self.db.add(row)
        self._commit_or_raise_duplicate()
        self.db.refresh(row)
        return row

    def update(self, user_id: int, req: UserUpdateRequest) -> User | None:
        row = self.db.get(User, user_id)
        if not row:
            return None
        payload = req.model_dump(exclude_unset=True)
        if "password" in payload and payload["password"]:
            row.password_hash = hash_password(payload.pop("password"))
        if "display_name" in payload and payload["display_name"] is not None:
            row.display_name = payload["display_name"].strip()
        if "roles" in payload and payload["roles"] is not None:
            row.roles = ",".join(payload["roles"] or ["user"])
        if "unit_code" in payload:
            row.unit_code = payload["unit_code"]
        if "status" in payload and payload["status"] is not None:
            row.status = payload["status"]
        self._commit_or_raise_duplicate()
        self.db.refresh(row)
        return row

    def delete(self, user_id: int) -> bool:
        row = self.db.get(User, user_id)
        if not row:
            return False
        row.status = "disabled"
        self.db.commit()
        return True

    def _commit_or_raise_duplicate(self) -> None:
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("用户名已存在") from exc
