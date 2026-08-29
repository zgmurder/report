from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_serializer

from app.core.timeutil import to_iso_cn

ReportStatus = Literal["draft", "confirmed", "archived"]


class ReportSection(BaseModel):
    id: str
    title: str
    type: str = "paragraph"
    content: str | None = None
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    source: list[str] = Field(default_factory=list)
    ai_generated: bool = False


class ReportContent(BaseModel):
    title: str
    type: str
    params: dict[str, Any] = Field(default_factory=dict)
    sections: list[ReportSection] = Field(default_factory=list)


class ReportCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    report_type: str = Field(default="monthly", min_length=1, max_length=50)
    folder_id: int | None = None
    source_query: dict[str, Any] = Field(default_factory=dict)


class ReportUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    folder_id: int | None = None
    status: ReportStatus | None = None


class ReportSaveRequest(BaseModel):
    content_json: ReportContent
    html_snapshot: str | None = None


class ReportGenerateRequest(BaseModel):
    report_type: str = "monthly"
    source_query: dict[str, Any] = Field(default_factory=dict)


class ReportItem(BaseModel):
    id: int
    title: str
    report_type: str
    status: ReportStatus
    folder_id: int | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        return to_iso_cn(value)


class ReportDetail(ReportItem):
    source_query: dict[str, Any] = Field(default_factory=dict)
    content_json: ReportContent | None = None
    draft_json: ReportContent | None = None
    html_snapshot: str | None = None


class AiDraftResponse(BaseModel):
    draft_json: ReportContent
    explanation: str
    warnings: list[str] = Field(default_factory=list)


class ReportFolderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    parent_id: int | None = None


class ReportFolderUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    parent_id: int | None = None
    sort_order: int | None = None


class ReportFolderItem(BaseModel):
    id: int
    name: str
    parent_id: int | None = None
    sort_order: int = 0
    report_count: int = 0
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        return to_iso_cn(value)
