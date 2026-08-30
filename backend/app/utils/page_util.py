"""分页工具（同步 Session）。"""

from __future__ import annotations

import math
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy import Row, Select, func, select
from sqlalchemy.orm import Session

from app.utils.camel_case import CamelCaseUtil

T = TypeVar("T")


class PageModel(BaseModel, Generic[T]):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    rows: list[T] = Field(default_factory=list, description="记录列表")
    page_num: int = Field(description="当前页码")
    page_size: int = Field(description="每页记录数")
    total: int = Field(description="总记录数")
    has_next: bool = Field(default=False, description="是否有下一页")


class PageUtil:
    @classmethod
    def get_page_obj(cls, data_list: list, page_num: int, page_size: int) -> PageModel:
        start = (page_num - 1) * page_size
        end = page_num * page_size
        paginated_data = data_list[start:end]
        has_next = math.ceil(len(data_list) / page_size) > page_num if page_size else False
        return PageModel(
            rows=paginated_data,
            page_num=page_num,
            page_size=page_size,
            total=len(data_list),
            has_next=has_next,
        )

    @classmethod
    def paginate(
        cls,
        db: Session,
        query: Select,
        page_num: int,
        page_size: int,
        is_page: bool = False,
    ) -> PageModel | list[dict[str, Any] | list[dict[Any, Any]]]:
        if is_page:
            total = db.execute(select(func.count("*")).select_from(query.subquery())).scalar() or 0
            query_result = db.execute(query.offset((page_num - 1) * page_size).limit(page_size))
            paginated_data: list[Row] = []
            for row in query_result:
                if row and len(row) == 1:
                    paginated_data.append(row[0])
                else:
                    paginated_data.append(row)
            has_next = math.ceil(total / page_size) > page_num if page_size else False
            return PageModel(
                rows=CamelCaseUtil.transform_result(paginated_data),
                page_num=page_num,
                page_size=page_size,
                total=total,
                has_next=has_next,
            )

        query_result = db.execute(query)
        no_paginated_data: list[Row] = []
        for row in query_result:
            if row and len(row) == 1:
                no_paginated_data.append(row[0])
            else:
                no_paginated_data.append(row)
        return CamelCaseUtil.transform_result(no_paginated_data)


def page_to_data(page: PageModel | dict | Any, extra: dict | None = None) -> dict:
    """把 PageModel 展平为 API data 字典。"""
    if isinstance(page, PageModel):
        data = page.model_dump(by_alias=True)
    elif hasattr(page, "model_dump"):
        data = page.model_dump(by_alias=True)
    elif isinstance(page, dict):
        data = dict(page)
    else:
        data = {
            "rows": getattr(page, "rows", []),
            "total": getattr(page, "total", 0),
            "pageNum": getattr(page, "page_num", getattr(page, "pageNum", 1)),
            "pageSize": getattr(page, "page_size", getattr(page, "pageSize", 20)),
        }
    if extra:
        data.update(extra)
    return data
