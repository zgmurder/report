from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReportTemplateCreateRequest(BaseModel):
    name: str
    category: str = "daily"
    description: str = ""
    content_json: dict[str, Any] = Field(default_factory=dict)
    status: str = "enabled"


class ReportTemplateUpdateRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    content_json: dict[str, Any] | None = None
    status: str | None = None


class ReportTemplateItem(BaseModel):
    id: int
    name: str
    category: str
    description: str = ""
    status: str
    created_at: datetime
    updated_at: datetime


class ReportTemplateDetail(ReportTemplateItem):
    content_json: dict[str, Any] = Field(default_factory=dict)


class StatComponentCreateRequest(BaseModel):
    name: str
    component_type: str = "text"
    data_source: str = "本地警情库"
    usage: str = ""
    config_json: dict[str, Any] = Field(default_factory=dict)
    status: str = "enabled"


class StatComponentUpdateRequest(BaseModel):
    name: str | None = None
    component_type: str | None = None
    data_source: str | None = None
    usage: str | None = None
    config_json: dict[str, Any] | None = None
    status: str | None = None


class StatComponentItem(BaseModel):
    id: int
    name: str
    component_type: str
    data_source: str
    usage: str = ""
    config_json: dict[str, Any] = Field(default_factory=dict)
    status: str
    created_at: datetime
    updated_at: datetime


class DataSourceCreateRequest(BaseModel):
    name: str
    source_type: str = "mysql"
    address: str = ""
    description: str = ""
    config_json: dict[str, Any] = Field(default_factory=dict)
    status: str = "enabled"


class DataSourceUpdateRequest(BaseModel):
    name: str | None = None
    source_type: str | None = None
    address: str | None = None
    description: str | None = None
    config_json: dict[str, Any] | None = None
    status: str | None = None


class DataSourceItem(BaseModel):
    id: int
    name: str
    source_type: str
    address: str = ""
    description: str = ""
    config_json: dict[str, Any] = Field(default_factory=dict)
    status: str
    created_at: datetime
    updated_at: datetime
