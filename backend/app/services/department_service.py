from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, is_admin
from app.repositories.department_repository import DepartmentRepository
from app.schemas.department import DepartmentCreateRequest, DepartmentItem, DepartmentTreeItem, DepartmentUpdateRequest


class DepartmentService:
    def __init__(self, db: Session, current_user: CurrentUser):
        self.repository = DepartmentRepository(db)
        self.current_user = current_user

    def list(self, include_disabled: bool = False) -> list[DepartmentItem]:
        return [self._to_item(row) for row in self.repository.list(include_disabled=include_disabled)]

    def tree(self, include_disabled: bool = False) -> list[DepartmentTreeItem]:
        return self.repository.tree(include_disabled=include_disabled)

    def create(self, req: DepartmentCreateRequest) -> DepartmentItem:
        self._require_admin()
        self._validate_parent(req.parent_id)
        try:
            return self._to_item(self.repository.create(req))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    def update(self, department_id: int, req: DepartmentUpdateRequest) -> DepartmentItem:
        self._require_admin()
        if req.parent_id == department_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="上级部门不能选择自身")
        if req.parent_id is not None:
            self._validate_parent(req.parent_id)
        try:
            row = self.repository.update(department_id, req)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="部门不存在")
        return self._to_item(row)

    def delete(self, department_id: int) -> dict[str, bool]:
        self._require_admin()
        deleted = self.repository.delete(department_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="部门不存在")
        return {"deleted": True}

    def _require_admin(self) -> None:
        if not is_admin(self.current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    def _validate_parent(self, parent_id: int | None) -> None:
        if parent_id is None:
            return
        parent = self.repository.get(parent_id)
        if not parent or parent.status != "enabled":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="上级部门不存在或已停用")

    def _to_item(self, row) -> DepartmentItem:
        return DepartmentItem(
            id=row.id,
            name=row.name,
            code=row.code,
            parent_id=row.parent_id,
            sort_order=row.sort_order,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
