from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class SearchDepartment(BaseModel):
    code: str
    name: str


class SearchDataSource(BaseModel):
    key: str
    name: str
    enabled: bool = True


class SearchOptionResponse(BaseModel):
    current_department: SearchDepartment
    data_sources: list[SearchDataSource]
    default_start_time: datetime
    default_end_time: datetime


class SearchClassificationItem(BaseModel):
    code: str
    name: str


class SearchClassificationResponse(BaseModel):
    source: str
    level: Literal["category", "type", "detail"]
    items: list[SearchClassificationItem]


class StatisticsDictionarySource(BaseModel):
    source: str
    name: str
    categories: list[SearchClassificationItem]
    types: list[SearchClassificationItem]
    details: list[SearchClassificationItem]
    disabled: dict[Literal["category", "type", "detail"], list[str]]


class StatisticsDictionaryConfigResponse(BaseModel):
    sources: list[StatisticsDictionarySource]


class StatisticsDictionaryConfigUpdate(BaseModel):
    source: Literal["jjd_jjd", "fkd_fkd"]
    disabled_categories: list[str] = Field(default_factory=list)
    disabled_types: list[str] = Field(default_factory=list)
    disabled_details: list[str] = Field(default_factory=list)


class SearchMetricItem(BaseModel):
    key: str
    label: str
    description: str = ""
    default: bool = False


class SearchMetricResponse(BaseModel):
    source: str
    dimensions: list[SearchMetricItem]
    measures: list[SearchMetricItem]


class ReportSearchQuery(BaseModel):
    source: Literal["jjd_jjd", "fkd_fkd"] = "jjd_jjd"
    start_time: datetime
    end_time: datetime
    category_codes: list[str] = Field(default_factory=list, max_length=500)
    type_codes: list[str] = Field(default_factory=list, max_length=500)
    detail_codes: list[str] = Field(default_factory=list, max_length=500)
    dimensions: list[str] = Field(default_factory=list, max_length=3)
    measures: list[str] = Field(default_factory=lambda: ["event_count"], min_length=1, max_length=6)
    limit: int = Field(default=100, ge=1, le=500)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_time <= self.start_time:
            raise ValueError("结束时间必须晚于开始时间")
        if (self.end_time - self.start_time).days > 366:
            raise ValueError("单次查询时间范围不能超过 366 天")
        return self


class ReportSearchBatchItem(BaseModel):
    block_id: str = Field(..., min_length=1, max_length=100)
    query: ReportSearchQuery


class ReportSearchBatchRequest(BaseModel):
    items: list[ReportSearchBatchItem] = Field(..., min_length=1, max_length=50)


class SearchResultColumn(BaseModel):
    key: str
    label: str
    type: Literal["text", "number", "datetime"] = "text"


class ReportSearchResult(BaseModel):
    source: SearchDataSource
    department: SearchDepartment
    columns: list[SearchResultColumn]
    rows: list[dict[str, Any]]
    row_count: int
    elapsed_ms: int
    executed_sql: str
    truncated: bool = False


class ReportSearchBatchItemResult(BaseModel):
    block_id: str
    success: bool
    result: ReportSearchResult | None = None
    error: str | None = None


class ReportSearchBatchResult(BaseModel):
    items: list[ReportSearchBatchItemResult]
