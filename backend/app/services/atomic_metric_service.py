"""原子模式指标查询编排。

SQL 拼装请改：module_intelligence/service/atomic_metric_sql.py
本文件负责：参数合并、执行查询、结果格式化与组装。
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.atomic_metric.exceptions import ServiceException
from app.schemas.atomic_metric import AtomicMetricQueryRequest, AtomicMetricQueryResult
from app.schemas.warning import (
    IntelligenceDayRiseWarningQueryModel,
    IntelligencePcsMxWarningQueryModel,
    IntelligenceRepeatWarningQueryModel,
    IntelligenceSuspectWarningQueryModel,
    IntelligenceWeekRiseWarningQueryModel,
)
from app.domain.atomic_metric.sql import AtomicMetricSql
from app.domain.atomic_metric.community_org_map import (
    fold_community_rows_by_org,
    normalize_org_dimension,
    org_dimension_label,
)
from app.domain.atomic_metric.schema_context import ComponentSchemaContext
from app.domain.atomic_metric.sql_executor import ComponentSqlExecutor
from app.domain.atomic_metric.sql_rules import normalize_unit_name_display
from app.services.tag_service import TagService
from app.services.warning.day_rise_warning_service import DayRiseWarningService
from app.services.warning.incident_category_service import IncidentCategoryService
from app.services.warning.mx_pcs_warning_service import MX_PCS_WARNING_SERVICES
from app.services.warning.repeat_warning_service import RepeatWarningService
from app.services.warning.suspect_warning_service import SuspectWarningService
from app.services.warning.week_rise_warning_service import WeekRiseWarningService


def build_stats_table_html(*args, **kwargs):
    return ""


class ComponentRenderService:
    @staticmethod
    def _dict_label_map(db, code):
        return {}


class FeedbackCategoryService:
    @staticmethod
    def tree(db):
        return []


class DataSourceDao:
    @staticmethod
    def get_by_code(db, code):
        return None


YoyTrend = Literal['up', 'down', 'flat', 'analysis']
TrendCompare = Literal['yoy', 'mom', 'share']
RankSortBy = Literal['count', 'yoy', 'mom', 'share']
RankSortOrder = Literal['asc', 'desc']
YoyAnalysisDrill = Literal['category', 'type']


def _normalize_yoy_analysis_drill(raw: Any) -> YoyAnalysisDrill | None:
    text = str(raw or '').strip().lower()
    if text in {'category', '类别', '类别分析'}:
        return 'category'
    if text in {'type', '类型', '类型分析'}:
        return 'type'
    return None


def _pick(params: dict[str, Any], *keys: str) -> str:
    """取参数文本；list/tuple 用逗号拼接（多选维度）。"""
    for key in keys:
        value = params.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            parts = [str(item).strip() for item in value if str(item).strip()]
            if parts:
                return ','.join(parts)
            continue
        text = str(value).strip()
        if text:
            if ',' in text:
                parts = [part.strip() for part in text.split(',') if part.strip()]
                return ','.join(parts) if parts else ''
            return text
    return ''


def _as_number(value: Any) -> int | float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num.is_integer():
        return int(num)
    return round(num, 1)


def _format_metric_value(value: Any) -> str:
    num = _as_number(value)
    if num is None:
        return str(value or '')
    return str(num)


def _format_change_phrase(value: Any) -> str:
    """同比/环比文案：上升 xx% / 下降 xx% / 持平。"""
    num = _as_number(value)
    if num is None:
        return '持平'
    if num > 0:
        return f'上升{_format_metric_value(num)}%'
    if num < 0:
        return f'下降{_format_metric_value(abs(num))}%'
    return '持平'


def _normalize_yoy_trend(value: Any) -> YoyTrend | None:
    text = str(value or '').strip().lower()
    aliases = {
        'up': 'up',
        '上升': 'up',
        '升幅': 'up',
        '同比上升': 'up',
        '环比上升': 'up',
        '占比上升': 'up',
        'down': 'down',
        '下降': 'down',
        '降幅': 'down',
        '同比下降': 'down',
        '环比下降': 'down',
        '占比下降': 'down',
        'flat': 'flat',
        '持平': 'flat',
        '同比持平': 'flat',
        '环比持平': 'flat',
        '占比持平': 'flat',
        'analysis': 'analysis',
        'analyze': 'analysis',
        'auto': 'analysis',
        '自动': 'analysis',
        '同比分析': 'analysis',
        '环比分析': 'analysis',
        '占比分析': 'analysis',
        '分析': 'analysis',
    }
    return aliases.get(text)  # type: ignore[return-value]


def _normalize_trend_compare(value: Any) -> TrendCompare | None:
    text = str(value or '').strip().lower()
    aliases = {
        'yoy': 'yoy',
        '同比': 'yoy',
        'mom': 'mom',
        '环比': 'mom',
        'share': 'share',
        '占比': 'share',
    }
    return aliases.get(text)  # type: ignore[return-value]


def _trend_compare_label(compare: TrendCompare) -> str:
    return {'yoy': '同比', 'mom': '环比', 'share': '占比'}[compare]


def _normalize_rank_sort_by(value: Any) -> RankSortBy:
    text = str(value or '').strip().lower()
    aliases = {
        'count': 'count',
        '数量': 'count',
        'total': 'count',
        'yoy': 'yoy',
        '同比': 'yoy',
        'mom': 'mom',
        '环比': 'mom',
        'share': 'share',
        '占比': 'share',
    }
    return aliases.get(text, 'count')  # type: ignore[return-value]


def _normalize_rank_sort_order(value: Any) -> RankSortOrder:
    text = str(value or '').strip().lower()
    aliases = {
        'asc': 'asc',
        'ascending': 'asc',
        '升序': 'asc',
        'desc': 'desc',
        'descending': 'desc',
        '降序': 'desc',
    }
    return aliases.get(text, 'desc')  # type: ignore[return-value]


def _format_station_yoy_pct(value: Any) -> str:
    """保留正负号：下降为负（如 -33.33%），上升为正。"""
    if value is None:
        return '—'
    try:
        num = float(value)
    except (TypeError, ValueError):
        return '—'
    if num == int(num):
        return f'{int(num)}%'
    return f'{num:.2f}'.rstrip('0').rstrip('.') + '%'


def _match_yoy_trend(yoy: float | None, trend: YoyTrend) -> bool:
    if trend == 'analysis':
        return yoy is not None
    if yoy is None:
        return False
    if trend == 'up':
        return yoy > 0
    if trend == 'down':
        return yoy < 0
    # 持平：同比为 0（去年基数为 0 时 yoy 为 NULL，不算持平）
    return abs(yoy) < 1e-9


def _cn_top_n_label(n: int) -> str:
    mapping = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九', 10: '十'}
    return mapping.get(int(n), str(n))


class AtomicMetricService:
    """按数据源表结构动态拼 COUNT + 可选同比/环比/下级所趋势。"""

    @classmethod
    def query(cls, db: Session, body: AtomicMetricQueryRequest) -> AtomicMetricQueryResult:
        merged = cls._merge_params(body)
        data_source = _pick(merged, 'data_source', 'dataSource') or 'fkd_fkd'
        date_start = _pick(merged, 'date_start', 'dateStart')
        date_end = _pick(merged, 'date_end', 'dateEnd')
        if not date_start or not date_end:
            raise ServiceException(message='请先设置时间范围')

        # 研判包命中单号对应反馈单 fkd_fkd.cjdbh，jjd_jjd 对不上，选包后强制走 fkd
        tag_package_id = cls._resolve_tag_package_id(merged, body)
        # 刑事/行政治安/交通：案件定性或交警中队在反馈单；仅本次查询切 fkd，不改前端全局 dataSource
        force_feedback = bool(tag_package_id) or cls._should_force_feedback_by_case_category(
            merged, data_source
        )
        if force_feedback:
            data_source = 'fkd_fkd'
            merged['data_source'] = data_source
            merged['dataSource'] = data_source
            # 维度列用反馈单 ajlbbh/ajlxbh/ajxlbh，勿沿用接警 documentType=incident
            merged['document_type'] = 'feedback'
            merged['documentType'] = 'feedback'

        schema = ComponentSchemaContext.resolve(data_source)
        columns = {str(item.get('column_name') or '').lower() for item in schema.columns}
        dim_filters = AtomicMetricSql.resolve_dimension_filters(columns, data_source, merged)
        has_dimension = any(
            _pick(merged, key)
            for key in (
                'category_code',
                'type_code',
                'subtype_code',
                'ajlb',
                'ajlx',
                'ajxl',
                'bjlb',
                'bjlx',
                'bjxl',
            )
        )
        # 口径见 atomic_metric_sql.AtomicMetricSql.resolve_metric_scope
        time_col, dept_expr, dept_prefix_len = AtomicMetricSql.resolve_metric_scope(
            columns,
            data_source,
            has_dimension=has_dimension,
            for_tag_package=bool(tag_package_id),
        )
        total_agg = AtomicMetricSql.resolve_total_agg(columns, data_source)
        count_id = AtomicMetricSql.resolve_case_id_expr(columns, data_source)

        include_yoy = bool(merged.get('include_yoy') or merged.get('includeYoy'))
        include_mom = bool(merged.get('include_mom') or merged.get('includeMom'))
        include_share = bool(merged.get('include_share') or merged.get('includeShare'))
        include_yoy_count = bool(
            merged.get('include_yoy_count') or merged.get('includeYoyCount')
        )
        include_mom_count = bool(
            merged.get('include_mom_count') or merged.get('includeMomCount')
        )
        include_cumulative = bool(
            merged.get('include_cumulative')
            or merged.get('includeCumulative')
            or merged.get('cumulative')
        )
        include_dim_combo = bool(
            merged.get('include_dim_combo') or merged.get('includeDimCombo')
        )
        dim_combo_levels_raw = str(
            _pick(merged, 'dim_combo_levels', 'dimComboLevels') or body.dim_combo_levels or ''
        ).strip()
        include_category_share = bool(
            merged.get('include_category_share') or merged.get('includeCategoryShare')
        )
        include_type_share = bool(merged.get('include_type_share') or merged.get('includeTypeShare'))
        include_subtype_share = bool(
            merged.get('include_subtype_share') or merged.get('includeSubtypeShare')
        )
        include_hot_community = bool(
            merged.get('include_hot_community') or merged.get('includeHotCommunity')
        )
        org_dimension = normalize_org_dimension(
            merged.get('org_dimension')
            or merged.get('orgDimension')
            or body.org_dimension
        )
        include_hot_period = bool(
            merged.get('include_hot_period') or merged.get('includeHotPeriod')
        )
        hot_period_hours = cls._resolve_hot_period_hours(merged, body)
        include_region_table = bool(
            merged.get('include_region_table') or merged.get('includeRegionTable')
        )
        include_warning = bool(
            merged.get('include_warning')
            or merged.get('includeWarning')
            or merged.get('warning')
        )
        warning_rule_type = str(
            _pick(merged, 'warning_rule_type', 'warningRuleType', 'warning_rule', 'warningRule')
            or ''
        ).strip()
        if include_warning and warning_rule_type not in {
            'dayRise',
            'weekRise',
            'suspect',
            'repeat',
            'pcsDayHb30',
            'pcsWeekHb30',
            'pcsMonthHb30',
            'pcsMonthTb30',
        }:
            raise ServiceException(message='请选择预警规则')
        filter_duplicate = bool(
            merged.get('filter_duplicate')
            or merged.get('filterDuplicate')
            or merged.get('only_duplicate')
            or merged.get('onlyDuplicate')
        )
        exclude_non_police = bool(
            merged.get('exclude_non_police')
            or merged.get('excludeNonPolice')
            or merged.get('filter_exclude_non_police')
            or merged.get('filterExcludeNonPolice')
        )
        exclude_traffic = bool(
            merged.get('exclude_traffic')
            or merged.get('excludeTraffic')
            or merged.get('filter_exclude_traffic')
            or merged.get('filterExcludeTraffic')
        )
        filter_self_received = bool(
            merged.get('filter_self_received')
            or merged.get('filterSelfReceived')
            or merged.get('self_received')
            or merged.get('selfReceived')
        )
        exclude_self_received = bool(
            merged.get('exclude_self_received')
            or merged.get('excludeSelfReceived')
            or merged.get('filter_exclude_self_received')
            or merged.get('filterExcludeSelfReceived')
        )
        if filter_self_received and exclude_self_received:
            raise ServiceException(message='不能同时勾选自接警与除自接警')
        yoy_trend = _normalize_yoy_trend(
            merged.get('yoy_trend') or merged.get('yoyTrend') or body.yoy_trend
        )
        trend_compare = cls._resolve_trend_compare(
            merged, body, include_yoy=include_yoy, include_mom=include_mom, include_share=include_share
        )
        package_case_ids: list[str] | None = None
        package_extra_where = ''
        package_extra_where_a = ''
        package_extra_where_b = ''
        package_bind: dict[str, Any] = {}
        if tag_package_id:
            # 同比/环比/地区同比窗需要历史期单号；若只按当期取 cjdbh，基期恒为 0 → 0%/持平
            need_yoy_window = bool(
                include_yoy
                or include_yoy_count
                or include_region_table
                or yoy_trend
                or trend_compare in {'yoy', 'share'}
            )
            need_mom_window = bool(
                include_mom
                or include_mom_count
                or (yoy_trend and trend_compare == 'mom')
            )
            pkg_begin, pkg_end = cls._resolve_package_case_time_range(
                date_start,
                date_end,
                need_yoy=need_yoy_window,
                need_mom=need_mom_window,
                need_cumulative=include_cumulative,
            )
            package_case_ids = TagService.list_cjdbh_by_package(
                db,
                tag_package_id,
                begin_time=pkg_begin,
                end_time=pkg_end,
            )
            package_extra_where, package_bind = AtomicMetricSql.build_case_id_filter(
                columns, package_case_ids
            )
            package_extra_where_a, _ = AtomicMetricSql.build_case_id_filter(
                columns, package_case_ids, qualify_alias='a'
            )
            package_extra_where_b, _ = AtomicMetricSql.build_case_id_filter(
                columns, package_case_ids, qualify_alias='b'
            )
        category_code = _pick(merged, 'category_code', 'ajlb', 'bjlb')
        type_code = _pick(merged, 'type_code', 'ajlx', 'bjlx')
        subtype_code = _pick(merged, 'subtype_code', 'ajxl', 'bjxl', 'feedback_subtype_code')
        # 交通类别 + 辖区：保留中队/大队（分局/市局/指挥中心仍排除）
        include_squad_brigade = cls._is_traffic_category(merged)
        # 用户勾了占比：拆分文案用（须在总占比校验/互斥清零前记下）
        show_dim_share_pct = bool(include_share)
        # 总占比：需有筛选维度或「重复」；已勾类别/类型/细类/社区拆分时由拆分文案带占比
        if (
            include_share
            and not has_dimension
            and not filter_duplicate
            and not (
                include_category_share
                or include_type_share
                or include_subtype_share
                or include_hot_community
                or org_dimension
            )
        ):
            include_share = False
        # 类别/类型/细类可同时分别拆分（互不影响）；与社区/时段/辖区互斥
        # 优先 地区 > 高发时段 > 高发社区 > 类别/类型/细类拆分 > 总占比
        # 旧版 dim_combo 组合表：若显式开启则仍走组合路径并关闭单层拆分
        dim_combo_levels = [
            part.strip().lower()
            for part in dim_combo_levels_raw.replace('，', ',').split(',')
            if part.strip().lower() in {'category', 'type', 'subtype'}
        ]
        seen_levels: set[str] = set()
        dim_combo_levels = [
            level for level in dim_combo_levels if not (level in seen_levels or seen_levels.add(level))
        ]
        if include_dim_combo and not dim_combo_levels:
            if include_category_share:
                dim_combo_levels.append('category')
            if include_type_share:
                dim_combo_levels.append('type')
            if include_subtype_share:
                dim_combo_levels.append('subtype')
        if include_dim_combo and dim_combo_levels:
            include_category_share = False
            include_type_share = False
            include_subtype_share = False
            include_hot_community = False
            include_hot_period = False
            include_region_table = False
            include_share = False
            org_dimension = None
        elif include_region_table:
            include_share = False
            include_category_share = False
            include_type_share = False
            include_subtype_share = False
            include_hot_community = False
            include_hot_period = False
            org_dimension = None
        elif include_hot_period:
            include_share = False
            include_category_share = False
            include_type_share = False
            include_subtype_share = False
            include_hot_community = False
            org_dimension = None
        elif org_dimension:
            # 组织维度：按社区折叠到片区/共建委/警务区；与社区/辖区/类别拆分互斥
            include_share = False
            include_category_share = False
            include_type_share = False
            include_subtype_share = False
            include_hot_community = False
            include_hot_period = False
            include_region_table = False
        elif include_hot_community:
            # 社区可与占比/同比/环比组合；关闭总占比指标，由社区文案带占比
            include_share = False
            include_category_share = False
            include_type_share = False
            include_subtype_share = False
            include_hot_period = False
            org_dimension = None
        elif include_category_share or include_type_share or include_subtype_share:
            # 类别/类型/细类分别拆分时可并存；关闭总占比（由拆分文案带占比）
            include_share = False

        sql = AtomicMetricSql.build_total_sql(
            table_name=schema.table_name,
            time_col=time_col,
            dept_expr=dept_expr,
            dept_prefix_len=dept_prefix_len,
            dim_filters=dim_filters,
            total_agg=total_agg,
            count_id=count_id,
            include_yoy=include_yoy,
            include_mom=include_mom,
            include_yoy_count=include_yoy_count,
            include_mom_count=include_mom_count,
            columns=columns,
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            extra_where=package_extra_where,
        )
        bind = ComponentSqlExecutor.build_bind_params(
            {
                'date_start': date_start,
                'date_end': date_end,
                'dept_code': _pick(merged, 'dept_code', 'deptCode'),
                **{
                    k: v
                    for k, v in merged.items()
                    if k
                    in (
                        'ajlb',
                        'ajlx',
                        'ajxl',
                        'bjlb',
                        'bjlx',
                        'bjxl',
                        'category_code',
                        'type_code',
                        'subtype_code',
                        'feedback_category_code',
                        'feedback_type_code',
                        'feedback_subtype_code',
                    )
                },
                **package_bind,
            },
            sql,
        )
        # 维度绑定：统一写入 SQL 使用的参数名（空字符串表示不过滤）
        # 类别/类型/细类分别拆分时互不影响：总量避免把多层 AND 在一起导致 0
        share_layer_count = sum(
            1 for flag in (include_category_share, include_type_share, include_subtype_share) if flag
        )
        for param_name in dim_filters:
            if share_layer_count >= 2:
                bind[param_name] = ''
            elif include_category_share:
                if param_name in ('ajlb', 'bjlb', 'category_code') and category_code:
                    bind[param_name] = category_code
                else:
                    bind[param_name] = ''
            elif include_type_share:
                if param_name in ('ajlx', 'bjlx', 'type_code') and type_code:
                    bind[param_name] = type_code
                else:
                    bind[param_name] = ''
            elif include_subtype_share:
                if (
                    param_name in ('ajxl', 'bjxl', 'subtype_code', 'feedback_subtype_code')
                    and subtype_code
                ):
                    bind[param_name] = subtype_code
                else:
                    bind[param_name] = ''
            else:
                bind[param_name] = _pick(merged, param_name) or ''

        ds_row = DataSourceDao.get_by_code(db, data_source)
        rows = ComponentSqlExecutor.fetch_rows(db, sql, bind, data_source_row=ds_row, limit=1)
        row = rows[0] if rows else {}

        total = _as_number(row.get('total'))
        field_values: dict[str, Any] = {'total': total if total is not None else 0}
        if filter_duplicate:
            field_values['filter_duplicate'] = True
        if exclude_non_police:
            field_values['exclude_non_police'] = True
        if exclude_traffic:
            field_values['exclude_traffic'] = True
        if filter_self_received:
            field_values['filter_self_received'] = True
        if exclude_self_received:
            field_values['exclude_self_received'] = True
        if tag_package_id:
            field_values['tag_package_id'] = tag_package_id
            field_values['tag_package_case_count'] = len(package_case_ids or [])
        segments: list[dict[str, Any]] = [
            {'type': 'metric', 'field': 'total', 'expr': 'total', 'value': _format_metric_value(field_values['total'])}
        ]
        total_label = '总量'
        if filter_duplicate and tag_package_id:
            total_label = '研判包重复总量'
        elif filter_duplicate:
            total_label = '重复总量'
        elif tag_package_id:
            total_label = '研判包总量'
        if exclude_non_police:
            total_label = f'除去非警务{total_label}' if total_label != '总量' else '除去非警务总量'
        if exclude_traffic:
            total_label = f'除交通{total_label}' if total_label != '总量' else '除交通总量'
        if filter_self_received:
            total_label = f'自接警{total_label}' if total_label != '总量' else '自接警总量'
        if exclude_self_received:
            total_label = f'除自接警{total_label}' if total_label != '总量' else '除自接警总量'
        text_parts = [f'{total_label} {_format_metric_value(field_values["total"])}']
        if tag_package_id:
            text_parts.append(f'研判包命中单号 {len(package_case_ids or [])} 个')

        executed_parts = [ComponentSqlExecutor.format_executable_sql(sql, bind)]

        if include_yoy:
            yoy = _as_number(row.get('yoy'))
            field_values['yoy'] = yoy if yoy is not None else 0
            yoy_change = _format_change_phrase(field_values['yoy'])
            field_values['yoy_change'] = yoy_change
            segments.append(
                {'type': 'metric', 'field': 'yoy', 'expr': 'yoy', 'value': _format_metric_value(field_values['yoy'])}
            )
            segments.append(
                {'type': 'metric', 'field': 'yoy_change', 'expr': 'yoy_change', 'value': yoy_change}
            )
            text_parts.append(f"同比 {_format_metric_value(field_values['yoy'])}%（{yoy_change}）")
        if include_mom:
            mom = _as_number(row.get('mom'))
            field_values['mom'] = mom if mom is not None else 0
            mom_change = _format_change_phrase(field_values['mom'])
            field_values['mom_change'] = mom_change
            segments.append(
                {'type': 'metric', 'field': 'mom', 'expr': 'mom', 'value': _format_metric_value(field_values['mom'])}
            )
            segments.append(
                {'type': 'metric', 'field': 'mom_change', 'expr': 'mom_change', 'value': mom_change}
            )
            text_parts.append(f"环比 {_format_metric_value(field_values['mom'])}%（{mom_change}）")

        if include_yoy_count:
            yoy_count = _as_number(row.get('yoy_count'))
            field_values['yoy_count'] = yoy_count if yoy_count is not None else 0
            segments.append(
                {
                    'type': 'metric',
                    'field': 'yoy_count',
                    'expr': 'yoy_count',
                    'value': _format_metric_value(field_values['yoy_count']),
                }
            )
            text_parts.append(f"同比数 {_format_metric_value(field_values['yoy_count'])}起")
        if include_mom_count:
            mom_count = _as_number(row.get('mom_count'))
            field_values['mom_count'] = mom_count if mom_count is not None else 0
            segments.append(
                {
                    'type': 'metric',
                    'field': 'mom_count',
                    'expr': 'mom_count',
                    'value': _format_metric_value(field_values['mom_count']),
                }
            )
            text_parts.append(f"环比数 {_format_metric_value(field_values['mom_count'])}起")

        if include_cumulative:
            year_start = cls._year_start_datetime(str(date_end))
            cum_sql = AtomicMetricSql.build_total_sql(
                table_name=schema.table_name,
                time_col=time_col,
                dept_expr=dept_expr,
                dept_prefix_len=dept_prefix_len,
                dim_filters=dim_filters,
                total_agg=total_agg,
                count_id=count_id,
                include_yoy=False,
                include_mom=False,
                columns=columns,
                filter_duplicate=filter_duplicate,
                exclude_non_police=exclude_non_police,
                exclude_traffic=exclude_traffic,
                filter_self_received=filter_self_received,
                exclude_self_received=exclude_self_received,
                extra_where=package_extra_where,
            )
            cum_bind = ComponentSqlExecutor.build_bind_params(
                {
                    'date_start': year_start,
                    'date_end': date_end,
                    'dept_code': _pick(merged, 'dept_code', 'deptCode'),
                    **{
                        k: v
                        for k, v in merged.items()
                        if k
                        in (
                            'ajlb',
                            'ajlx',
                            'ajxl',
                            'bjlb',
                            'bjlx',
                            'bjxl',
                            'category_code',
                            'type_code',
                            'subtype_code',
                            'feedback_category_code',
                            'feedback_type_code',
                            'feedback_subtype_code',
                        )
                    },
                    **package_bind,
                },
                cum_sql,
            )
            for param_name in dim_filters:
                cum_bind[param_name] = _pick(merged, param_name) or ''
            cum_rows = ComponentSqlExecutor.fetch_rows(
                db, cum_sql, cum_bind, data_source_row=ds_row, limit=1
            )
            cum_row = cum_rows[0] if cum_rows else {}
            cumulative = _as_number(cum_row.get('total'))
            field_values['cumulative'] = cumulative if cumulative is not None else 0
            field_values['cumulative_date_start'] = year_start
            segments.append(
                {
                    'type': 'metric',
                    'field': 'cumulative',
                    'expr': 'cumulative',
                    'value': _format_metric_value(field_values['cumulative']),
                }
            )
            text_parts.append(f"累计 {_format_metric_value(field_values['cumulative'])}")
            executed_parts.append(ComponentSqlExecutor.format_executable_sql(cum_sql, cum_bind))

        share_value = None
        if include_share:
            # 占比口径：
            # - 默认：维度总量 / 同范围不限维度（如 刑事/全部）
            # - 勾选重复：重复(维度)量 / 同口径去掉重复过滤（重复占该类或总量）
            # - 勾选自接警/除自接警：过滤后维度量 / 维度总量（分母不含该过滤）
            if filter_self_received or exclude_self_received:
                base_sql = AtomicMetricSql.build_total_sql(
                    table_name=schema.table_name,
                    time_col=time_col,
                    dept_expr=dept_expr,
                    dept_prefix_len=dept_prefix_len,
                    dim_filters=dim_filters,
                    total_agg=total_agg,
                    count_id=count_id,
                    include_yoy=False,
                    include_mom=False,
                    columns=columns,
                    filter_duplicate=filter_duplicate,
                    exclude_non_police=exclude_non_police,
                    exclude_traffic=exclude_traffic,
                    filter_self_received=False,
                    exclude_self_received=False,
                    extra_where=package_extra_where,
                )
            elif filter_duplicate:
                # 分母不含「重复」过滤，得到重复占比
                if has_dimension:
                    base_sql = AtomicMetricSql.build_total_sql(
                        table_name=schema.table_name,
                        time_col=time_col,
                        dept_expr=dept_expr,
                        dept_prefix_len=dept_prefix_len,
                        dim_filters=dim_filters,
                        total_agg=total_agg,
                        count_id=count_id,
                        include_yoy=False,
                        include_mom=False,
                        columns=columns,
                        filter_duplicate=False,
                        exclude_non_police=exclude_non_police,
                        exclude_traffic=exclude_traffic,
                        filter_self_received=False,
                        exclude_self_received=False,
                        extra_where=package_extra_where,
                    )
                else:
                    base_sql = AtomicMetricSql.build_base_total_sql(
                        table_name=schema.table_name,
                        time_col=time_col,
                        dept_expr=dept_expr,
                        dept_prefix_len=dept_prefix_len,
                        total_agg=total_agg,
                        columns=columns,
                        filter_duplicate=False,
                        exclude_non_police=exclude_non_police,
                        exclude_traffic=exclude_traffic,
                        filter_self_received=False,
                        extra_where=package_extra_where,
                    )
            else:
                base_sql = AtomicMetricSql.build_base_total_sql(
                    table_name=schema.table_name,
                    time_col=time_col,
                    dept_expr=dept_expr,
                    dept_prefix_len=dept_prefix_len,
                    total_agg=total_agg,
                    columns=columns,
                    filter_duplicate=filter_duplicate,
                    exclude_non_police=exclude_non_police,
                    exclude_traffic=exclude_traffic,
                    filter_self_received=False,
                    extra_where=package_extra_where,
                )
            base_bind = ComponentSqlExecutor.build_bind_params(
                {
                    'date_start': date_start,
                    'date_end': date_end,
                    'dept_code': _pick(merged, 'dept_code', 'deptCode'),
                    **{k: (_pick(merged, k) or '') for k in dim_filters},
                    **package_bind,
                },
                base_sql,
            )
            if filter_self_received or exclude_self_received or (filter_duplicate and has_dimension):
                for param_name in dim_filters:
                    base_bind[param_name] = _pick(merged, param_name) or ''
            base_rows = ComponentSqlExecutor.fetch_rows(
                db, base_sql, base_bind, data_source_row=ds_row, limit=1
            )
            base_total = _as_number((base_rows[0] if base_rows else {}).get('total')) or 0
            filtered_total = field_values.get('total') or 0
            try:
                share_value = (
                    0
                    if not base_total
                    else round(float(filtered_total) / float(base_total) * 100, 2)
                )
            except (TypeError, ValueError, ZeroDivisionError):
                share_value = 0
            # 展示去掉多余 0：12.50 -> 12.5
            if isinstance(share_value, float) and share_value == int(share_value):
                share_value = int(share_value)
            field_values['share'] = share_value
            field_values['base_total'] = base_total
            segments.append(
                {
                    'type': 'metric',
                    'field': 'share',
                    'expr': 'share',
                    'value': _format_metric_value(share_value),
                }
            )
            text_parts.append(f"占比 {_format_metric_value(share_value)}%")
            executed_parts.append(ComponentSqlExecutor.format_executable_sql(base_sql, base_bind))

        top_n = cls._resolve_yoy_trend_top_n(merged, body)
        count_threshold = cls._resolve_count_threshold(merged, body)
        rank_sort_by = cls._resolve_rank_sort_by(merged, body)
        rank_sort_order = cls._resolve_rank_sort_order(merged, body)
        if top_n:
            field_values['rank_sort_by'] = rank_sort_by
            field_values['rank_sort_order'] = rank_sort_order
        category_share_text = None
        category_rows: list[dict[str, Any]] | None = None
        dim_combo_text = None
        dim_table_headers: list[str] | None = None
        dim_table_rows: list[list[str]] | None = None
        if include_dim_combo and dim_combo_levels and not yoy_trend:
            combo_sql = AtomicMetricSql.build_dim_combo_sql(
                table_name=schema.table_name,
                time_col=time_col,
                dept_expr=dept_expr,
                dept_prefix_len=dept_prefix_len,
                dim_filters=dim_filters,
                count_id=count_id,
                columns=columns,
                data_source=data_source,
                levels=dim_combo_levels,
                filter_duplicate=filter_duplicate,
                exclude_non_police=exclude_non_police,
                exclude_traffic=exclude_traffic,
                filter_self_received=filter_self_received,
                exclude_self_received=exclude_self_received,
                extra_where=package_extra_where,
            )
            combo_bind = ComponentSqlExecutor.build_bind_params(
                {
                    'date_start': date_start,
                    'date_end': date_end,
                    'dept_code': _pick(merged, 'dept_code', 'deptCode'),
                    **{k: '' for k in dim_filters},
                    **package_bind,
                },
                combo_sql,
            )
            # 下拉有值则过滤该层；勾选但无下拉值则该层不过滤（全部）
            for param_name in dim_filters:
                if param_name in ('ajlb', 'bjlb', 'category_code') and category_code:
                    combo_bind[param_name] = category_code
                elif param_name in ('ajlx', 'bjlx', 'type_code') and type_code:
                    combo_bind[param_name] = type_code
                elif (
                    param_name in ('ajxl', 'bjxl', 'subtype_code', 'feedback_subtype_code')
                    and subtype_code
                ):
                    combo_bind[param_name] = subtype_code
                else:
                    combo_bind[param_name] = ''
            combo_rows = ComponentSqlExecutor.fetch_rows(
                db, combo_sql, combo_bind, data_source_row=ds_row, limit=2000
            )
            combo_rows = cls._resolve_dim_combo_labels(
                db, combo_rows, data_source, dim_combo_levels
            )
            executed_parts.append(
                ComponentSqlExecutor.format_executable_sql(combo_sql, combo_bind)
            )
            dim_table_headers, dim_table_rows, dim_combo_text = cls._format_dim_combo_table(
                combo_rows,
                levels=dim_combo_levels,
                top_n=top_n,
                count_threshold=count_threshold,
            )
            field_values['dim_combo'] = dim_combo_text
            field_values['dim_combo_levels'] = ','.join(dim_combo_levels)
            field_values['dim_table_headers'] = dim_table_headers
            field_values['dim_table_rows'] = dim_table_rows
            if top_n:
                field_values['yoy_trend_top_n'] = top_n
            segments.append(
                {
                    'type': 'metric',
                    'field': 'dim_combo',
                    'expr': 'dim_combo',
                    'value': dim_combo_text or '无',
                }
            )
            level_label = '·'.join(
                {'category': '类别', 'type': '类型', 'subtype': '细类'}[level]
                for level in dim_combo_levels
            )
            text_parts.append(f'{level_label} {dim_combo_text or "无"}')
            if combo_rows:
                row_sum = 0
                for crow in combo_rows:
                    try:
                        row_sum += int(float(crow.get('cur_total') or 0))
                    except (TypeError, ValueError):
                        continue
                if row_sum > 0 and not _as_number(field_values.get('total')):
                    field_values['total'] = row_sum
                    for seg in segments:
                        if seg.get('field') == 'total':
                            seg['value'] = _format_metric_value(row_sum)
                    if text_parts and str(text_parts[0]).startswith(total_label):
                        text_parts[0] = f'{total_label} {_format_metric_value(row_sum)}'

        if include_category_share:
            category_sql = AtomicMetricSql.build_category_share_sql(
                table_name=schema.table_name,
                time_col=time_col,
                dept_expr=dept_expr,
                dept_prefix_len=dept_prefix_len,
                dim_filters=dim_filters,
                count_id=count_id,
                columns=columns,
                data_source=data_source,
                filter_duplicate=filter_duplicate,
                exclude_non_police=exclude_non_police,
                exclude_traffic=exclude_traffic,
                filter_self_received=filter_self_received,
                exclude_self_received=exclude_self_received,
                extra_where=package_extra_where,
            )
            category_bind = ComponentSqlExecutor.build_bind_params(
                {
                    'date_start': date_start,
                    'date_end': date_end,
                    'dept_code': _pick(merged, 'dept_code', 'deptCode'),
                    **{k: '' for k in dim_filters},
                    **package_bind,
                },
                category_sql,
            )
            # 有勾选类别则只拆这些类别；否则拆当前范围全部类别。类型/细类始终清空。
            for param_name in dim_filters:
                if param_name in ('ajlb', 'bjlb', 'category_code') and category_code:
                    category_bind[param_name] = category_code
                else:
                    category_bind[param_name] = ''
            category_rows = ComponentSqlExecutor.fetch_rows(
                db, category_sql, category_bind, data_source_row=ds_row, limit=500
            )
            category_rows = cls._resolve_category_share_labels(
                db, category_rows, data_source
            )
            executed_parts.append(
                ComponentSqlExecutor.format_executable_sql(category_sql, category_bind)
            )
            # 与趋势联用时只出趋势列表结构，不出「刑事120起」拆分文案
            if not yoy_trend:
                category_share_text = cls._format_category_share_list(
                    category_rows,
                    top_n=top_n,
                    include_share=show_dim_share_pct,
                    include_yoy=include_yoy,
                    include_mom=include_mom,
                    include_yoy_count=include_yoy_count,
                    include_mom_count=include_mom_count,
                    count_threshold=count_threshold,
                    sort_by=rank_sort_by,
                    sort_order=rank_sort_order,
                )
                field_values['category_share'] = category_share_text
                if top_n:
                    field_values['yoy_trend_top_n'] = top_n
                    if not any(s.get('field') == 'yoy_trend_top_n' for s in segments):
                        segments.append(
                            {
                                'type': 'metric',
                                'field': 'yoy_trend_top_n',
                                'expr': 'yoy_trend_top_n',
                                'value': str(top_n),
                            }
                        )
                segments.append(
                    {
                        'type': 'metric',
                        'field': 'category_share',
                        'expr': 'category_share',
                        'value': category_share_text,
                    }
                )
                text_parts.append(
                    f'{cls._format_dim_share_label("类别", include_share=show_dim_share_pct, include_yoy=include_yoy, include_mom=include_mom, include_yoy_count=include_yoy_count, include_mom_count=include_mom_count, top_n=top_n)} '
                    f'{category_share_text or "无"}'
                )
                # 多选类别拆分时，用拆分行合计回填总量（避免类别∩类型过滤导致总量为 0）
                if category_code and category_rows:
                    row_sum = 0
                    for crow in category_rows:
                        try:
                            row_sum += int(float(crow.get('cur_total') or 0))
                        except (TypeError, ValueError):
                            continue
                    if row_sum > 0 and not _as_number(field_values.get('total')):
                        field_values['total'] = row_sum
                        for seg in segments:
                            if seg.get('field') == 'total':
                                seg['value'] = _format_metric_value(row_sum)
                        if text_parts and str(text_parts[0]).startswith(total_label):
                            text_parts[0] = f'{total_label} {_format_metric_value(row_sum)}'

        type_share_text = None
        type_rows: list[dict[str, Any]] | None = None
        if include_type_share:
            # 反馈单 ajlxbh 与接警类型码（如 10010=偷盗类）不一致：类型拆分改走接警单
            type_source = data_source
            if cls._should_query_jjd_for_incident_type_codes(db, data_source, type_code):
                type_source = 'jjd_jjd'
            if type_source != data_source:
                type_schema = ComponentSchemaContext.resolve(type_source)
                type_columns = {
                    str(item.get('column_name') or '').lower() for item in type_schema.columns
                }
                type_dim_filters = AtomicMetricSql.resolve_dimension_filters(
                    type_columns, type_source, merged
                )
                type_time_col, type_dept_expr, type_dept_prefix_len = (
                    AtomicMetricSql.resolve_metric_scope(
                        type_columns,
                        type_source,
                        has_dimension=True,
                        for_tag_package=False,
                    )
                )
                type_count_id = AtomicMetricSql.resolve_case_id_expr(type_columns, type_source)
                type_ds_row = DataSourceDao.get_by_code(db, type_source)
                type_table = type_schema.table_name
                type_extra_where = ''
            else:
                type_schema = schema
                type_columns = columns
                type_dim_filters = dim_filters
                type_time_col = time_col
                type_dept_expr = dept_expr
                type_dept_prefix_len = dept_prefix_len
                type_count_id = count_id
                type_ds_row = ds_row
                type_table = schema.table_name
                type_extra_where = package_extra_where
            type_sql = AtomicMetricSql.build_type_share_sql(
                table_name=type_table,
                time_col=type_time_col,
                dept_expr=type_dept_expr,
                dept_prefix_len=type_dept_prefix_len,
                dim_filters=type_dim_filters,
                count_id=type_count_id,
                columns=type_columns,
                data_source=type_source,
                filter_duplicate=filter_duplicate if type_source == data_source else False,
                exclude_non_police=exclude_non_police,
                exclude_traffic=exclude_traffic,
                filter_self_received=filter_self_received if type_source == data_source else False,
                exclude_self_received=exclude_self_received if type_source == data_source else False,
                extra_where=type_extra_where,
            )
            type_bind = ComponentSqlExecutor.build_bind_params(
                {
                    'date_start': date_start,
                    'date_end': date_end,
                    'dept_code': _pick(merged, 'dept_code', 'deptCode'),
                    **{k: '' for k in type_dim_filters},
                    **(package_bind if type_source == data_source else {}),
                },
                type_sql,
            )
            # 类型拆分与类别独立：只按类型过滤
            for param_name in type_dim_filters:
                if param_name in ('ajlx', 'bjlx', 'type_code') and type_code:
                    type_bind[param_name] = type_code
                else:
                    type_bind[param_name] = ''
            type_rows = ComponentSqlExecutor.fetch_rows(
                db, type_sql, type_bind, data_source_row=type_ds_row, limit=500
            )
            type_rows = cls._resolve_type_share_labels(db, type_rows, type_source)
            executed_parts.append(ComponentSqlExecutor.format_executable_sql(type_sql, type_bind))
            if not yoy_trend:
                type_share_text = cls._format_type_share_list(
                    type_rows,
                    top_n=top_n,
                    include_share=show_dim_share_pct,
                    include_yoy=include_yoy,
                    include_mom=include_mom,
                    include_yoy_count=include_yoy_count,
                    include_mom_count=include_mom_count,
                    count_threshold=count_threshold,
                    sort_by=rank_sort_by,
                    sort_order=rank_sort_order,
                )
                field_values['type_share'] = type_share_text
                if top_n:
                    field_values['yoy_trend_top_n'] = top_n
                    if not any(s.get('field') == 'yoy_trend_top_n' for s in segments):
                        segments.append(
                            {
                                'type': 'metric',
                                'field': 'yoy_trend_top_n',
                                'expr': 'yoy_trend_top_n',
                                'value': str(top_n),
                            }
                        )
                segments.append(
                    {
                        'type': 'metric',
                        'field': 'type_share',
                        'expr': 'type_share',
                        'value': type_share_text,
                    }
                )
                text_parts.append(
                    f'{cls._format_dim_share_label("类型", include_share=show_dim_share_pct, include_yoy=include_yoy, include_mom=include_mom, include_yoy_count=include_yoy_count, include_mom_count=include_mom_count, top_n=top_n)} '
                    f'{type_share_text or "无"}'
                )
                if type_code and type_rows:
                    row_sum = 0
                    for trow in type_rows:
                        try:
                            row_sum += int(float(trow.get('cur_total') or 0))
                        except (TypeError, ValueError):
                            continue
                    if row_sum > 0 and not _as_number(field_values.get('total')):
                        field_values['total'] = row_sum
                        for seg in segments:
                            if seg.get('field') == 'total':
                                seg['value'] = _format_metric_value(row_sum)
                        if text_parts and str(text_parts[0]).startswith(total_label):
                            text_parts[0] = f'{total_label} {_format_metric_value(row_sum)}'

        subtype_share_text = None
        subtype_rows: list[dict[str, Any]] | None = None
        if include_subtype_share:
            subtype_source = data_source
            if cls._should_query_jjd_for_incident_subtype_codes(
                db, data_source, subtype_code
            ):
                subtype_source = 'jjd_jjd'
            if subtype_source != data_source:
                subtype_schema = ComponentSchemaContext.resolve(subtype_source)
                subtype_columns = {
                    str(item.get('column_name') or '').lower() for item in subtype_schema.columns
                }
                subtype_dim_filters = AtomicMetricSql.resolve_dimension_filters(
                    subtype_columns, subtype_source, merged
                )
                subtype_time_col, subtype_dept_expr, subtype_dept_prefix_len = (
                    AtomicMetricSql.resolve_metric_scope(
                        subtype_columns,
                        subtype_source,
                        has_dimension=True,
                        for_tag_package=False,
                    )
                )
                subtype_count_id = AtomicMetricSql.resolve_case_id_expr(
                    subtype_columns, subtype_source
                )
                subtype_ds_row = DataSourceDao.get_by_code(db, subtype_source)
                subtype_table = subtype_schema.table_name
                subtype_extra_where = ''
            else:
                subtype_columns = columns
                subtype_dim_filters = dim_filters
                subtype_time_col = time_col
                subtype_dept_expr = dept_expr
                subtype_dept_prefix_len = dept_prefix_len
                subtype_count_id = count_id
                subtype_ds_row = ds_row
                subtype_table = schema.table_name
                subtype_extra_where = package_extra_where
            subtype_sql = AtomicMetricSql.build_subtype_share_sql(
                table_name=subtype_table,
                time_col=subtype_time_col,
                dept_expr=subtype_dept_expr,
                dept_prefix_len=subtype_dept_prefix_len,
                dim_filters=subtype_dim_filters,
                count_id=subtype_count_id,
                columns=subtype_columns,
                data_source=subtype_source,
                filter_duplicate=filter_duplicate if subtype_source == data_source else False,
                exclude_non_police=exclude_non_police,
                exclude_traffic=exclude_traffic,
                filter_self_received=(
                    filter_self_received if subtype_source == data_source else False
                ),
                exclude_self_received=(
                    exclude_self_received if subtype_source == data_source else False
                ),
                extra_where=subtype_extra_where,
            )
            subtype_bind = ComponentSqlExecutor.build_bind_params(
                {
                    'date_start': date_start,
                    'date_end': date_end,
                    'dept_code': _pick(merged, 'dept_code', 'deptCode'),
                    **{k: '' for k in subtype_dim_filters},
                    **(package_bind if subtype_source == data_source else {}),
                },
                subtype_sql,
            )
            # 细类拆分与类别/类型独立：只按细类过滤
            for param_name in subtype_dim_filters:
                if (
                    param_name in ('ajxl', 'bjxl', 'subtype_code', 'feedback_subtype_code')
                    and subtype_code
                ):
                    subtype_bind[param_name] = subtype_code
                else:
                    subtype_bind[param_name] = ''
            subtype_rows = ComponentSqlExecutor.fetch_rows(
                db, subtype_sql, subtype_bind, data_source_row=subtype_ds_row, limit=500
            )
            subtype_rows = cls._resolve_subtype_share_labels(
                db, subtype_rows, subtype_source
            )
            executed_parts.append(
                ComponentSqlExecutor.format_executable_sql(subtype_sql, subtype_bind)
            )
            if not yoy_trend:
                subtype_share_text = cls._format_subtype_share_list(
                    subtype_rows,
                    top_n=top_n,
                    include_share=show_dim_share_pct,
                    include_yoy=include_yoy,
                    include_mom=include_mom,
                    include_yoy_count=include_yoy_count,
                    include_mom_count=include_mom_count,
                    count_threshold=count_threshold,
                    sort_by=rank_sort_by,
                    sort_order=rank_sort_order,
                )
                field_values['subtype_share'] = subtype_share_text
                if top_n:
                    field_values['yoy_trend_top_n'] = top_n
                    if not any(s.get('field') == 'yoy_trend_top_n' for s in segments):
                        segments.append(
                            {
                                'type': 'metric',
                                'field': 'yoy_trend_top_n',
                                'expr': 'yoy_trend_top_n',
                                'value': str(top_n),
                            }
                        )
                segments.append(
                    {
                        'type': 'metric',
                        'field': 'subtype_share',
                        'expr': 'subtype_share',
                        'value': subtype_share_text,
                    }
                )
                text_parts.append(
                    f'{cls._format_dim_share_label("细类", include_share=show_dim_share_pct, include_yoy=include_yoy, include_mom=include_mom, include_yoy_count=include_yoy_count, include_mom_count=include_mom_count, top_n=top_n)} '
                    f'{subtype_share_text or "无"}'
                )

        hot_communities_text = None
        org_units_text = None
        hot_community_rows: list[dict[str, Any]] = []
        need_community_rows = bool(include_hot_community or org_dimension)
        if need_community_rows:
            community_ctx = cls._resolve_community_source_context(
                db,
                data_source=data_source,
                schema=schema,
                columns=columns,
                merged=merged,
                has_dimension=has_dimension,
                tag_package_id=tag_package_id,
                package_case_ids=package_case_ids,
            )
            need_community_period = bool(
                include_yoy
                or include_mom
                or include_yoy_count
                or include_mom_count
                or rank_sort_by in {'yoy', 'mom'}
            )
            community_sql = None
            if need_community_period:
                community_sql = AtomicMetricSql.build_community_yoy_sql(
                    table_name=community_ctx['schema'].table_name,
                    time_col=community_ctx['time_col'],
                    dept_expr=community_ctx['dept_expr'],
                    dim_filters=community_ctx['dim_filters'],
                    count_id=community_ctx['count_id'],
                    columns=community_ctx['columns'],
                    data_source=community_ctx['data_source'],
                    filter_duplicate=filter_duplicate,
                    exclude_non_police=exclude_non_police,
                    exclude_traffic=exclude_traffic,
                    filter_self_received=filter_self_received,
                    exclude_self_received=exclude_self_received,
                    extra_where=community_ctx['extra_where'],
                    jjd_bridge=bool(community_ctx.get('jjd_bridge')),
                )
            else:
                community_sql = AtomicMetricSql.build_hot_community_sql(
                    table_name=community_ctx['schema'].table_name,
                    time_col=community_ctx['time_col'],
                    dept_expr=community_ctx['dept_expr'],
                    dim_filters=community_ctx['dim_filters'],
                    count_id=community_ctx['count_id'],
                    columns=community_ctx['columns'],
                    data_source=community_ctx['data_source'],
                    top_n=None if show_dim_share_pct else top_n,
                    filter_duplicate=filter_duplicate,
                    exclude_non_police=exclude_non_police,
                    exclude_traffic=exclude_traffic,
                    filter_self_received=filter_self_received,
                    exclude_self_received=exclude_self_received,
                    extra_where=community_ctx['extra_where'],
                    jjd_bridge=bool(community_ctx.get('jjd_bridge')),
                )
            if community_sql:
                community_bind = ComponentSqlExecutor.build_bind_params(
                    {
                        'date_start': date_start,
                        'date_end': date_end,
                        'dept_code': _pick(merged, 'dept_code', 'deptCode'),
                        **community_ctx['dim_bind'],
                        **community_ctx['package_bind'],
                    },
                    community_sql,
                )
                hot_community_rows = ComponentSqlExecutor.fetch_rows(
                    db,
                    community_sql,
                    community_bind,
                    data_source_row=community_ctx['ds_row'],
                    limit=500,
                )
                executed_parts.append(
                    ComponentSqlExecutor.format_executable_sql(community_sql, community_bind)
                )
                # 与趋势联用时只出趋势列表结构，不出「社区/组织N起」拆分文案
                if not yoy_trend:
                    if org_dimension:
                        org_rows = fold_community_rows_by_org(
                            hot_community_rows, org_type=org_dimension
                        )
                        org_units_text = cls._format_hot_community_list(
                            org_rows,
                            top_n=top_n,
                            include_share=show_dim_share_pct,
                            include_yoy=include_yoy,
                            include_mom=include_mom,
                            include_yoy_count=include_yoy_count,
                            include_mom_count=include_mom_count,
                            count_threshold=count_threshold,
                            sort_by=rank_sort_by,
                            sort_order=rank_sort_order,
                        )
                        field_values['org_dimension'] = org_dimension
                        field_values['org_units'] = org_units_text
                        org_label = org_dimension_label(org_dimension)
                        if top_n:
                            field_values['yoy_trend_top_n'] = top_n
                            if not any(s.get('field') == 'yoy_trend_top_n' for s in segments):
                                segments.append(
                                    {
                                        'type': 'metric',
                                        'field': 'yoy_trend_top_n',
                                        'expr': 'yoy_trend_top_n',
                                        'value': str(top_n),
                                    }
                                )
                        segments.append(
                            {
                                'type': 'metric',
                                'field': 'org_units',
                                'expr': 'org_units',
                                'value': org_units_text,
                            }
                        )
                        text_parts.append(
                            f'{cls._format_dim_share_label(org_label, include_share=show_dim_share_pct, include_yoy=include_yoy, include_mom=include_mom, include_yoy_count=include_yoy_count, include_mom_count=include_mom_count, top_n=top_n)} '
                            f'{org_units_text or "无"}'
                        )
                    elif include_hot_community:
                        hot_communities_text = cls._format_hot_community_list(
                            hot_community_rows,
                            top_n=top_n,
                            include_share=show_dim_share_pct,
                            include_yoy=include_yoy,
                            include_mom=include_mom,
                            include_yoy_count=include_yoy_count,
                            include_mom_count=include_mom_count,
                            count_threshold=count_threshold,
                            sort_by=rank_sort_by,
                            sort_order=rank_sort_order,
                        )
                        field_values['hot_communities'] = hot_communities_text
                        if top_n:
                            field_values['yoy_trend_top_n'] = top_n
                            if not any(s.get('field') == 'yoy_trend_top_n' for s in segments):
                                segments.append(
                                    {
                                        'type': 'metric',
                                        'field': 'yoy_trend_top_n',
                                        'expr': 'yoy_trend_top_n',
                                        'value': str(top_n),
                                    }
                                )
                        segments.append(
                            {
                                'type': 'metric',
                                'field': 'hot_communities',
                                'expr': 'hot_communities',
                                'value': hot_communities_text,
                            }
                        )
                        text_parts.append(
                            f'{cls._format_dim_share_label("社区", include_share=show_dim_share_pct, include_yoy=include_yoy, include_mom=include_mom, include_yoy_count=include_yoy_count, include_mom_count=include_mom_count, top_n=top_n)} '
                            f'{hot_communities_text or "无"}'
                        )
            else:
                hot_communities_text = ''
                org_units_text = ''
                if not yoy_trend:
                    if org_dimension:
                        field_values['org_dimension'] = org_dimension
                        field_values['org_units'] = ''
                        text_parts.append(f'{org_dimension_label(org_dimension)} 无')
                    elif include_hot_community:
                        field_values['hot_communities'] = ''
                        text_parts.append('社区 无')

        hot_periods_text = None
        if include_hot_period:
            period_sql = AtomicMetricSql.build_hot_period_sql(
                table_name=schema.table_name,
                time_col=time_col,
                dept_expr=dept_expr,
                dept_prefix_len=dept_prefix_len,
                dim_filters=dim_filters,
                count_id=count_id,
                columns=columns,
                hour_span=hot_period_hours,
                top_n=top_n,
                filter_duplicate=filter_duplicate,
                exclude_non_police=exclude_non_police,
                exclude_traffic=exclude_traffic,
                filter_self_received=filter_self_received,
                exclude_self_received=exclude_self_received,
                extra_where=package_extra_where,
            )
            period_bind = ComponentSqlExecutor.build_bind_params(
                {
                    'date_start': date_start,
                    'date_end': date_end,
                    'dept_code': _pick(merged, 'dept_code', 'deptCode'),
                    **{k: (_pick(merged, k) or '') for k in dim_filters},
                    **package_bind,
                },
                period_sql,
            )
            period_rows = ComponentSqlExecutor.fetch_rows(
                db, period_sql, period_bind, data_source_row=ds_row, limit=500
            )
            hot_periods_text = cls._format_hot_period_list(
                period_rows, top_n=top_n, count_threshold=count_threshold
            )
            field_values['hot_periods'] = hot_periods_text
            field_values['hot_period_hours'] = hot_period_hours
            if top_n:
                field_values['yoy_trend_top_n'] = top_n
                if not any(s.get('field') == 'yoy_trend_top_n' for s in segments):
                    segments.append(
                        {
                            'type': 'metric',
                            'field': 'yoy_trend_top_n',
                            'expr': 'yoy_trend_top_n',
                            'value': str(top_n),
                        }
                    )
            segments.append(
                {
                    'type': 'metric',
                    'field': 'hot_periods',
                    'expr': 'hot_periods',
                    'value': hot_periods_text or '无',
                }
            )
            top_hint = f'前{top_n}位' if top_n else ''
            text_parts.append(
                f'高发时段({hot_period_hours}小时){top_hint} {hot_periods_text or "无"}'
            )
            executed_parts.append(
                ComponentSqlExecutor.format_executable_sql(period_sql, period_bind)
            )

        yoy_stations = None
        regions_text = None
        table_title = None
        table_headers = None
        table_rows = None
        html_fragment = None

        # 社区 / 类别 / 类型 / 细类 + 趋势：按勾选维度做趋势，不跑派出所地区表
        use_org_yoy = bool(org_dimension and yoy_trend)
        use_community_yoy = bool(include_hot_community and yoy_trend and not org_dimension)
        use_category_yoy = bool(include_category_share and yoy_trend)
        use_type_yoy = bool(include_type_share and yoy_trend)
        use_subtype_yoy = bool(include_subtype_share and yoy_trend)
        use_dim_yoy = bool(use_category_yoy or use_type_yoy or use_subtype_yoy)
        # 地区表与下级所同比趋势共用同一份地区 SQL（只查一次）
        region_rows: list[dict[str, Any]] | None = None
        region_executed_sql: str | None = None
        if (yoy_trend or include_region_table) and not use_community_yoy and not use_org_yoy and not use_dim_yoy:
            region_rows, region_executed_sql = cls._fetch_region_station_rows(
                db,
                schema=schema,
                data_source=data_source,
                ds_row=ds_row,
                merged=merged,
                dim_filters=dim_filters,
                date_start=date_start,
                date_end=date_end,
                time_col=time_col,
                dept_expr=dept_expr,
                dept_prefix_len=dept_prefix_len,
                columns=columns,
                filter_duplicate=filter_duplicate,
                exclude_non_police=exclude_non_police,
                exclude_traffic=exclude_traffic,
                filter_self_received=filter_self_received,
                exclude_self_received=exclude_self_received,
                extra_where=package_extra_where_b,
                extra_bind=package_bind,
                include_squad_brigade=include_squad_brigade,
            )
            executed_parts.append(region_executed_sql)

        if yoy_trend:
            top_n = cls._resolve_yoy_trend_top_n(merged, body)
            compare_label = _trend_compare_label(trend_compare)
            trend_scope = 'station'
            trend_unit_kind: Literal[
                'station', 'community', 'category', 'type', 'subtype'
            ] = 'station'
            if use_community_yoy or use_org_yoy:
                community_ctx = cls._resolve_community_source_context(
                    db,
                    data_source=data_source,
                    schema=schema,
                    columns=columns,
                    merged=merged,
                    has_dimension=has_dimension,
                    tag_package_id=tag_package_id,
                    package_case_ids=package_case_ids,
                )
                community_yoy_rows = cls._fetch_community_yoy_rows(
                    db,
                    schema=community_ctx['schema'],
                    data_source=community_ctx['data_source'],
                    ds_row=community_ctx['ds_row'],
                    dim_filters=community_ctx['dim_filters'],
                    date_start=date_start,
                    date_end=date_end,
                    time_col=community_ctx['time_col'],
                    dept_expr=community_ctx['dept_expr'],
                    count_id=community_ctx['count_id'],
                    columns=community_ctx['columns'],
                    filter_duplicate=filter_duplicate,
                    exclude_non_police=exclude_non_police,
                    exclude_traffic=exclude_traffic,
                    filter_self_received=filter_self_received,
                    exclude_self_received=exclude_self_received,
                    extra_where=community_ctx['extra_where'],
                    package_bind=community_ctx['package_bind'],
                    executed_parts=executed_parts,
                    dept_code=_pick(merged, 'dept_code', 'deptCode'),
                    dim_bind=community_ctx['dim_bind'],
                    jjd_bridge=bool(community_ctx.get('jjd_bridge')),
                    # 有排名时高发社区结果已截断，社区同比需重新全量取当期
                    cur_rows=None if top_n else hot_community_rows,
                    need_mom=trend_compare == 'mom',
                )
                if use_org_yoy and org_dimension:
                    analysis_rows = fold_community_rows_by_org(
                        community_yoy_rows, org_type=org_dimension
                    )
                    trend_scope = 'org'
                    trend_unit_kind = 'community'
                    field_values['org_dimension'] = org_dimension
                else:
                    trend_scope = 'community'
                    trend_unit_kind = 'community'
                    analysis_rows = community_yoy_rows
            elif use_dim_yoy:
                if use_category_yoy:
                    analysis_rows = cls._dim_share_rows_as_trend_units(
                        category_rows or [],
                        code_keys=('category_code',),
                        name_keys=('category_name', 'category_code'),
                    )
                    trend_scope = 'category'
                    trend_unit_kind = 'category'
                elif use_type_yoy:
                    analysis_rows = cls._dim_share_rows_as_trend_units(
                        type_rows or [],
                        code_keys=('type_code',),
                        name_keys=('type_name', 'type_code'),
                    )
                    trend_scope = 'type'
                    trend_unit_kind = 'type'
                else:
                    analysis_rows = cls._dim_share_rows_as_trend_units(
                        subtype_rows or [],
                        code_keys=('subtype_code',),
                        name_keys=('subtype_name', 'subtype_code'),
                    )
                    trend_scope = 'subtype'
                    trend_unit_kind = 'subtype'
            else:
                analysis_rows = region_rows or []
                trend_scope = 'station'
                trend_unit_kind = 'station'

            # 升幅 / 降幅 / 旧 analysis：统一分析文案；flat 仍走列表筛选
            use_analysis_text = yoy_trend in ('up', 'down', 'analysis')
            top_stations: list[tuple[str, str, float]] = []
            direction: Literal['up', 'down'] | None = None
            analysis_top_n = top_n if top_n else 3
            if use_analysis_text:
                prefer: Literal['up', 'down'] | None = (
                    'up' if yoy_trend == 'up' else ('down' if yoy_trend == 'down' else None)
                )
                # 勾选排名（传了排序/前N）时吃排序/升降序；未勾排名仍按升/降幅幅度
                has_rank_sort = bool(top_n) or bool(
                    _pick(merged, 'rank_sort_by', 'rankSortBy')
                    or _pick(merged, 'rank_sort_order', 'rankSortOrder')
                    or body.rank_sort_by
                    or body.rank_sort_order
                )
                station_text, top_stations, direction = cls._format_yoy_analysis(
                    analysis_rows,
                    top_n=analysis_top_n,
                    unit_kind=trend_unit_kind,
                    compare=trend_compare,
                    prefer=prefer,
                    sort_by=rank_sort_by if has_rank_sort else None,
                    sort_order=rank_sort_order,
                    include_squad_brigade=include_squad_brigade
                    if trend_unit_kind == 'station'
                    else False,
                )
                yoy_stations = station_text
                # 仅辖区(所)级支持类别/类型下钻；升幅、降幅均可
                if trend_scope == 'station':
                    analysis_drill = _normalize_yoy_analysis_drill(
                        merged.get('yoy_analysis_drill')
                        or merged.get('yoyAnalysisDrill')
                        or body.yoy_analysis_drill
                    )
                    if analysis_drill and top_stations and direction:
                        drill_sql = AtomicMetricSql.build_station_dim_yoy_sql(
                            table_name=schema.table_name,
                            time_col=time_col,
                            dept_expr=dept_expr,
                            count_id=count_id,
                            columns=columns,
                            data_source=data_source,
                            level=analysis_drill,
                            station_param_keys=[f'st_{i}' for i in range(len(top_stations))],
                            filter_duplicate=filter_duplicate,
                            exclude_non_police=exclude_non_police,
                            exclude_traffic=exclude_traffic,
                            filter_self_received=filter_self_received,
                            exclude_self_received=exclude_self_received,
                            extra_where=package_extra_where,
                        )
                        drill_bind: dict[str, Any] = {
                            'date_start': date_start,
                            'date_end': date_end,
                            **package_bind,
                        }
                        for index, (unit_code, _name, _yoy) in enumerate(top_stations):
                            drill_bind[f'st_{index}'] = unit_code
                        drill_bind = ComponentSqlExecutor.build_bind_params(drill_bind, drill_sql)
                        dim_rows = ComponentSqlExecutor.fetch_rows(
                            db, drill_sql, drill_bind, data_source_row=ds_row, limit=2000
                        )
                        label_map = (
                            cls._build_category_label_map(db, data_source)
                            if analysis_drill == 'category'
                            else cls._build_type_label_map(db, data_source)
                        )
                        appendix = cls._format_station_dim_drill_appendix(
                            top_stations=top_stations,
                            direction=direction,
                            dim_rows=dim_rows,
                            top_n=analysis_top_n,
                            label_map=label_map,
                            unmapped_label='其他' if analysis_drill == 'type' else None,
                        )
                        if appendix:
                            yoy_stations = f'{station_text}{appendix}'
                        executed_parts.append(
                            ComponentSqlExecutor.format_executable_sql(drill_sql, drill_bind)
                        )
                        field_values['yoy_analysis_drill'] = analysis_drill
            else:
                yoy_stations = cls._format_yoy_station_list(
                    analysis_rows,
                    yoy_trend,
                    top_n=top_n,
                    unit_kind=trend_unit_kind,
                    compare=trend_compare,
                    include_squad_brigade=include_squad_brigade
                    if trend_unit_kind == 'station'
                    else False,
                )
            field_values['yoy_stations'] = yoy_stations
            field_values['trend_compare'] = trend_compare
            field_values['yoy_trend_scope'] = trend_scope
            if top_n:
                field_values['yoy_trend_top_n'] = top_n
                if not any(s.get('field') == 'yoy_trend_top_n' for s in segments):
                    segments.append(
                        {
                            'type': 'metric',
                            'field': 'yoy_trend_top_n',
                            'expr': 'yoy_trend_top_n',
                            'value': str(top_n),
                        }
                    )
            segments.append(
                {
                    'type': 'metric',
                    'field': 'yoy_stations',
                    'expr': 'yoy_stations',
                    'value': yoy_stations,
                }
            )
            scope_prefix = {
                'community': '社区',
                'org': org_dimension_label(org_dimension),
                'category': '类别',
                'type': '类型',
                'subtype': '细类',
            }.get(trend_scope, '')
            trend_label = {
                'up': f'{scope_prefix}{compare_label}升幅',
                'down': f'{scope_prefix}{compare_label}降幅',
                'flat': f'{scope_prefix}{compare_label}持平',
                'analysis': f'{scope_prefix}{compare_label}自动',
            }[yoy_trend]
            # 分析文案已含「升/降幅前N」，不再额外拼「前N位」
            top_hint = f'前{top_n}位' if top_n and not use_analysis_text else ''
            text_parts.append(f'{trend_label}{top_hint} {yoy_stations or "无"}')

        if include_region_table:
            regions_text = cls._format_region_list(
                region_rows or [],
                top_n=top_n,
                include_share=show_dim_share_pct,
                include_yoy=include_yoy,
                include_mom=include_mom,
                include_yoy_count=include_yoy_count,
                include_mom_count=include_mom_count,
                count_threshold=count_threshold,
                sort_by=rank_sort_by,
                sort_order=rank_sort_order,
                include_squad_brigade=include_squad_brigade,
            )
            field_values['regions'] = regions_text
            if top_n:
                field_values['yoy_trend_top_n'] = top_n
                if not any(s.get('field') == 'yoy_trend_top_n' for s in segments):
                    segments.append(
                        {
                            'type': 'metric',
                            'field': 'yoy_trend_top_n',
                            'expr': 'yoy_trend_top_n',
                            'value': str(top_n),
                        }
                    )
            segments.append(
                {
                    'type': 'metric',
                    'field': 'regions',
                    'expr': 'regions',
                    'value': regions_text or '无',
                }
            )
            text_parts.append(
                f'{cls._format_dim_share_label("辖区", include_share=show_dim_share_pct, include_yoy=include_yoy, include_mom=include_mom, include_yoy_count=include_yoy_count, include_mom_count=include_mom_count, top_n=top_n)} '
                f'{regions_text or "无"}'
            )

        warning_text = ''
        if include_warning:
            warning_top_n = cls._resolve_yoy_trend_top_n(merged, body)
            warning_ajlb = cls._resolve_warning_ajlb(db, merged, data_source)
            warning_text = cls._build_warning_text(
                db,
                rule_type=warning_rule_type,
                date_start=str(date_start),
                date_end=str(date_end),
                dept_code=str(_pick(merged, 'dept_code', 'deptCode') or ''),
                top_n=warning_top_n,
                ajlb=warning_ajlb,
            )
            field_values['warning_text'] = warning_text
            field_values['warning_rule_type'] = warning_rule_type
            if warning_ajlb:
                field_values['warning_ajlb'] = warning_ajlb
            if warning_top_n:
                field_values['yoy_trend_top_n'] = warning_top_n
            segments.append(
                {
                    'type': 'metric',
                    'field': 'warning_text',
                    'expr': 'warning_text',
                    'value': warning_text or '无',
                }
            )
            rule_label = {
                'dayRise': '连续三天上升',
                'weekRise': '连续两周上升',
                'suspect': '涉警前科',
                'repeat': '重复涉警',
                'pcsDayHb30': '派出所按天环比上升30%',
                'pcsWeekHb30': '派出所按周环比上升30%',
                'pcsMonthHb30': '派出所按月环比上升30%',
                'pcsMonthTb30': '派出所按月同比上升30%',
            }.get(warning_rule_type, warning_rule_type)
            top_hint = f'前{warning_top_n}位' if warning_top_n else ''
            cat_hint = f'·{warning_ajlb}' if warning_ajlb else ''
            text_parts.append(f'预警({rule_label}{cat_hint}{top_hint}) {warning_text or "无"}')

        return AtomicMetricQueryResult(
            total=field_values.get('total'),
            yoy=field_values.get('yoy'),
            mom=field_values.get('mom'),
            yoy_change=field_values.get('yoy_change'),
            mom_change=field_values.get('mom_change'),
            yoy_count=field_values.get('yoy_count'),
            mom_count=field_values.get('mom_count'),
            cumulative=field_values.get('cumulative'),
            dim_combo=dim_combo_text,
            dim_table_headers=dim_table_headers,
            dim_table_rows=dim_table_rows,
            share=share_value,
            category_share=category_share_text,
            type_share=type_share_text,
            subtype_share=subtype_share_text,
            hot_communities=hot_communities_text,
            org_units=org_units_text,
            hot_periods=hot_periods_text,
            regions=regions_text,
            yoy_stations=yoy_stations,
            warning_text=warning_text or None,
            table_title=table_title,
            table_headers=table_headers,
            table_rows=table_rows,
            html_fragment=html_fragment,
            field_values=field_values,
            content_segments=segments,
            text_content='，'.join(text_parts),
            executed_sql='\n\n'.join(executed_parts),
        )

    @classmethod
    def _calc_region_pct(cls, cur: float | int | None, base: float | int | None) -> float | None:
        """地区表 / 下级所趋势共用：(本期-基期)/基期*100；基期为 0 返回 None。"""
        try:
            cur_n = float(cur or 0)
            base_n = float(base or 0)
        except (TypeError, ValueError):
            return None
        if base_n == 0:
            return None
        return round((cur_n - base_n) * 100 / base_n, 2)

    @classmethod
    def _is_city_dept_code(cls, dept_code: str | None) -> bool:
        digits = ''.join(ch for ch in str(dept_code or '') if ch.isdigit())
        if not digits:
            return True
        stripped = digits.rstrip('0') or digits
        return len(stripped) <= 6

    @classmethod
    def _to_date_only(cls, value: str | None) -> str:
        """预警表 rq/week_end 为日期字符串；去掉时分秒，避免字符串比较漏数。"""
        text = str(value or '').strip()
        if not text:
            return ''
        # 2026-07-30 / 2026-07-30 00:00:00 / 2026-07-30T00:00:00
        return text.replace('T', ' ')[:10]

    @classmethod
    def _resolve_warning_ajlb(
        cls, db: Session, merged: dict[str, Any], data_source: str
    ) -> str | None:
        """解析预警类别过滤：优先类别名称，缺省时用类别代码反查名称；支持多选（逗号分隔）。"""
        raw_name = str(
            _pick(
                merged,
                'category_name',
                'categoryName',
                'ajlb_name',
                'bjlb_name',
                'bjlbmc',
            )
            or ''
        ).strip()
        raw_code = str(
            _pick(merged, 'category_code', 'categoryCode', 'ajlb', 'bjlb', 'bjlbdm') or ''
        ).strip()

        def _split_multi(text: str) -> list[str]:
            return [part.strip() for part in text.split(',') if part.strip()]

        name_parts = _split_multi(raw_name)
        code_parts = _split_multi(raw_code)
        # 名称若其实是编码，按代码处理
        if name_parts and all(part.isdigit() for part in name_parts):
            code_parts = code_parts or name_parts
            name_parts = []

        if not name_parts and code_parts:
            label_map = cls._build_category_label_map(db, data_source)
            resolved: list[str] = []
            for code in code_parts:
                label = str(label_map.get(code) or '').strip()
                if label:
                    resolved.append(label)
                elif code and not code.isdigit():
                    resolved.append(code)
            name_parts = resolved
        elif not name_parts and raw_code and not raw_code.isdigit() and ',' not in raw_code:
            name_parts = [raw_code]

        if not name_parts:
            return None
        # 预警表多用全角括号
        return ','.join(
            part.replace('(', '（').replace(')', '）') for part in name_parts
        )

    @classmethod
    def _normalize_report_warning_text(cls, text: str | None) -> str:
        raw = str(text or '').strip()
        if not raw:
            return ''
        return (
            raw.replace('，点击查看详情。', '。')
            .replace('点击查看详情。', '')
            .replace('点击查看详情', '')
            .strip('，；; ')
        )

    @classmethod
    def _build_warning_text(
        cls,
        db: Session,
        *,
        rule_type: str,
        date_start: str,
        date_end: str,
        dept_code: str,
        top_n: int | None = None,
        ajlb: str | None = None,
    ) -> str:
        """按规则拉取预警文案（报告口径去掉“点击查看详情”）。

        全市维度 + 涉警前科：按整段时间范围汇总为一条「全市 … 共 X 起」。
        top_n：排名前 N 条（连续三天/两周上升、派出所级摘要等按列表顺序截取）。
        ajlb：类别名称过滤（连续三天/两周上升表字段）。
        """
        begin = cls._to_date_only(date_start)
        end = cls._to_date_only(date_end) or begin
        limit = top_n if top_n and top_n >= 1 else None
        page_size = limit if limit else 50
        category = str(ajlb or '').strip() or None
        texts: list[str] = []
        if rule_type == 'suspect':
            query = IntelligenceSuspectWarningQueryModel(
                page_num=1,
                page_size=page_size,
                org_code=dept_code or None,
                begin_rq=begin or None,
                end_rq=end or None,
                view_mode='detail',
            )
            if cls._is_city_dept_code(dept_code):
                # 全市仍输出汇总句；派出所/筛选结果输出单条命中文案
                summary_query = IntelligenceSuspectWarningQueryModel(
                    page_num=1,
                    page_size=page_size,
                    org_code=dept_code or None,
                    begin_rq=begin or None,
                    end_rq=end or None,
                    view_mode='summary',
                )
                city_rows = SuspectWarningService.list_city_summaries(db, summary_query)
                total = 0
                for row in city_rows or []:
                    try:
                        total += int(row.get('alarmCount') or row.get('alarm_count') or 0)
                    except (TypeError, ValueError):
                        continue
                if total > 0:
                    texts.append(
                        cls._normalize_report_warning_text(
                            SuspectWarningService.build_summary_text('全市', begin, end, total)
                        )
                    )
            if not texts:
                page = SuspectWarningService.list_page(db, query)
                for row in page.rows or []:
                    if not isinstance(row, dict):
                        continue
                    text = cls._normalize_report_warning_text(
                        row.get('warningText') or row.get('warning_text')
                    )
                    if text:
                        texts.append(text)
        elif rule_type == 'weekRise':
            query = IntelligenceWeekRiseWarningQueryModel(
                page_num=1,
                page_size=page_size,
                org_code=dept_code or None,
                begin_rq=begin or None,
                end_rq=end or None,
                ajlb=category,
            )
            page = WeekRiseWarningService.list_page(db, query)
            for row in page.rows or []:
                if not isinstance(row, dict):
                    continue
                text = cls._normalize_report_warning_text(
                    row.get('warningText') or row.get('warning_text')
                )
                if text:
                    texts.append(text)
        elif rule_type == 'dayRise':
            query = IntelligenceDayRiseWarningQueryModel(
                page_num=1,
                page_size=page_size,
                org_code=dept_code or None,
                begin_rq=begin or None,
                end_rq=end or None,
                ajlb=category,
            )
            page = DayRiseWarningService.list_page(db, query)
            for row in page.rows or []:
                if not isinstance(row, dict):
                    continue
                text = cls._normalize_report_warning_text(
                    row.get('warningText') or row.get('warning_text')
                )
                if text:
                    texts.append(text)
        elif rule_type == 'repeat':
            query = IntelligenceRepeatWarningQueryModel(
                page_num=1,
                page_size=page_size,
                org_code=dept_code or None,
                begin_rq=begin or None,
                end_rq=end or None,
                view_mode='summary',
            )
            page = RepeatWarningService.list_page(db, query)
            for row in page.rows or []:
                if not isinstance(row, dict):
                    continue
                text = cls._normalize_report_warning_text(
                    row.get('warningText') or row.get('warning_text')
                )
                if text:
                    texts.append(text)
        elif rule_type in MX_PCS_WARNING_SERVICES:
            query = IntelligencePcsMxWarningQueryModel(
                page_num=1,
                page_size=page_size,
                org_code=dept_code or None,
                begin_rq=begin or None,
                end_rq=end or None,
                ajlb=category,
            )
            page = MX_PCS_WARNING_SERVICES[rule_type].list_page(db, query)
            for row in page.rows or []:
                if not isinstance(row, dict):
                    continue
                text = cls._normalize_report_warning_text(
                    row.get('warningText') or row.get('warning_text')
                )
                if text:
                    texts.append(text)
        # 去重保序；排名取前 N
        seen: set[str] = set()
        unique: list[str] = []
        for text in texts:
            if text in seen:
                continue
            seen.add(text)
            unique.append(text)
            if limit and len(unique) >= limit:
                break
        return '；'.join(unique)

    @classmethod
    def _format_region_list(
        cls,
        station_rows: list[dict[str, Any]],
        top_n: int | None = None,
        *,
        include_share: bool = False,
        include_yoy: bool = False,
        include_mom: bool = False,
        include_yoy_count: bool = False,
        include_mom_count: bool = False,
        count_threshold: tuple[str, float] | None = None,
        sort_by: RankSortBy = 'count',
        sort_order: RankSortOrder = 'desc',
        include_squad_brigade: bool = False,
    ) -> str:
        """辖区文字：城西：30起，大陈：20起；可附占比/同比/环比/同比数/环比数。"""
        stations = cls._list_region_stations(
            station_rows,
            unit_kind='station',
            include_squad_brigade=include_squad_brigade,
        )
        mapped = [
            {
                'unit_name': name,
                'today_cnt': today,
                'mom_cnt': mom,
                'yoy_cnt': yoy_base,
            }
            for _code, name, today, mom, yoy_base in stations
        ]
        return cls._format_hot_community_list(
            mapped,
            top_n=top_n,
            include_share=include_share,
            include_yoy=include_yoy,
            include_mom=include_mom,
            include_yoy_count=include_yoy_count,
            include_mom_count=include_mom_count,
            count_threshold=count_threshold,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    @classmethod
    def _format_region_pct(cls, cur: float | int | None, base: float | int | None) -> str:
        value = cls._calc_region_pct(cur, base)
        if value is None:
            return ''
        if value == int(value):
            return str(int(value))
        return f'{value:.2f}'.rstrip('0').rstrip('.')

    @classmethod
    def _list_region_stations(
        cls,
        station_rows: list[dict[str, Any]],
        *,
        unit_kind: Literal[
            'station', 'community', 'category', 'type', 'subtype'
        ] = 'station',
        include_squad_brigade: bool = False,
    ) -> list[tuple[str, str, int, int, int]]:
        """解析地区/社区/维度 SQL 行 → (unit_code, name, today, mom, yoy_base)。

        station：跳过全市，排除中队/大队/分局/市局/指挥中心，仅保留本期有量。
        include_squad_brigade=True（交通类别）时保留中队/大队，仍排除分局/市局/指挥中心。
        community / category / type / subtype：按名称保留本期有量。
        """
        stations: list[tuple[str, str, int, int, int]] = []
        exclude_tokens = (
            ('分局', '市局', '指挥中心')
            if include_squad_brigade
            else ('中队', '大队', '分局', '市局', '指挥中心')
        )
        for row in station_rows or []:
            unit_code = str(row.get('unit_code') or row.get('fasqdm') or '').strip()
            raw_name = str(row.get('unit_name') or row.get('fasqmc') or '').strip()
            name = (
                raw_name
                if unit_kind != 'station'
                else normalize_unit_name_display(raw_name)
            )
            try:
                today = int(float(row.get('today_cnt') or row.get('total') or 0))
                mom = int(float(row.get('mom_cnt') or row.get('yesterday_cnt') or 0))
                yoy_base = int(float(row.get('yoy_cnt') or row.get('last_year_today_cnt') or 0))
            except (TypeError, ValueError):
                continue
            if unit_code == '00' or name in {'全市', '合计', '总计'} or not name:
                continue
            if today <= 0:
                continue
            if unit_kind == 'station' and any(token in name for token in exclude_tokens):
                continue
            stations.append((unit_code, name, today, mom, yoy_base))
        return stations

    @classmethod
    def _dim_share_rows_as_trend_units(
        cls,
        rows: list[dict[str, Any]],
        *,
        code_keys: tuple[str, ...],
        name_keys: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        """类别/类型/细类拆分行 → 趋势格式化所需 unit 行。"""
        out: list[dict[str, Any]] = []
        for row in rows or []:
            code = ''
            for key in code_keys:
                code = str(row.get(key) or '').strip()
                if code:
                    break
            name = ''
            for key in name_keys:
                name = str(row.get(key) or '').strip()
                if name:
                    break
            if not name:
                continue
            try:
                today = int(float(row.get('cur_total') or 0))
                mom = int(float(row.get('mom_total') or 0))
                yoy_base = int(float(row.get('yoy_total') or 0))
            except (TypeError, ValueError):
                continue
            out.append(
                {
                    'unit_code': code or name,
                    'unit_name': name,
                    'today_cnt': today,
                    'mom_cnt': mom,
                    'yoy_cnt': yoy_base,
                }
            )
        return out

    @classmethod
    def _stations_to_region_table(
        cls,
        station_rows: list[dict[str, Any]],
        *,
        title: str,
        include_squad_brigade: bool = False,
    ) -> tuple[list[str], list[list[str]], str]:
        """派出所聚合行 → 宽表：单位 | 全市 | 各所；行=当日/同比/环比。

        全市优先取 SQL 返回的 unit_code='00'（DISTINCT 口径），避免各所相加偏差。
        """
        stations = cls._list_region_stations(
            station_rows, include_squad_brigade=include_squad_brigade
        )
        city_today = city_mom = city_yoy = 0
        has_city_row = False
        for row in station_rows or []:
            unit_code = str(row.get('unit_code') or '').strip()
            name = normalize_unit_name_display(str(row.get('unit_name') or '').strip())
            try:
                today = int(float(row.get('today_cnt') or 0))
                mom = int(float(row.get('mom_cnt') or row.get('yesterday_cnt') or 0))
                yoy = int(float(row.get('yoy_cnt') or row.get('last_year_today_cnt') or 0))
            except (TypeError, ValueError):
                continue
            if unit_code == '00' or name == '全市':
                city_today, city_mom, city_yoy = today, mom, yoy
                has_city_row = True
                break

        if not has_city_row:
            city_today = sum(item[2] for item in stations)
            city_mom = sum(item[3] for item in stations)
            city_yoy = sum(item[4] for item in stations)

        headers = ['单位', '全市', *[item[1] for item in stations]]
        table_rows = [
            ['当日数据', str(city_today), *[str(item[2]) for item in stations]],
            [
                '同比(%)',
                cls._format_region_pct(city_today, city_yoy),
                *[cls._format_region_pct(item[2], item[4]) for item in stations],
            ],
            [
                '环比(%)',
                cls._format_region_pct(city_today, city_mom),
                *[cls._format_region_pct(item[2], item[3]) for item in stations],
            ],
        ]
        html_fragment = build_stats_table_html(
            headers,
            table_rows,
            title=title,
            pivot_first_column=True,
        )
        return headers, table_rows, html_fragment

    @classmethod
    def _fetch_region_station_rows(
        cls,
        db: Session,
        *,
        schema: ComponentSchemaContext,
        data_source: str,
        ds_row: Any,
        merged: dict[str, Any],
        dim_filters: dict[str, str],
        date_start: str,
        date_end: str,
        time_col: str,
        dept_expr: str,
        dept_prefix_len: int,
        columns: set[str],
        filter_duplicate: bool = False,
        exclude_non_police: bool = False,
        exclude_traffic: bool = False,
        filter_self_received: bool = False,
        exclude_self_received: bool = False,
        extra_where: str = '',
        extra_bind: dict[str, Any] | None = None,
        include_squad_brigade: bool = False,
    ) -> tuple[list[dict[str, Any]], str]:
        """执行地区 SQL，供地区表与下级所同比趋势共用。"""
        # 部门列 / LEFT 位数与总量同一套 resolve_metric_scope，禁止写死 LEFT 6
        region_sql = AtomicMetricSql.build_region_station_sql(
            table_name=schema.table_name,
            time_col=time_col,
            data_source=data_source,
            dim_filters=dim_filters,
            columns=columns,
            dept_col=dept_expr,
            dept_prefix_len=dept_prefix_len,
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            extra_where=extra_where,
            include_squad_brigade=include_squad_brigade,
        )
        bind = ComponentSqlExecutor.build_bind_params(
            {
                'date_start': date_start,
                'date_end': date_end,
                'dept_code': _pick(merged, 'dept_code', 'deptCode'),
                **{k: (_pick(merged, k) or '') for k in dim_filters},
                **(extra_bind or {}),
            },
            region_sql,
        )
        station_rows = ComponentSqlExecutor.fetch_rows(
            db, region_sql, bind, data_source_row=ds_row, limit=500
        )
        return station_rows, ComponentSqlExecutor.format_executable_sql(region_sql, bind)

    @classmethod
    def _build_region_table_from_rows(
        cls,
        station_rows: list[dict[str, Any]],
        merged: dict[str, Any],
    ) -> tuple[str, list[str], list[list[str]], str]:
        topic = (
            _pick(merged, 'category_name', 'categoryName', 'ajlb_name')
            or _pick(merged, 'type_name', 'typeName')
            or _pick(merged, 'subtype_name', 'subtypeName')
            or ''
        )
        table_title = f'{topic}各地接警量统计表' if topic else '各地接警量统计表'
        headers, rows, html_fragment = cls._stations_to_region_table(
            station_rows,
            title=table_title,
            include_squad_brigade=cls._is_traffic_category(merged),
        )
        return table_title, headers, rows, html_fragment

    # 接警/反馈字典一致：10=刑事案件，20=行政(治安)案件
    _CASE_CATEGORY_CODES = frozenset({'10', '20'})
    # 反馈/接警「交通」类别：辖区统计需保留中队、大队
    _TRAFFIC_CATEGORY_CODES = frozenset({'20000'})
    _TRAFFIC_CATEGORY_NAMES = frozenset({'交通', '交通警情'})

    @classmethod
    def _is_traffic_category(cls, merged: dict[str, Any]) -> bool:
        """是否交通类别（用于辖区保留中队/大队）。"""
        raw_code = _pick(
            merged,
            'category_code',
            'categoryCode',
            'ajlb',
            'bjlb',
            'bjlbdm',
            'feedback_category_code',
        )
        raw_name = _pick(
            merged,
            'category_name',
            'categoryName',
            'ajlb_name',
            'bjlb_name',
            'bjlbmc',
        )
        codes = [part.strip() for part in str(raw_code or '').split(',') if part.strip()]
        names = [part.strip() for part in str(raw_name or '').split(',') if part.strip()]
        if any(code in cls._TRAFFIC_CATEGORY_CODES for code in codes):
            return True
        if any(name in cls._TRAFFIC_CATEGORY_NAMES for name in names):
            return True
        return False

    @classmethod
    def _should_force_feedback_by_case_category(
        cls, merged: dict[str, Any], data_source: str
    ) -> bool:
        """刑事/行政治安/交通选中时，若当前是接警单则本次查询改走反馈单。

        交通辖区单位在填写反馈单位(txfkdwdm)上的交警中队/大队，接警单 gxdwdm 多为派出所，
        仅放开名称过滤仍看不到中队。
        """
        if 'jjd' not in (data_source or '').lower():
            return False
        category = _pick(merged, 'category_code', 'categoryCode', 'ajlb', 'bjlb')
        codes = {part.strip() for part in category.split(',') if part.strip()}
        if codes & cls._CASE_CATEGORY_CODES or codes & cls._TRAFFIC_CATEGORY_CODES:
            return True
        name = _pick(
            merged,
            'category_name',
            'categoryName',
            'ajlb_name',
            'bjlb_name',
            'bjlbmc',
        )
        if not name:
            return False
        name_parts = [part.strip() for part in name.split(',') if part.strip()]
        if any(part in cls._TRAFFIC_CATEGORY_NAMES for part in name_parts):
            return True
        return any(
            '刑事' in part or '治安' in part or '行政治安' in part for part in name_parts
        )

    @classmethod
    def _codes_exist_in_table(
        cls,
        db: Session,
        *,
        sql: str,
        codes: str,
    ) -> bool:
        parts = [part.strip() for part in str(codes or '').split(',') if part.strip()]
        if not parts:
            return False
        try:
            result = db.execute(text(sql), {'codes': ','.join(parts)})
            hit = int(result.scalar() or 0)
        except Exception:
            return False
        return hit >= len(parts)

    @classmethod
    def _should_query_jjd_for_incident_type_codes(
        cls, db: Session, data_source: str, type_code: str | None
    ) -> bool:
        """反馈单上用接警类型码（如 10010 偷盗类）会查不到，类型拆分改走接警单。"""
        if 'fkd' not in (data_source or '').lower():
            return False
        if not type_code:
            return False
        return cls._codes_exist_in_table(
            db,
            sql=(
                "SELECT COUNT(DISTINCT CAST(CAST(bjlxdm AS SIGNED) AS CHAR)) "
                "FROM zd_bjlxdm "
                "WHERE FIND_IN_SET(CAST(CAST(bjlxdm AS SIGNED) AS CHAR), :codes) > 0"
            ),
            codes=str(type_code),
        )

    @classmethod
    def _should_query_jjd_for_incident_subtype_codes(
        cls, db: Session, data_source: str, subtype_code: str | None
    ) -> bool:
        """反馈单上用接警细类码会查不到，细类拆分改走接警单。"""
        if 'fkd' not in (data_source or '').lower():
            return False
        if not subtype_code:
            return False
        return cls._codes_exist_in_table(
            db,
            sql=(
                "SELECT COUNT(DISTINCT CAST(CAST(bjxldm AS SIGNED) AS CHAR)) "
                "FROM zd_bjxldm "
                "WHERE FIND_IN_SET(CAST(CAST(bjxldm AS SIGNED) AS CHAR), :codes) > 0"
            ),
            codes=str(subtype_code),
        )

    @classmethod
    def _resolve_tag_package_id(
        cls, merged: dict[str, Any], body: AtomicMetricQueryRequest
    ) -> int | None:
        raw = (
            merged.get('tag_package_id')
            or merged.get('tagPackageId')
            or merged.get('package_id')
            or merged.get('packageId')
            or body.tag_package_id
        )
        if raw is None or raw == '':
            return None
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    @classmethod
    def _parse_metric_datetime(cls, value: str) -> datetime | None:
        text = str(value or '').strip()
        if not text:
            return None
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text.replace('Z', '+00:00').split('+')[0])
        except ValueError:
            return None

    @classmethod
    def _resolve_package_case_time_range(
        cls,
        date_start: str,
        date_end: str,
        *,
        need_yoy: bool,
        need_mom: bool,
        need_cumulative: bool = False,
    ) -> tuple[str, str]:
        """研判包取 cjdbh 的时间窗。

        同比/环比 SQL 会统计历史窗内同单号集合；若取号只截当期，历史窗无单号 → 基期 0 → 0%。
        累计需覆盖结束时间所在年 1 月 1 日起的单号。
        """
        if not need_yoy and not need_mom and not need_cumulative:
            return date_start, date_end
        start = cls._parse_metric_datetime(date_start)
        end = cls._parse_metric_datetime(date_end)
        if start is None or end is None:
            return date_start, date_end
        end_text = str(date_end).strip()
        end_excl = end + timedelta(days=1) if len(end_text) <= 10 else end + timedelta(seconds=1)
        begin = start
        if need_mom:
            mom_start = start - (end_excl - start)
            if mom_start < begin:
                begin = mom_start
        if need_yoy:
            try:
                yoy_start = start.replace(year=start.year - 1)
            except ValueError:
                yoy_start = start.replace(year=start.year - 1, day=28)
            if yoy_start < begin:
                begin = yoy_start
        if need_cumulative:
            year_start = cls._parse_metric_datetime(cls._year_start_datetime(date_end))
            if year_start is not None and year_start < begin:
                begin = year_start
        return begin.strftime('%Y-%m-%d %H:%M:%S'), date_end

    @classmethod
    def _year_start_datetime(cls, date_end: str) -> str:
        """结束时间所在年的 1 月 1 日 00:00:00（用于累计统计）。"""
        parsed = cls._parse_metric_datetime(date_end)
        if parsed is None:
            text = str(date_end or '').strip().replace('T', ' ')
            year = text[:4]
            if year.isdigit() and len(year) == 4:
                return f'{year}-01-01 00:00:00'
            return f'{datetime.now().year}-01-01 00:00:00'
        return f'{parsed.year}-01-01 00:00:00'

    @classmethod
    def _shift_metric_datetime(cls, value: str, *, years: int) -> str:
        """按整年平移日期，保留原字符串精度（日期 / 日期时间）。"""
        parsed = cls._parse_metric_datetime(value)
        if parsed is None:
            return value
        try:
            shifted = parsed.replace(year=parsed.year + years)
        except ValueError:
            shifted = parsed.replace(year=parsed.year + years, day=28)
        text = str(value or '').strip()
        if len(text) <= 10:
            return shifted.strftime('%Y-%m-%d')
        return shifted.strftime('%Y-%m-%d %H:%M:%S')

    @classmethod
    def _shift_metric_period_back(cls, date_start: str, date_end: str) -> tuple[str, str]:
        """将区间整体前移同等长度（环比基期）。"""
        start = cls._parse_metric_datetime(date_start)
        end = cls._parse_metric_datetime(date_end)
        if start is None or end is None:
            return date_start, date_end
        end_text = str(date_end).strip()
        end_excl = end + timedelta(days=1) if len(end_text) <= 10 else end + timedelta(seconds=1)
        span = end_excl - start
        mom_start = start - span
        mom_end = end - span
        if len(str(date_start).strip()) <= 10:
            return mom_start.strftime('%Y-%m-%d'), mom_end.strftime('%Y-%m-%d')
        return mom_start.strftime('%Y-%m-%d %H:%M:%S'), mom_end.strftime('%Y-%m-%d %H:%M:%S')

    @classmethod
    def _resolve_community_source_context(
        cls,
        db: Session,
        *,
        data_source: str,
        schema,
        columns: set[str],
        merged: dict[str, Any],
        has_dimension: bool,
        tag_package_id: int | None,
        package_case_ids: list[str] | None,
    ) -> dict[str, Any]:
        """社区取 fkd.sdsq；接警口径下用 jjdbh 关联 jjd 过滤维度/时间/部门。"""
        community_source = data_source
        community_schema = schema
        community_columns = columns
        community_merged = dict(merged)
        jjd_bridge = False
        if 'jjd' in (data_source or '').lower():
            jjd_bridge = True
            community_source = 'fkd_fkd'
            community_schema = ComponentSchemaContext.resolve(community_source)
            community_columns = {
                str(item.get('column_name') or '').lower() for item in community_schema.columns
            }
            community_merged['data_source'] = community_source
            community_merged['dataSource'] = community_source
            community_merged['document_type'] = 'feedback'
            community_merged['documentType'] = 'feedback'
            # 维度改走 jjd EXISTS，避免把接警码误套到反馈 aj* 列
            for key in (
                'category_code',
                'categoryCode',
                'type_code',
                'typeCode',
                'subtype_code',
                'subtypeCode',
                'ajlb',
                'ajlx',
                'ajxl',
                'bjlb',
                'bjlx',
                'bjxl',
                'ajlbbh',
                'ajlxbh',
                'ajxlbh',
                'bjlbdm',
                'bjlxdm',
                'bjxldm',
                'feedback_subtype_code',
            ):
                community_merged[key] = ''

        dim_filters = AtomicMetricSql.resolve_dimension_filters(
            community_columns, community_source, community_merged
        )
        time_col, dept_expr, _dept_prefix = AtomicMetricSql.resolve_metric_scope(
            community_columns,
            community_source,
            has_dimension=has_dimension,
            for_tag_package=bool(tag_package_id),
        )
        count_id = AtomicMetricSql.resolve_case_id_expr(community_columns, community_source)
        ds_row = DataSourceDao.get_by_code(db, community_source)

        extra_where = ''
        package_bind: dict[str, Any] = {}
        if package_case_ids:
            extra_where, package_bind = AtomicMetricSql.build_case_id_filter(
                community_columns, package_case_ids, qualify_alias='a'
            )

        if jjd_bridge:
            # 接警维度绑定：供 EXISTS 内 FIND_IN_SET 使用
            dim_bind = {
                'bjlb': _pick(merged, 'bjlb', 'category_code', 'categoryCode') or '',
                'bjlx': _pick(merged, 'bjlx', 'type_code', 'typeCode') or '',
                'bjxl': _pick(merged, 'bjxl', 'subtype_code', 'subtypeCode') or '',
            }
        else:
            dim_bind = {k: (_pick(community_merged, k) or '') for k in dim_filters}

        return {
            'data_source': community_source,
            'schema': community_schema,
            'columns': community_columns,
            'dim_filters': dim_filters,
            'dim_bind': dim_bind,
            'jjd_bridge': jjd_bridge,
            'time_col': time_col,
            'dept_expr': dept_expr,
            'count_id': count_id,
            'ds_row': ds_row,
            'extra_where': extra_where,
            'package_bind': package_bind,
        }

    @classmethod
    def _fetch_community_yoy_rows(
        cls,
        db: Session,
        *,
        schema,
        data_source: str,
        ds_row,
        dim_filters: dict[str, str],
        date_start: str,
        date_end: str,
        time_col: str,
        dept_expr: str,
        count_id: str,
        columns: set[str],
        filter_duplicate: bool,
        exclude_non_police: bool,
        exclude_traffic: bool,
        filter_self_received: bool,
        exclude_self_received: bool,
        extra_where: str,
        package_bind: dict[str, Any],
        executed_parts: list[str],
        dept_code: str | None,
        dim_bind: dict[str, Any] | None = None,
        jjd_bridge: bool = False,
        cur_rows: list[dict[str, Any]] | None = None,
        need_mom: bool = False,
    ) -> list[dict[str, Any]]:
        """社区趋势：复用高发社区 SQL 查当期/去年同期（及可选环比期），再合并为地区行结构。"""
        community_sql = AtomicMetricSql.build_hot_community_sql(
            table_name=schema.table_name,
            time_col=time_col,
            dept_expr=dept_expr,
            dim_filters=dim_filters,
            count_id=count_id,
            columns=columns,
            data_source=data_source,
            top_n=None,
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            extra_where=extra_where,
            jjd_bridge=jjd_bridge,
        )
        if not community_sql:
            return []

        # jjd_bridge 时 dim_bind 为 bjlb/bjlx/bjxl，不能只按 fkd 的 dim_filters 取键
        if dim_bind:
            dim_values = {k: str(v or '') for k, v in dim_bind.items()}
        else:
            dim_values = {k: '' for k in dim_filters}

        def _fetch(period_start: str, period_end: str) -> list[dict[str, Any]]:
            bind = ComponentSqlExecutor.build_bind_params(
                {
                    'date_start': period_start,
                    'date_end': period_end,
                    'dept_code': dept_code or '',
                    **dim_values,
                    **package_bind,
                },
                community_sql,
            )
            rows = ComponentSqlExecutor.fetch_rows(
                db, community_sql, bind, data_source_row=ds_row, limit=2000
            )
            executed_parts.append(ComponentSqlExecutor.format_executable_sql(community_sql, bind))
            return rows or []

        def _to_count_map(rows: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, str]]:
            count_map: dict[str, int] = {}
            name_map: dict[str, str] = {}
            for row in rows:
                code = str(row.get('fasqdm') or row.get('unit_code') or '').strip()
                name = str(row.get('fasqmc') or row.get('unit_name') or '').strip()
                if not code and not name:
                    continue
                key = code or name
                try:
                    raw_total = (
                        row.get('total')
                        if row.get('total') is not None
                        else row.get('today_cnt')
                    )
                    count_map[key] = int(float(raw_total or 0))
                except (TypeError, ValueError):
                    count_map[key] = 0
                if name:
                    name_map[key] = name
            return count_map, name_map

        # 当期可复用已查的高发社区结果，避免重复扫表
        resolved_cur = list(cur_rows) if cur_rows is not None else _fetch(date_start, date_end)
        yoy_rows = _fetch(
            cls._shift_metric_datetime(date_start, years=-1),
            cls._shift_metric_datetime(date_end, years=-1),
        )
        yoy_map, name_map = _to_count_map(yoy_rows)
        mom_map: dict[str, int] = {}
        if need_mom:
            mom_start, mom_end = cls._shift_metric_period_back(date_start, date_end)
            mom_rows = _fetch(mom_start, mom_end)
            mom_map, mom_names = _to_count_map(mom_rows)
            for key, name in mom_names.items():
                name_map.setdefault(key, name)

        merged_rows: list[dict[str, Any]] = []
        for row in resolved_cur:
            code = str(row.get('fasqdm') or '').strip()
            name = str(row.get('fasqmc') or '').strip()
            if not code and not name:
                continue
            key = code or name
            try:
                today = int(float(row.get('total') or 0))
            except (TypeError, ValueError):
                today = 0
            if today <= 0:
                continue
            merged_rows.append(
                {
                    'unit_code': code or key,
                    'unit_name': name or name_map.get(key) or key,
                    'today_cnt': today,
                    'mom_cnt': mom_map.get(key, 0),
                    'yoy_cnt': yoy_map.get(key, 0),
                }
            )
        return merged_rows

    @classmethod
    def _resolve_trend_compare(
        cls,
        merged: dict[str, Any],
        body: AtomicMetricQueryRequest,
        *,
        include_yoy: bool,
        include_mom: bool,
        include_share: bool,
    ) -> TrendCompare:
        """趋势口径：显式 trend_compare > 同比 > 环比 > 占比 > 默认同比。"""
        explicit = _normalize_trend_compare(
            merged.get('trend_compare')
            or merged.get('trendCompare')
            or getattr(body, 'trend_compare', None)
        )
        if explicit:
            return explicit
        if include_yoy:
            return 'yoy'
        if include_mom:
            return 'mom'
        if include_share:
            return 'share'
        return 'yoy'

    @classmethod
    def _calc_station_trend_pct(
        cls,
        today: int,
        mom: int,
        yoy_base: int,
        compare: TrendCompare,
        *,
        total_cur: int = 0,
        total_mom: int = 0,
        total_yoy: int = 0,
    ) -> float | None:
        if compare == 'mom':
            return cls._calc_region_pct(today, mom)
        if compare == 'share':
            if total_cur <= 0:
                return None
            share_cur = today / total_cur * 100
            if total_yoy > 0:
                return share_cur - (yoy_base / total_yoy * 100)
            if total_mom > 0:
                return share_cur - (mom / total_mom * 100)
            return None
        return cls._calc_region_pct(today, yoy_base)

    @classmethod
    def _resolve_count_threshold(
        cls, merged: dict[str, Any], body: AtomicMetricQueryRequest
    ) -> tuple[str, float] | None:
        """解析数量阈值：返回 (gt|lt, value)；无效则 None。"""
        op = (
            merged.get('count_threshold_op')
            or merged.get('countThresholdOp')
            or body.count_threshold_op
            or ''
        )
        op = str(op).strip().lower()
        if op in {'>', 'gt', 'greater', '大于'}:
            op = 'gt'
        elif op in {'<', 'lt', 'less', '小于'}:
            op = 'lt'
        else:
            return None
        raw = merged.get('count_threshold_value')
        if raw is None or raw == '':
            raw = merged.get('countThresholdValue')
        if raw is None or raw == '':
            raw = body.count_threshold_value
        if raw is None or raw == '':
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        if value < 0:
            return None
        return op, value

    @classmethod
    def _pass_count_threshold(
        cls, count: int | float, threshold: tuple[str, float] | None
    ) -> bool:
        if not threshold:
            return True
        op, value = threshold
        try:
            num = float(count)
        except (TypeError, ValueError):
            return False
        if op == 'gt':
            return num > value
        if op == 'lt':
            return num < value
        return True

    @classmethod
    def _resolve_rank_sort_by(
        cls, merged: dict[str, Any], body: AtomicMetricQueryRequest
    ) -> RankSortBy:
        raw = merged.get('rank_sort_by')
        if raw is None or raw == '':
            raw = merged.get('rankSortBy')
        if raw is None or raw == '':
            raw = body.rank_sort_by
        return _normalize_rank_sort_by(raw)

    @classmethod
    def _resolve_rank_sort_order(
        cls, merged: dict[str, Any], body: AtomicMetricQueryRequest
    ) -> RankSortOrder:
        raw = merged.get('rank_sort_order')
        if raw is None or raw == '':
            raw = merged.get('rankSortOrder')
        if raw is None or raw == '':
            raw = body.rank_sort_order
        return _normalize_rank_sort_order(raw)

    @classmethod
    def _sort_dim_rank_items(
        cls,
        items: list[tuple[str, int, float, float | None, float | None, int, int]],
        sort_by: RankSortBy,
        sort_order: RankSortOrder = 'desc',
    ) -> None:
        """按数量/同比/环比/占比排序；sort_order=asc|desc，默认降序。次键数量、名称。"""
        ascending = sort_order == 'asc'

        def sort_key(
            item: tuple[str, int, float, float | None, float | None, int, int],
        ) -> tuple[float, int, str]:
            name, cur_total, share, yoy, mom, _yoy_cnt, _mom_cnt = item
            if sort_by == 'yoy':
                if yoy is None:
                    metric = float('inf') if ascending else float('-inf')
                else:
                    metric = float(yoy)
            elif sort_by == 'mom':
                if mom is None:
                    metric = float('inf') if ascending else float('-inf')
                else:
                    metric = float(mom)
            elif sort_by == 'share':
                metric = float(share or 0)
            else:
                metric = float(cur_total)
            primary = metric if ascending else -metric
            secondary = cur_total if ascending else -cur_total
            return (primary, secondary, name)

        items.sort(key=sort_key)

    @classmethod
    def _resolve_yoy_trend_top_n(cls, merged: dict[str, Any], body: AtomicMetricQueryRequest) -> int | None:
        raw = merged.get('yoy_trend_top_n')
        if raw is None or raw == '':
            raw = merged.get('yoyTrendTopN')
        if raw is None or raw == '':
            raw = body.yoy_trend_top_n
        if raw is None or raw == '':
            return None
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None
        if value <= 0:
            return None
        return min(value, 200)

    @classmethod
    def _format_yoy_station_list(
        cls,
        rows: list[dict[str, Any]],
        trend: YoyTrend,
        top_n: int | None = None,
        *,
        unit_kind: Literal[
            'station', 'community', 'category', 'type', 'subtype'
        ] = 'station',
        compare: TrendCompare = 'yoy',
        include_squad_brigade: bool = False,
    ) -> str:
        """按派出所/社区/类别等变化(%)筛上升/下降/持平。"""
        if trend in ('analysis', 'up', 'down'):
            prefer: Literal['up', 'down'] | None = (
                'up' if trend == 'up' else ('down' if trend == 'down' else None)
            )
            text, _stations, _direction = cls._format_yoy_analysis(
                rows,
                top_n=top_n or 3,
                unit_kind=unit_kind,
                compare=compare,
                prefer=prefer,
                include_squad_brigade=include_squad_brigade,
            )
            return text
        stations = cls._list_region_stations(
            rows, unit_kind=unit_kind, include_squad_brigade=include_squad_brigade
        )
        total_cur = sum(item[2] for item in stations)
        total_mom = sum(item[3] for item in stations)
        total_yoy = sum(item[4] for item in stations)
        items: list[tuple[str, float, int]] = []
        for _unit_code, name, today, mom, yoy_base in stations:
            pct = cls._calc_station_trend_pct(
                today,
                mom,
                yoy_base,
                compare,
                total_cur=total_cur,
                total_mom=total_mom,
                total_yoy=total_yoy,
            )
            if not _match_yoy_trend(pct, trend):
                continue
            assert pct is not None
            items.append((name, pct, today))
        if trend == 'flat':
            # 持平：展示为 0，按本期量取前 N
            items.sort(key=lambda item: (-item[2], item[0]))
        else:
            # 上升/下降：按 |变化%| 从大到小
            items.sort(key=lambda item: (-abs(item[1]), -item[2], item[0]))
        if top_n and top_n > 0:
            items = items[:top_n]
        return '、'.join(
            f'{name}{today}起（{_format_station_yoy_pct(yoy)}）' for name, yoy, today in items
        )

    @classmethod
    def _collect_yoy_station_groups(
        cls,
        rows: list[dict[str, Any]],
        *,
        unit_kind: Literal[
            'station', 'community', 'category', 'type', 'subtype'
        ] = 'station',
        compare: TrendCompare = 'yoy',
        sort_by: RankSortBy | None = None,
        sort_order: RankSortOrder = 'desc',
        include_squad_brigade: bool = False,
    ) -> tuple[
        list[tuple[str, str, float, int]],
        list[tuple[str, str, float, int]],
        list[tuple[str, str, float, int]],
    ]:
        """按派出所/社区/维度口径分组：上升 / 持平 / 下降。

        各组元素：(unit_code, name, pct%, today)。
        sort_by 为 None 时按变化幅度（升幅大/降幅大优先）；否则按排名排序字段。
        """
        stations = cls._list_region_stations(
            rows, unit_kind=unit_kind, include_squad_brigade=include_squad_brigade
        )
        total_cur = sum(item[2] for item in stations)
        total_mom = sum(item[3] for item in stations)
        total_yoy = sum(item[4] for item in stations)
        up: list[tuple[str, str, float, int]] = []
        flat: list[tuple[str, str, float, int]] = []
        down: list[tuple[str, str, float, int]] = []
        for unit_code, name, today, mom, yoy_base in stations:
            pct = cls._calc_station_trend_pct(
                today,
                mom,
                yoy_base,
                compare,
                total_cur=total_cur,
                total_mom=total_mom,
                total_yoy=total_yoy,
            )
            if pct is None:
                continue
            if pct > 0:
                up.append((unit_code, name, pct, today))
            elif pct < 0:
                down.append((unit_code, name, pct, today))
            else:
                flat.append((unit_code, name, pct, today))
        cls._sort_yoy_analysis_group(
            up, sort_by=sort_by, sort_order=sort_order, direction='up', total_cur=total_cur
        )
        cls._sort_yoy_analysis_group(
            flat, sort_by=sort_by, sort_order=sort_order, direction='flat', total_cur=total_cur
        )
        cls._sort_yoy_analysis_group(
            down, sort_by=sort_by, sort_order=sort_order, direction='down', total_cur=total_cur
        )
        return up, flat, down

    @classmethod
    def _sort_yoy_analysis_group(
        cls,
        items: list[tuple[str, str, float, int]],
        *,
        sort_by: RankSortBy | None,
        sort_order: RankSortOrder,
        direction: Literal['up', 'down', 'flat'],
        total_cur: int,
    ) -> None:
        """分析分组排序：无排名时按幅度；有排名时按数量/同比/环比/占比 + 升降序。"""
        if not items:
            return
        if sort_by is None:
            if direction == 'up':
                items.sort(key=lambda item: (-item[2], item[1]))
            elif direction == 'down':
                items.sort(key=lambda item: (item[2], item[1]))
            else:
                items.sort(key=lambda item: item[1])
            return

        ascending = sort_order == 'asc'

        def sort_key(item: tuple[str, str, float, int]) -> tuple[float, int, str]:
            _code, name, pct, today = item
            if sort_by in {'yoy', 'mom'}:
                # 分析口径下 pct 即为当前同比/环比/占比变化
                metric = float(pct)
            elif sort_by == 'share':
                metric = (float(today) / float(total_cur) * 100.0) if total_cur else 0.0
            else:
                metric = float(today)
            primary = metric if ascending else -metric
            secondary = today if ascending else -today
            return (primary, secondary, name)

        items.sort(key=sort_key)

    @classmethod
    def _format_yoy_name_list(
        cls,
        items: list[tuple[Any, ...]],
        *,
        with_pct: bool,
    ) -> str:
        """趋势单位列表：名称N起 / 名称N起（pct%）。"""
        parts: list[str] = []
        for item in items:
            today: int | None = None
            if len(item) >= 4:
                _code, name, yoy, today_raw = item[0], item[1], item[2], item[3]
                try:
                    today = int(today_raw)
                except (TypeError, ValueError):
                    today = None
            elif len(item) == 3:
                _code, name, yoy = item[0], item[1], item[2]
            else:
                name, yoy = item[0], item[1]
            name_text = str(name)
            base = f'{name_text}{today}起' if today is not None else name_text
            if with_pct:
                parts.append(f'{base}（{_format_station_yoy_pct(yoy)}）')
            else:
                parts.append(base)
        return '、'.join(parts)

    @classmethod
    def _format_yoy_analysis(
        cls,
        rows: list[dict[str, Any]],
        top_n: int = 3,
        *,
        unit_kind: Literal[
            'station', 'community', 'category', 'type', 'subtype'
        ] = 'station',
        compare: TrendCompare = 'yoy',
        prefer: Literal['up', 'down'] | None = None,
        sort_by: RankSortBy | None = None,
        sort_order: RankSortOrder = 'desc',
        include_squad_brigade: bool = False,
    ) -> tuple[str, list[tuple[str, str, float]], Literal['up', 'down'] | None]:
        """组织升/降幅分析文案，并返回前 N 单位供下钻。

        prefer:
          - up：强制升幅文案（除下降/持平外，升幅前 N）
          - down：强制降幅文案（除上升/持平外，降幅前 N）
          - None：按升/降数量自动选择（兼容旧 analysis）
        sort_by:
          - None：按变化幅度取前 N（默认）
          - count/yoy/mom/share：吃排名排序字段 + sort_order
        返回：(文案, top_units[(unit_code,name,pct)], direction)
        """
        unit_label = {
            'station': '派出所',
            'community': '社区',
            'category': '类别',
            'type': '类型',
            'subtype': '细类',
        }.get(unit_kind, '派出所')
        compare_label = _trend_compare_label(compare)
        up, flat, down = cls._collect_yoy_station_groups(
            rows,
            unit_kind=unit_kind,
            compare=compare,
            sort_by=sort_by,
            sort_order=sort_order,
            include_squad_brigade=include_squad_brigade,
        )
        if not up and not flat and not down:
            return '', [], None

        n = max(1, min(int(top_n or 3), 200))

        def _top_for_drill(
            items: list[tuple[str, str, float, int]],
        ) -> list[tuple[str, str, float]]:
            return [(code, name, pct) for code, name, pct, _today in items]

        def _rise_text() -> tuple[str, list[tuple[str, str, float]], Literal['up'] | None]:
            if not up:
                return '', [], None
            except_parts: list[str] = []
            if down:
                except_parts.append(
                    f'{cls._format_yoy_name_list(down, with_pct=True)}下降'
                )
            if flat:
                except_parts.append(
                    f'{cls._format_yoy_name_list(flat, with_pct=False)}持平'
                )
            top_items = up[:n]
            top_label = _cn_top_n_label(len(top_items))
            top_text = cls._format_yoy_name_list(top_items, with_pct=True)
            if except_parts:
                text = f'除{"，".join(except_parts)}外，升幅前{top_label}的为{top_text}。'
            else:
                text = f'各{unit_label}{compare_label}上升，升幅前{top_label}的为{top_text}。'
            return text, _top_for_drill(top_items), 'up'

        def _fall_text() -> tuple[str, list[tuple[str, str, float]], Literal['down'] | None]:
            if not down:
                return '', [], None
            except_parts: list[str] = []
            if up:
                except_parts.append(
                    f'{cls._format_yoy_name_list(up, with_pct=len(up) <= 3)}上升'
                )
            if flat:
                except_parts.append(
                    f'{cls._format_yoy_name_list(flat, with_pct=False)}持平'
                )
            top_items = down[:n]
            top_label = _cn_top_n_label(len(top_items))
            top_text = cls._format_yoy_name_list(top_items, with_pct=True)
            if except_parts:
                text = f'除{"，".join(except_parts)}外，降幅前{top_label}的为{top_text}。'
            else:
                text = f'各{unit_label}{compare_label}下降，降幅前{top_label}的为{top_text}。'
            return text, _top_for_drill(top_items), 'down'

        if prefer == 'up':
            text, tops, direction = _rise_text()
            if text:
                return text, tops, direction
            # 无上升时退回降幅/持平说明
            text, tops, direction = _fall_text()
            if text:
                return text, tops, direction
            return f'{cls._format_yoy_name_list(flat, with_pct=False)}持平。', [], None

        if prefer == 'down':
            text, tops, direction = _fall_text()
            if text:
                return text, tops, direction
            text, tops, direction = _rise_text()
            if text:
                return text, tops, direction
            return f'{cls._format_yoy_name_list(flat, with_pct=False)}持平。', [], None

        # 自动：上升多于下降则升幅，否则降幅
        if up and len(up) > len(down):
            return _rise_text()
        if down:
            return _fall_text()
        if up:
            return _rise_text()
        return f'{cls._format_yoy_name_list(flat, with_pct=False)}持平。', [], None

    @staticmethod
    def _alarm_display_name(name: str) -> str:
        text = str(name or '').strip()
        if not text:
            return ''
        return text if text.endswith('警情') else f'{text}警情'

    @classmethod
    def _format_station_dim_drill_appendix(
        cls,
        *,
        top_stations: list[tuple[str, str, float]],
        direction: Literal['up', 'down'],
        dim_rows: list[dict[str, Any]],
        top_n: int,
        label_map: dict[str, str],
        unmapped_label: str | None = None,
    ) -> str:
        """拼「其中赤岸升幅前三的警情为…；城西…」。"""
        if not top_stations:
            return ''
        by_unit: dict[str, list[dict[str, Any]]] = {}
        for row in dim_rows or []:
            unit_code = str(row.get('unit_code') or '').strip()
            if not unit_code:
                continue
            by_unit.setdefault(unit_code, []).append(row)

        amp_label = '升幅' if direction == 'up' else '降幅'
        parts: list[str] = []
        for unit_code, station_name, _station_yoy in top_stations:
            rows = by_unit.get(unit_code) or []
            merged: dict[str, tuple[int, float]] = {}
            for row in rows:
                code = str(row.get('dim_code') or '').strip()
                raw_name = str(row.get('dim_name') or '').strip()
                name = ''
                if raw_name and not cls._looks_like_type_code(raw_name):
                    name = raw_name
                else:
                    for key in (code, raw_name, code.lstrip('0') if code else ''):
                        if key and key in label_map:
                            mapped = str(label_map[key] or '').strip()
                            if mapped and not cls._looks_like_type_code(mapped):
                                name = mapped
                                break
                    if not name:
                        if unmapped_label and (code or raw_name):
                            name = unmapped_label
                        else:
                            name = raw_name or code
                name = cls._alarm_display_name(name)
                if not name:
                    continue
                try:
                    cur_total = int(float(row.get('cur_total') or 0))
                except (TypeError, ValueError):
                    cur_total = 0
                if cur_total <= 0:
                    continue
                try:
                    yoy = float(row.get('yoy'))
                except (TypeError, ValueError):
                    continue
                if direction == 'up' and yoy <= 0:
                    continue
                if direction == 'down' and yoy >= 0:
                    continue
                prev = merged.get(name)
                if prev:
                    prev_cur, prev_yoy = prev
                    next_cur = prev_cur + cur_total
                    next_yoy = (
                        (prev_yoy * prev_cur + yoy * cur_total) / next_cur if next_cur else yoy
                    )
                    merged[name] = (next_cur, next_yoy)
                else:
                    merged[name] = (cur_total, yoy)
            items = [(name, cur, yoy) for name, (cur, yoy) in merged.items()]
            items.sort(key=lambda item: (-abs(item[2]), -item[1], item[0]))
            items = items[: max(1, top_n)]
            if not items:
                continue
            detail = '、'.join(
                f'{name}{cur}起（{cls._format_type_yoy_phrase(yoy)}）'
                for name, cur, yoy in items
            )
            top_label = _cn_top_n_label(len(items))
            parts.append(f'{station_name}{amp_label}前{top_label}的警情为{detail}')
        if not parts:
            return ''
        return '其中' + '；'.join(parts) + '。'

    @staticmethod
    def _looks_like_type_code(text: str) -> bool:
        value = str(text or '').strip()
        if not value:
            return True
        # 纯数字即代码：10/20（刑事/行政）或 050002009 等细类
        return bool(re.fullmatch(r'\d+', value))

    @classmethod
    def _build_dim_label_map(
        cls,
        db: Session,
        data_source: str,
        *,
        level: str,
    ) -> dict[str, str]:
        """维度代码 → 名称：优先字典，再补类别树指定层级。"""
        is_incident = 'jjd' in (data_source or '').lower()
        label_map = ComponentRenderService._dict_label_map(db, 'jq_category')
        # 反馈类别码偶发挂在 jq_type；两类字典都并入，避免 10/20 等短码落空
        if level == 'category':
            type_dict = ComponentRenderService._dict_label_map(db, 'jq_type')
            for code, name in type_dict.items():
                label_map.setdefault(code, name)
            # 案件定性常见码兜底（与 ZD_FKLBDM 一致）
            label_map.setdefault('10', '刑事案件')
            label_map.setdefault('20', '行政(治安)案件')
        try:
            tree = (
                IncidentCategoryService.tree(db)
                if is_incident
                else FeedbackCategoryService.tree(db)
            )
        except Exception:
            tree = []

        def walk(nodes: list[Any]) -> None:
            for node in nodes or []:
                code = str(getattr(node, 'code', '') or '').strip()
                name = str(getattr(node, 'name', '') or '').strip()
                node_level = str(getattr(node, 'level', '') or '').strip()
                # 树名称优先覆盖字典，避免短码仍显示数字
                if code and name and node_level == level:
                    if code not in label_map or cls._looks_like_type_code(label_map.get(code, '')):
                        label_map[code] = name
                children = getattr(node, 'children', None) or []
                if children:
                    walk(children)

        walk(tree)
        return label_map

    @classmethod
    def _build_category_label_map(cls, db: Session, data_source: str) -> dict[str, str]:
        """类别代码 → 名称。"""
        return cls._build_dim_label_map(db, data_source, level='category')

    @classmethod
    def _build_type_label_map(cls, db: Session, data_source: str) -> dict[str, str]:
        """类型代码 → 名称。"""
        return cls._build_dim_label_map(db, data_source, level='type')

    @classmethod
    def _build_subtype_label_map(cls, db: Session, data_source: str) -> dict[str, str]:
        """细类代码 → 名称。"""
        return cls._build_dim_label_map(db, data_source, level='subtype')

    @classmethod
    def _resolve_share_dim_labels(
        cls,
        db: Session,
        rows: list[dict[str, Any]],
        data_source: str,
        *,
        code_key: str,
        name_key: str,
        level: str,
        unmapped_label: str | None = None,
    ) -> list[dict[str, Any]]:
        """把维度代码映射为中文名。

        unmapped_label：映射不到字典且仍像编码时的兜底（类型/细类用「其他」）。
        """
        if not rows:
            return rows
        label_map = cls._build_dim_label_map(db, data_source, level=level)
        for row in rows:
            code = str(row.get(code_key) or '').strip()
            name = str(row.get(name_key) or '').strip()
            if name and not cls._looks_like_type_code(name):
                row[name_key] = name
                continue
            resolved = ''
            for key in (code, name, code.lstrip('0') if code else ''):
                if key and key in label_map:
                    resolved = str(label_map[key] or '').strip()
                    if resolved and not cls._looks_like_type_code(resolved):
                        break
                    resolved = ''
            if resolved:
                row[name_key] = resolved
            elif unmapped_label:
                row[name_key] = unmapped_label
            else:
                row[name_key] = name or code
        if unmapped_label:
            return cls._merge_share_rows_by_display_name(rows, code_key=code_key, name_key=name_key)
        return rows

    @classmethod
    def _merge_share_rows_by_display_name(
        cls,
        rows: list[dict[str, Any]],
        *,
        code_key: str,
        name_key: str,
    ) -> list[dict[str, Any]]:
        """同名维度合并（多个未映射码都叫「其他」时汇总计数）。"""
        if not rows:
            return rows
        grouped: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for row in rows:
            name = str(row.get(name_key) or '').strip()
            if not name:
                name = str(row.get(code_key) or '').strip() or '其他'
            if name not in grouped:
                order.append(name)
                grouped[name] = {
                    code_key: str(row.get(code_key) or '').strip() or name,
                    name_key: name,
                    'cur_total': 0.0,
                    'mom_total': 0.0,
                    'yoy_total': 0.0,
                }
            bucket = grouped[name]
            for field in ('cur_total', 'mom_total', 'yoy_total'):
                try:
                    bucket[field] = float(bucket.get(field) or 0) + float(row.get(field) or 0)
                except (TypeError, ValueError):
                    pass

        scope = sum(float(item.get('cur_total') or 0) for item in grouped.values())
        merged: list[dict[str, Any]] = []
        for name in order:
            item = grouped[name]
            cur = float(item.get('cur_total') or 0)
            mom = float(item.get('mom_total') or 0)
            yoy = float(item.get('yoy_total') or 0)
            item['share'] = round((cur / scope * 100.0) if scope > 0 else 0.0, 2)
            item['mom'] = round(((cur - mom) / mom * 100.0) if mom > 0 else 0.0, 2)
            item['yoy'] = round(((cur - yoy) / yoy * 100.0) if yoy > 0 else 0.0, 2)
            merged.append(item)
        merged.sort(key=lambda r: (-float(r.get('cur_total') or 0), str(r.get(name_key) or '')))
        return merged

    @classmethod
    def _resolve_category_share_labels(
        cls,
        db: Session,
        rows: list[dict[str, Any]],
        data_source: str,
    ) -> list[dict[str, Any]]:
        """把类别代码映射为中文名。"""
        return cls._resolve_share_dim_labels(
            db,
            rows,
            data_source,
            code_key='category_code',
            name_key='category_name',
            level='category',
        )

    @classmethod
    def _resolve_type_share_labels(
        cls,
        db: Session,
        rows: list[dict[str, Any]],
        data_source: str,
    ) -> list[dict[str, Any]]:
        """把类型代码映射为中文名；字典未命中显示「其他」。"""
        return cls._resolve_share_dim_labels(
            db,
            rows,
            data_source,
            code_key='type_code',
            name_key='type_name',
            level='type',
            unmapped_label='其他',
        )

    @classmethod
    def _resolve_subtype_share_labels(
        cls,
        db: Session,
        rows: list[dict[str, Any]],
        data_source: str,
    ) -> list[dict[str, Any]]:
        """把细类代码映射为中文名；字典未命中显示「其他」。"""
        return cls._resolve_share_dim_labels(
            db,
            rows,
            data_source,
            code_key='subtype_code',
            name_key='subtype_name',
            level='subtype',
            unmapped_label='其他',
        )

    @classmethod
    def _resolve_dim_combo_labels(
        cls,
        db: Session,
        rows: list[dict[str, Any]],
        data_source: str,
        levels: list[str],
    ) -> list[dict[str, Any]]:
        """组合维度：按 levels 逐层把代码映射为中文名。"""
        resolved = rows
        for level in levels:
            if level == 'category':
                resolved = cls._resolve_category_share_labels(db, resolved, data_source)
            elif level == 'type':
                resolved = cls._resolve_type_share_labels(db, resolved, data_source)
            elif level == 'subtype':
                resolved = cls._resolve_subtype_share_labels(db, resolved, data_source)
        return resolved

    @classmethod
    def _format_dim_combo_table(
        cls,
        rows: list[dict[str, Any]],
        *,
        levels: list[str],
        top_n: int | None = None,
        count_threshold: tuple[str, float] | None = None,
    ) -> tuple[list[str], list[list[str]], str]:
        """组合维度 → 表头、行、文案（如：行政-偷盗 10起、刑事-偷盗 5起）。"""
        label_map = {'category': '类别', 'type': '类型', 'subtype': '细类'}
        name_keys = {
            'category': ('category_name', 'category_code'),
            'type': ('type_name', 'type_code'),
            'subtype': ('subtype_name', 'subtype_code'),
        }
        headers = [label_map[level] for level in levels if level in label_map] + ['数量']
        table_rows: list[list[str]] = []
        text_parts: list[str] = []
        for row in rows:
            try:
                cur_total = int(float(row.get('cur_total') or 0))
            except (TypeError, ValueError):
                cur_total = 0
            if cur_total <= 0:
                continue
            if not cls._pass_count_threshold(cur_total, count_threshold):
                continue
            names: list[str] = []
            for level in levels:
                keys = name_keys.get(level) or ()
                name = ''
                for key in keys:
                    name = str(row.get(key) or '').strip()
                    if name:
                        break
                if not name:
                    name = '其他'
                names.append(name)
            if not names:
                continue
            count_text = str(cur_total)
            table_rows.append([*names, count_text])
            joined = '-'.join(names) if len(names) > 1 else names[0]
            text_parts.append(f'{joined}{cur_total}起')
        if top_n and top_n > 0:
            table_rows = table_rows[:top_n]
            text_parts = text_parts[:top_n]
        return headers, table_rows, '、'.join(text_parts) if text_parts else '无'

    @classmethod
    def _format_type_share_pct(cls, value: Any) -> str:
        try:
            num = float(value)
        except (TypeError, ValueError):
            return '0.00'
        text = f'{num:.2f}'.rstrip('0').rstrip('.')
        return text or '0'

    @classmethod
    def _format_type_yoy_phrase(cls, yoy: float | None) -> str:
        if yoy is None:
            return '同比持平'
        if yoy > 0:
            return f'同比上升{cls._format_type_share_pct(yoy)}%'
        if yoy < 0:
            return f'同比下降{cls._format_type_share_pct(abs(yoy))}%'
        return '同比持平'

    @classmethod
    def _format_type_mom_phrase(cls, mom: float | None) -> str:
        if mom is None:
            return '环比持平'
        if mom > 0:
            return f'环比上升{cls._format_type_share_pct(mom)}%'
        if mom < 0:
            return f'环比下降{cls._format_type_share_pct(abs(mom))}%'
        return '环比持平'

    @classmethod
    def _format_dim_share_label(
        cls,
        level: str,
        *,
        include_share: bool = False,
        include_yoy: bool = False,
        include_mom: bool = False,
        include_yoy_count: bool = False,
        include_mom_count: bool = False,
        top_n: int | None = None,
    ) -> str:
        """类别 / 占比·同比数·类别 等前缀。"""
        bits: list[str] = []
        if include_share:
            bits.append('占比')
        if include_mom_count:
            bits.append('环比数')
        if include_yoy_count:
            bits.append('同比数')
        if include_yoy:
            bits.append('同比')
        if include_mom:
            bits.append('环比')
        bits.append(level)
        label = '·'.join(bits)
        if top_n and top_n > 0:
            label = f'{label}前{top_n}位'
        return label

    @classmethod
    def _format_dim_share_list(
        cls,
        rows: list[dict[str, Any]],
        *,
        name_keys: tuple[str, ...],
        top_n: int | None = None,
        include_share: bool = False,
        include_yoy: bool = False,
        include_mom: bool = False,
        include_yoy_count: bool = False,
        include_mom_count: bool = False,
        count_threshold: tuple[str, float] | None = None,
        sort_by: RankSortBy = 'count',
        sort_order: RankSortOrder = 'desc',
    ) -> str:
        """仅层级：诈骗案85起；+占比/同比/环比/同比数/环比数时再拼括号细节。"""
        items: list[tuple[str, int, float, float | None, float | None, int, int]] = []
        for row in rows:
            name = ''
            for key in name_keys:
                name = str(row.get(key) or '').strip()
                if name:
                    break
            if not name:
                continue
            try:
                cur_total = int(float(row.get('cur_total') or 0))
            except (TypeError, ValueError):
                cur_total = 0
            if cur_total <= 0:
                continue
            if not cls._pass_count_threshold(cur_total, count_threshold):
                continue
            try:
                share = float(row.get('share') or 0)
            except (TypeError, ValueError):
                share = 0.0
            yoy: float | None = None
            if include_yoy or sort_by == 'yoy':
                try:
                    yoy = float(row.get('yoy'))
                except (TypeError, ValueError):
                    yoy = 0.0
            mom: float | None = None
            if include_mom or sort_by == 'mom':
                try:
                    mom = float(row.get('mom'))
                except (TypeError, ValueError):
                    mom = 0.0
            try:
                yoy_cnt = int(float(row.get('yoy_total') or row.get('yoy_cnt') or 0))
            except (TypeError, ValueError):
                yoy_cnt = 0
            try:
                mom_cnt = int(float(row.get('mom_total') or row.get('mom_cnt') or 0))
            except (TypeError, ValueError):
                mom_cnt = 0
            items.append((name, cur_total, share, yoy, mom, yoy_cnt, mom_cnt))
        cls._sort_dim_rank_items(items, sort_by, sort_order)
        if top_n and top_n > 0:
            items = items[:top_n]
        parts: list[str] = []
        for name, cur_total, share, yoy, mom, yoy_cnt, mom_cnt in items:
            detail: list[str] = []
            if include_share:
                detail.append(f'占比{cls._format_type_share_pct(share)}%')
            if include_yoy:
                detail.append(cls._format_type_yoy_phrase(yoy))
            if include_yoy_count:
                detail.append(f'同比数{yoy_cnt}起')
            if include_mom:
                detail.append(cls._format_type_mom_phrase(mom))
            if include_mom_count:
                detail.append(f'环比数{mom_cnt}起')
            if detail:
                parts.append(f'{name}{cur_total}起（{"，".join(detail)}）')
            else:
                parts.append(f'{name}{cur_total}起')
        return '、'.join(parts)

    @classmethod
    def _format_category_share_list(
        cls,
        rows: list[dict[str, Any]],
        top_n: int | None = None,
        *,
        include_share: bool = False,
        include_yoy: bool = False,
        include_mom: bool = False,
        include_yoy_count: bool = False,
        include_mom_count: bool = False,
        count_threshold: tuple[str, float] | None = None,
        sort_by: RankSortBy = 'count',
        sort_order: RankSortOrder = 'desc',
    ) -> str:
        """刑事警情120起；勾选占比/同比/环比/同比数/环比数时再附加。"""
        return cls._format_dim_share_list(
            rows,
            name_keys=('category_name', 'category_code'),
            top_n=top_n,
            include_share=include_share,
            include_yoy=include_yoy,
            include_mom=include_mom,
            include_yoy_count=include_yoy_count,
            include_mom_count=include_mom_count,
            count_threshold=count_threshold,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    @classmethod
    def _format_type_share_list(
        cls,
        rows: list[dict[str, Any]],
        top_n: int | None = None,
        *,
        include_share: bool = False,
        include_yoy: bool = False,
        include_mom: bool = False,
        include_yoy_count: bool = False,
        include_mom_count: bool = False,
        count_threshold: tuple[str, float] | None = None,
        sort_by: RankSortBy = 'count',
        sort_order: RankSortOrder = 'desc',
    ) -> str:
        """诈骗案85起；勾选占比/同比/环比/同比数/环比数时再附加。"""
        return cls._format_dim_share_list(
            rows,
            name_keys=('type_name', 'type_code'),
            top_n=top_n,
            include_share=include_share,
            include_yoy=include_yoy,
            include_mom=include_mom,
            include_yoy_count=include_yoy_count,
            include_mom_count=include_mom_count,
            count_threshold=count_threshold,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    @classmethod
    def _format_subtype_share_list(
        cls,
        rows: list[dict[str, Any]],
        top_n: int | None = None,
        *,
        include_share: bool = False,
        include_yoy: bool = False,
        include_mom: bool = False,
        include_yoy_count: bool = False,
        include_mom_count: bool = False,
        count_threshold: tuple[str, float] | None = None,
        sort_by: RankSortBy = 'count',
        sort_order: RankSortOrder = 'desc',
    ) -> str:
        """入室盗窃12起；勾选占比/同比/环比/同比数/环比数时再附加。"""
        return cls._format_dim_share_list(
            rows,
            name_keys=('subtype_name', 'subtype_code'),
            top_n=top_n,
            include_share=include_share,
            include_yoy=include_yoy,
            include_mom=include_mom,
            include_yoy_count=include_yoy_count,
            include_mom_count=include_mom_count,
            count_threshold=count_threshold,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    @classmethod
    def _resolve_hot_period_hours(
        cls, merged: dict[str, Any], body: AtomicMetricQueryRequest
    ) -> int:
        raw = merged.get('hot_period_hours')
        if raw is None or raw == '':
            raw = merged.get('hotPeriodHours')
        if raw is None or raw == '':
            raw = body.hot_period_hours
        try:
            value = int(float(raw)) if raw is not None and raw != '' else 2
        except (TypeError, ValueError):
            value = 2
        return max(1, min(value, 12))

    @classmethod
    def _format_hot_period_list(
        cls,
        rows: list[dict[str, Any]],
        top_n: int | None = None,
        *,
        count_threshold: tuple[str, float] | None = None,
    ) -> str:
        """0-1时：12起，1-2时：8起"""
        parts: list[str] = []
        for row in rows or []:
            try:
                start = int(float(row.get('slot_start') or 0))
            except (TypeError, ValueError):
                continue
            try:
                end = int(float(row.get('slot_end') or (start + 1)))
            except (TypeError, ValueError):
                end = start + 1
            try:
                total = int(float(row.get('total') or 0))
            except (TypeError, ValueError):
                total = 0
            if total <= 0:
                continue
            if not cls._pass_count_threshold(total, count_threshold):
                continue
            parts.append(f'{start}-{end}时：{total}起')
            if top_n and len(parts) >= top_n:
                break
        return '，'.join(parts)

    @classmethod
    def _format_hot_community_list(
        cls,
        rows: list[dict[str, Any]],
        top_n: int | None = None,
        *,
        include_share: bool = False,
        include_yoy: bool = False,
        include_mom: bool = False,
        include_yoy_count: bool = False,
        include_mom_count: bool = False,
        count_threshold: tuple[str, float] | None = None,
        sort_by: RankSortBy = 'count',
        sort_order: RankSortOrder = 'desc',
    ) -> str:
        """五爱社区：30起；勾选占比/同比/环比/同比数/环比数时附加括号细节。

        兼容两套行结构：
        - 高发社区：fasqmc / total
        - 社区同比：unit_name / today_cnt / mom_cnt / yoy_cnt
        """
        items: list[tuple[str, int, float, float | None, float | None, int, int]] = []
        scope_total = 0
        parsed: list[tuple[str, int, int, int]] = []
        for row in rows or []:
            name = str(
                row.get('fasqmc')
                or row.get('unit_name')
                or row.get('fasqdm')
                or row.get('unit_code')
                or ''
            ).strip()
            if not name:
                continue
            try:
                total = int(
                    float(
                        row.get('total')
                        if row.get('total') is not None
                        else (row.get('today_cnt') or 0)
                    )
                )
            except (TypeError, ValueError):
                total = 0
            if total <= 0:
                continue
            try:
                mom_cnt = int(float(row.get('mom_cnt') or row.get('mom_total') or 0))
            except (TypeError, ValueError):
                mom_cnt = 0
            try:
                yoy_cnt = int(float(row.get('yoy_cnt') or row.get('yoy_total') or 0))
            except (TypeError, ValueError):
                yoy_cnt = 0
            parsed.append((name, total, mom_cnt, yoy_cnt))
            scope_total += total

        for name, total, mom_cnt, yoy_cnt in parsed:
            if not cls._pass_count_threshold(total, count_threshold):
                continue
            share = (total / scope_total * 100.0) if scope_total > 0 else 0.0
            yoy: float | None = None
            if include_yoy or sort_by == 'yoy':
                yoy = (
                    ((total - yoy_cnt) / yoy_cnt * 100.0) if yoy_cnt > 0 else 0.0
                )
            mom: float | None = None
            if include_mom or sort_by == 'mom':
                mom = (
                    ((total - mom_cnt) / mom_cnt * 100.0) if mom_cnt > 0 else 0.0
                )
            items.append((name, total, share, yoy, mom, yoy_cnt, mom_cnt))

        cls._sort_dim_rank_items(items, sort_by, sort_order)
        if top_n and top_n > 0:
            items = items[:top_n]

        parts: list[str] = []
        for name, total, share, yoy, mom, yoy_cnt, mom_cnt in items:
            detail: list[str] = []
            if include_share:
                detail.append(f'占比{cls._format_type_share_pct(share)}%')
            if include_yoy:
                detail.append(cls._format_type_yoy_phrase(yoy))
            if include_yoy_count:
                detail.append(f'同比数{yoy_cnt}起')
            if include_mom:
                detail.append(cls._format_type_mom_phrase(mom))
            if include_mom_count:
                detail.append(f'环比数{mom_cnt}起')
            if detail:
                parts.append(f'{name}：{total}起（{"，".join(detail)}）')
            else:
                parts.append(f'{name}：{total}起')
        return '，'.join(parts)

    @classmethod
    def _merge_params(cls, body: AtomicMetricQueryRequest) -> dict[str, Any]:
        merged: dict[str, Any] = dict(body.params or {})
        for key, value in {
            'data_source': body.data_source,
            'dept_code': body.dept_code,
            'date_start': body.date_start,
            'date_end': body.date_end,
            'document_type': body.document_type,
            'category_code': body.category_code,
            'category_name': body.category_name,
            'type_code': body.type_code,
            'subtype_code': body.subtype_code,
            'include_yoy': body.include_yoy,
            'include_mom': body.include_mom,
            'include_share': body.include_share,
            'include_yoy_count': body.include_yoy_count,
            'include_mom_count': body.include_mom_count,
            'include_cumulative': body.include_cumulative,
            'include_dim_combo': body.include_dim_combo,
            'dim_combo_levels': body.dim_combo_levels,
            'include_category_share': body.include_category_share,
            'include_type_share': body.include_type_share,
            'include_subtype_share': body.include_subtype_share,
            'include_hot_community': body.include_hot_community,
            'org_dimension': body.org_dimension,
            'include_hot_period': body.include_hot_period,
            'hot_period_hours': body.hot_period_hours,
            'include_region_table': body.include_region_table,
            'filter_duplicate': body.filter_duplicate,
            'exclude_non_police': body.exclude_non_police,
            'exclude_traffic': body.exclude_traffic,
            'filter_self_received': body.filter_self_received,
            'exclude_self_received': body.exclude_self_received,
            'tag_package_id': body.tag_package_id,
            'yoy_trend': body.yoy_trend,
            'trend_compare': body.trend_compare,
            'yoy_analysis_drill': body.yoy_analysis_drill,
            'yoy_trend_top_n': body.yoy_trend_top_n,
            'rank_sort_by': body.rank_sort_by,
            'rank_sort_order': body.rank_sort_order,
            'count_threshold_op': body.count_threshold_op,
            'count_threshold_value': body.count_threshold_value,
            'include_warning': body.include_warning,
            'warning_rule_type': body.warning_rule_type,
        }.items():
            if value is None or value == '':
                continue
            merged[key] = value

        # 维度别名归一
        category = _pick(
            merged,
            'category_code',
            'categoryCode',
            'feedback_category_code',
            'ajlb',
            'ajlbbh',
            'ajlbdm',
            'bjlb',
            'bjlbdm',
        )
        type_code = _pick(
            merged,
            'type_code',
            'typeCode',
            'feedback_type_code',
            'ajlx',
            'ajlxbh',
            'ajlxdm',
            'bjlx',
            'bjlxdm',
        )
        subtype = _pick(
            merged,
            'subtype_code',
            'subtypeCode',
            'feedback_subtype_code',
            'ajxl',
            'ajxlbh',
            'ajxldm',
            'bjxl',
            'bjxldm',
        )
        if category:
            merged['category_code'] = category
            merged['ajlb'] = category
            merged['bjlb'] = category
        if type_code:
            merged['type_code'] = type_code
            merged['ajlx'] = type_code
            merged['bjlx'] = type_code
        if subtype:
            merged['subtype_code'] = subtype
            merged['ajxl'] = subtype
            merged['bjxl'] = subtype
            merged['feedback_subtype_code'] = subtype

        trend = _normalize_yoy_trend(merged.get('yoy_trend') or merged.get('yoyTrend'))
        if trend:
            merged['yoy_trend'] = trend
        return merged

