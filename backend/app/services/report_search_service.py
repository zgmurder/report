from __future__ import annotations

from datetime import timedelta
from time import perf_counter

from fastapi import HTTPException, status

from app.core.security import CurrentUser
from app.core.time import local_now
from app.domain.report_search.definitions import DATA_SOURCES, get_dimensions, get_measures
from app.repositories.report_search_repository import ReportSearchRepository
from app.schemas.report_search import (
    ReportSearchBatchItemResult,
    ReportSearchBatchRequest,
    ReportSearchBatchResult,
    ReportSearchQuery,
    ReportSearchResult,
    SearchClassificationItem,
    SearchClassificationResponse,
    StatisticsDictionaryConfigResponse,
    StatisticsDictionaryConfigUpdate,
    StatisticsDictionarySource,
    SearchDataSource,
    SearchDepartment,
    SearchMetricItem,
    SearchMetricResponse,
    SearchOptionResponse,
    SearchResultColumn,
)


class ReportSearchService:
    def __init__(self, repository: ReportSearchRepository):
        self.repository = repository

    def options(self, current_user: CurrentUser) -> SearchOptionResponse:
        today = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
        start = today - timedelta(days=1)
        return SearchOptionResponse(
            current_department=self._department(current_user),
            data_sources=[SearchDataSource(**source) for source in DATA_SOURCES.values()],
            default_start_time=start,
            default_end_time=today,
        )

    def dictionary_config(self, current_user: CurrentUser) -> StatisticsDictionaryConfigResponse:
        self._require_admin(current_user)
        sources = []
        for source, metadata in DATA_SOURCES.items():
            sources.append(
                StatisticsDictionarySource(
                    source=source,
                    name=metadata["name"],
                    categories=[SearchClassificationItem(**row) for row in self.repository.list_all_classifications(source, "category")],
                    types=[SearchClassificationItem(**row) for row in self.repository.list_all_classifications(source, "type")],
                    details=[SearchClassificationItem(**row) for row in self.repository.list_all_classifications(source, "detail")],
                    disabled=self.repository.get_disabled_codes(source),
                )
            )
        return StatisticsDictionaryConfigResponse(sources=sources)

    def update_dictionary_config(
        self,
        request: StatisticsDictionaryConfigUpdate,
        current_user: CurrentUser,
    ) -> StatisticsDictionarySource:
        self._require_admin(current_user)
        valid = {
            "category": {row["code"] for row in self.repository.list_all_classifications(request.source, "category")},
            "type": {row["code"] for row in self.repository.list_all_classifications(request.source, "type")},
            "detail": {row["code"] for row in self.repository.list_all_classifications(request.source, "detail")},
        }
        requested = {
            "category": request.disabled_categories,
            "type": request.disabled_types,
            "detail": request.disabled_details,
        }
        for level, codes in requested.items():
            if set(codes) - valid[level]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="包含不存在的字典代码")
        self.repository.replace_disabled_codes(request.source, requested, current_user.id)
        metadata = DATA_SOURCES[request.source]
        return StatisticsDictionarySource(
            source=request.source,
            name=metadata["name"],
            categories=[SearchClassificationItem(**row) for row in self.repository.list_all_classifications(request.source, "category")],
            types=[SearchClassificationItem(**row) for row in self.repository.list_all_classifications(request.source, "type")],
            details=[SearchClassificationItem(**row) for row in self.repository.list_all_classifications(request.source, "detail")],
            disabled=requested,
        )

    def classifications(self, source: str, level: str, parent_code: str | None) -> SearchClassificationResponse:
        if source not in {"jjd_jjd", "fkd_fkd"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的数据源")
        if level not in {"category", "type", "detail"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的分类层级")
        rows = self.repository.list_classifications(source, level, parent_code)
        return SearchClassificationResponse(
            source=source,
            level=level,
            items=[SearchClassificationItem(**row) for row in rows],
        )

    def metrics(self, source: str) -> SearchMetricResponse:
        if source not in DATA_SOURCES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的数据源")
        return SearchMetricResponse(
            source=source,
            dimensions=[self._metric(item) for item in get_dimensions(source).values()],
            measures=[self._metric(item) for item in get_measures(source).values()],
        )

    def batch_query(self, request: ReportSearchBatchRequest, current_user: CurrentUser) -> ReportSearchBatchResult:
        items: list[ReportSearchBatchItemResult] = []
        seen: set[str] = set()
        for item in request.items:
            if item.block_id in seen:
                items.append(ReportSearchBatchItemResult(block_id=item.block_id, success=False, error="数据块编号重复"))
                continue
            seen.add(item.block_id)
            try:
                result = self.query(item.query, current_user)
                items.append(ReportSearchBatchItemResult(block_id=item.block_id, success=True, result=result))
            except HTTPException as exc:
                items.append(ReportSearchBatchItemResult(block_id=item.block_id, success=False, error=str(exc.detail)))
            except Exception:
                items.append(ReportSearchBatchItemResult(block_id=item.block_id, success=False, error="查询执行失败"))
        return ReportSearchBatchResult(items=items)

    def query(self, request: ReportSearchQuery, current_user: CurrentUser) -> ReportSearchResult:
        dimensions = get_dimensions(request.source)
        measures = get_measures(request.source)
        invalid_dimensions = set(request.dimensions) - set(dimensions)
        invalid_measures = set(request.measures) - set(measures)
        if invalid_dimensions or invalid_measures:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="包含不支持的查询指标")
        if "proportion" in request.measures and not any(
            (request.category_codes, request.type_codes, request.detail_codes)
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="占比指标需要先选择类别、类型或细类")
        if not current_user.unit_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前账号未配置部门")

        started = perf_counter()
        rows, executed_sql = self.repository.execute(request, current_user.unit_code)
        truncated = len(rows) > request.limit
        rows = rows[: request.limit]
        is_classification_result = not request.dimensions and any(
            (request.category_codes, request.type_codes, request.detail_codes)
        )
        if not request.dimensions:
            self._calculate_comparison_metrics(rows, request.measures, is_classification_result)
        if is_classification_result:
            level_keys = {"类别": "category", "类型": "type", "细类": "detail"}
            name_maps = {
                level: {str(item["code"]): str(item["name"]) for item in self.repository.list_all_classifications(request.source, level)}
                for level in level_keys.values()
            }
            for row in rows:
                level = level_keys.get(str(row.get("classification_level")), "")
                row["classification_name"] = name_maps.get(level, {}).get(str(row.get("classification_code")), "")
            columns = [
                SearchResultColumn(key="classification_level", label="分类层级"),
                SearchResultColumn(key="classification_name", label="分类名称"),
                SearchResultColumn(key="classification_code", label="分类代码"),
                *(SearchResultColumn(key=key, label=measures[key].label, type="number") for key in request.measures),
            ]
        else:
            columns = [
                SearchResultColumn(key=item.key, label=item.label, type=item.result_type)
                for item in [*(dimensions[key] for key in request.dimensions), *(measures[key] for key in request.measures)]
                if item.key != "proportion" or bool(request.dimensions)
            ]
        return ReportSearchResult(
            source=SearchDataSource(**DATA_SOURCES[request.source]),
            department=self._department(current_user),
            columns=columns,
            rows=rows,
            row_count=len(rows),
            elapsed_ms=round((perf_counter() - started) * 1000),
            executed_sql=executed_sql,
            truncated=truncated,
        )

    @staticmethod
    def _calculate_comparison_metrics(rows: list[dict], selected_measures: list[str], include_proportion: bool) -> None:
        for row in rows:
            current = int(row.get("event_count") or 0)
            year_base = int(row.pop("year_base_count", 0) or 0)
            period_base = int(row.pop("period_base_count", 0) or 0)
            proportion_base = int(row.pop("proportion_base_count", 0) or 0)
            calculated = {
                "event_count": current,
                "year_on_year_change": current - year_base,
                "year_on_year_rate": round((current - year_base) / year_base * 100, 2) if year_base else None,
                "period_on_period_change": current - period_base,
                "period_on_period_rate": round((current - period_base) / period_base * 100, 2) if period_base else None,
                "proportion": round(current / proportion_base * 100, 2) if include_proportion and proportion_base else None,
            }
            for key in list(row):
                if key in calculated and key not in selected_measures:
                    row.pop(key, None)
            for key in selected_measures:
                if key in calculated and (key != "proportion" or include_proportion):
                    row[key] = calculated[key]

    def _department(self, current_user: CurrentUser) -> SearchDepartment:
        code = current_user.unit_code or ""
        return SearchDepartment(code=code, name=self.repository.get_department_name(code))

    @staticmethod
    def _require_admin(current_user: CurrentUser) -> None:
        if "admin" not in current_user.roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可配置统计字典")

    @staticmethod
    def _metric(item) -> SearchMetricItem:
        return SearchMetricItem(
            key=item.key,
            label=item.label,
            description=item.description,
            default=item.default,
        )
