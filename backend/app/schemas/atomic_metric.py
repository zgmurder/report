from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AtomicMetricQueryRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    data_source: str | None = None
    dept_code: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    document_type: str | None = None
    category_code: str | None = None
    category_name: str | None = None
    type_code: str | None = None
    subtype_code: str | None = None
    include_yoy: bool = False
    include_mom: bool = False
    include_share: bool = False
    include_mom_count: bool = False
    include_yoy_count: bool = False
    include_cumulative: bool = False
    include_dim_combo: bool = False
    dim_combo_levels: str | None = None
    include_category_share: bool = False
    include_type_share: bool = False
    include_subtype_share: bool = False
    include_hot_community: bool = False
    org_dimension: str | None = None
    include_hot_period: bool = False
    hot_period_hours: int | None = None
    include_region_table: bool = False
    filter_duplicate: bool = False
    exclude_non_police: bool = False
    exclude_traffic: bool = False
    filter_self_received: bool = False
    exclude_self_received: bool = False
    tag_package_id: int | None = None
    yoy_trend: str | None = None
    trend_compare: str | None = None
    yoy_analysis_drill: str | None = None
    yoy_trend_top_n: int | None = None
    rank_sort_by: str | None = None
    rank_sort_order: str | None = None
    count_threshold_op: str | None = None
    count_threshold_value: float | None = None
    include_warning: bool = False
    warning_rule_type: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class AtomicMetricQueryResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total: int | float | None = None
    yoy: float | None = None
    mom: float | None = None
    yoy_change: str | None = None
    mom_change: str | None = None
    yoy_count: int | float | None = None
    mom_count: int | float | None = None
    cumulative: int | float | None = None
    dim_combo: str | None = None
    dim_table_headers: list[str] | None = None
    dim_table_rows: list[list[str]] | None = None
    share: float | None = None
    category_share: str | None = None
    type_share: str | None = None
    subtype_share: str | None = None
    hot_communities: str | None = None
    org_units: str | None = None
    hot_periods: str | None = None
    regions: str | None = None
    yoy_stations: str | None = None
    warning_text: str | None = None
    table_title: str | None = None
    table_headers: list[str] | None = None
    table_rows: list[list[str]] | None = None
    html_fragment: str | None = None
    field_values: dict[str, Any] = Field(default_factory=dict)
    content_segments: list[dict[str, Any]] = Field(default_factory=list)
    text_content: str | None = None
    executed_sql: str | None = None
