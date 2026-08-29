from __future__ import annotations

from app.core.security import CurrentUser, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreateRequest, UserResponse, UserUpdateRequest


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def authenticate(self, username: str, password: str) -> CurrentUser | None:
        row = self.repo.get_by_username(username.strip())
        if not row or row.status != "enabled":
            return None
        if not verify_password(password, row.password_hash):
            return None
        return CurrentUser(
            id=row.id,
            username=row.username,
            display_name=row.display_name,
            roles=self._parse_roles(row.roles),
            unit_code=row.unit_code,
        )

    def list(self, include_disabled: bool = False) -> list[UserResponse]:
        return [self._to_response(row) for row in self.repo.list(include_disabled=include_disabled)]

    def create(self, req: UserCreateRequest) -> UserResponse:
        row = self.repo.create(req)
        return self._to_response(row)

    def update(self, user_id: int, req: UserUpdateRequest) -> UserResponse | None:
        row = self.repo.update(user_id, req)
        return self._to_response(row) if row else None

    def delete(self, user_id: int) -> dict[str, bool]:
        return {"deleted": self.repo.delete(user_id)}

    def ensure_seed_data(self) -> None:
        self.repo.ensure_seed_data()

    def _to_response(self, row) -> UserResponse:
        return UserResponse(
            id=row.id,
            username=row.username,
            display_name=row.display_name,
            roles=self._parse_roles(row.roles),
            unit_code=row.unit_code,
            status=row.status,
        )

    @staticmethod
    def _parse_roles(value: str | None) -> list[str]:
        return [item.strip() for item in (value or "user").split(",") if item.strip()]
