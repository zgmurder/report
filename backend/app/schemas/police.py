from datetime import datetime

from pydantic import BaseModel, Field


class PoliceEventQuery(BaseModel):
    start_time: datetime | None = None
    end_time: datetime | None = None
    keyword: str | None = None
    event_type: str | None = None
    unit_code: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class PoliceEventItem(BaseModel):
    id: str
    alarm_time: datetime | None = None
    event_type: str | None = None
    unit_name: str | None = None
    address: str | None = None
    summary: str | None = None


class PoliceOverview(BaseModel):
    total: int
    by_type: list[dict] = Field(default_factory=list)
    by_unit: list[dict] = Field(default_factory=list)
    trend: list[dict] = Field(default_factory=list)
