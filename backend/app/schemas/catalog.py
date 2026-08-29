from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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
