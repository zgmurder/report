from datetime import datetime

from pydantic import BaseModel, Field


class DepartmentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    code: str = Field(..., min_length=1, max_length=32)
    parent_id: int | None = None
    sort_order: int = 0
    status: str = "enabled"


class DepartmentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=32)
    parent_id: int | None = None
    sort_order: int | None = None
    status: str | None = None


class DepartmentItem(BaseModel):
    id: int
    name: str
    code: str
    parent_id: int | None = None
    sort_order: int
    status: str
    created_at: datetime
    updated_at: datetime


class DepartmentTreeItem(DepartmentItem):
    children: list["DepartmentTreeItem"] = Field(default_factory=list)
