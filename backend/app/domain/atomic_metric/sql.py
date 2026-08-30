"""原子模式 SQL 拼装（改查询口径 / SQL 优先改本文件）。

入口：AtomicMetricService.query → 本模块 AtomicMetricSql

================================================================================
【口径对照】与组件模式保持一致（intel_component.sql 注释）
================================================================================
| 场景                         | 时间列        | 部门列      | 市局匹配   | 对应组件              |
|------------------------------|---------------|-------------|------------|-----------------------|
| 无类别/类型/细类（总量）     | insert_time   | fkdwdm      | LEFT 6     | stat_alarm_total_text |
| 有类别/类型/细类             | bjsj          | txfkdwdm    | LEFT 6     | 类别/类型/细类组件    |
| 研判包过滤（fkd）            | bjsj          | fkdwdm      | LEFT 6     | 对齐 ywjq_analysis 取号 |
| 地区表（与总量同口径）       | 同上          | 同上        | 同上       | 全市 DISTINCT，非各所加 |
| 接警单 jjd_*                 | 动态解析      | gxdwdm优先  | LEFT 6     | —                     |

聚合：
- 接警单有 zjjdbh+jjdbh：COUNT(DISTINCT COALESCE(NULLIF(zjjdbh,''), jjdbh))
- 否则有 jjdbh：COUNT(DISTINCT jjdbh)；再否则 cjdbh / COUNT(*)
- 部门过滤后附加：dept_expr IS NOT NULL
- 类别/类型/细类占比：有单号时先按案去重再按维度聚合（避免 fkd 多反馈行跨类型重复计数）

可选过滤：
- filter_duplicate=True → 仅接警单(jjd)生效，按报警时间+同一电话判定重复：
    · 同号且间隔 8 分钟～60 分钟
    · 当前警情为纠纷（zd_* 字典名称含「纠纷」）时，同号扩到 8 分钟～72 小时
  （反馈单不套用；不再使用 jjdcllxdm=3）
- exclude_non_police=True → 排除非警务类别（ajlbbh/ajlbdm/bjlbdm=700000 或名称含非警务）
- exclude_traffic=True → 排除交通类别（ajlbbh/ajlbdm/bjlbdm=20000 或名称交通/交通警情）
- filter_self_received=True → 自接警：接警单位代码 jjdwdm = 管辖单位代码 gxdwdm
- exclude_self_received=True → 除自接警：排除 jjdwdm = gxdwdm 的记录
- tag_package_id → 先按研判包标签查 ywjq_analysis 得 cjdbh（勾选同比/环比时时间窗扩到历史期），再强制用 fkd_fkd 按 cjdbh IN (...) 过滤（勿用 jjd）
- 社区统计取 fkd_fkd.sdsq；前端选接警单时用 jjd_jjd.jjdbh=fkd.jjdbh 关联，维度/时间/部门按接警单过滤
- 类别=刑事(10)/行政(治安)(20)/交通(20000) → 不再自动切表，一律跟前端全局数据源；交通辖区仍可按名称保留中队/大队
- 类型/细类拆分同样跟全局数据源，不因字典码差异自动改查另一张表
- 地区/同比趋势单位名排除：中队、大队、分局、市局、指挥中心（类别=交通时保留中队/大队）

================================================================================
【函数索引】需要改哪段 SQL 就找哪个函数
================================================================================
口径解析
  1. resolve_metric_scope       — 时间列 / 部门列 / LEFT 位数
  2. resolve_case_id_expr       — 去重主键（zjjdbh 优先）
  3. resolve_total_agg          — COUNT(...) 聚合
  4. resolve_dimension_filters  — 类别/类型/细类 → 绑定参数
  5. _resolve_alarm_unit_scope  — 地区表部门列 / 去重键 / jz_dept 单位名

WHERE 片段
  6. _dept_where / _dim_where / _repeat_where / _case_id_in_where

业务 SQL
  7. build_total_sql            — 总量（可选同比/环比）★ 最常改
  8. build_base_total_sql       — 占比分母（同范围不限维度）
  9. build_category_share_sql   — 类别占比
 10. build_type_share_sql       — 类型占比
 11. build_subtype_share_sql    — 细类占比
  12. build_hot_community_sql    — 社区（fkd.sdsq；接警口径可 jjdbh 关联 jjd）
  12b. build_community_yoy_sql    — 社区同比（同口径）
 12c. build_hot_period_sql       — 高发时段（按 N 小时分桶）
  13. build_region_station_sql   — 地区表（jz_dept + 当期量，含全市；同比环比程序算）
                                  下级所同比趋势 / 同比分析复用，由 service 过滤文案
 14. build_station_dim_yoy_sql  — 同比分析下钻：指定派出所 × 类别/类型 同比

绑定参数：:date_start :date_end :dept_code
  以及维度 :ajlb/:ajlx/:ajxl 或 :bjlb/:bjlx/:bjxl（空字符串 = 不过滤）
地区时间窗：与总量一致（DATETIME + DATE_END_EXCLUSIVE_EXPR）；全市行 unit_code='00'
"""

from __future__ import annotations

import re
from typing import Any

from app.domain.atomic_metric.exceptions import ServiceException
from app.domain.atomic_metric.sql_rules import DATE_END_EXCLUSIVE_EXPR, date_end_bound_expr


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
            # 兼容「10, 20」空格
            if ',' in text:
                parts = [part.strip() for part in text.split(',') if part.strip()]
                return ','.join(parts) if parts else ''
            return text
    return ''


def _is_city_bureau_code(dept_code: str | None) -> bool:
    """市局码：以 000000 结尾（如 330782000000）。"""
    text = str(dept_code or '').strip()
    return bool(text) and text.endswith('000000')


def _dept_where(
    dept_expr: str,
    prefix_len: int = 6,
    *,
    dept_code: str | None = None,
    require_not_null: bool = True,
) -> str:
    """部门过滤片段。

    传入 dept_code 时按实值简化：
    - 空：不加条件
    - 市局：LEFT(col,6)=LEFT(:dept_code,6)
    - 派出所：col = :dept_code
    未传 dept_code 时保留兼容的 IF 绑定写法。
    """
    n = 6 if int(prefix_len) <= 0 else min(int(prefix_len), 6)
    not_null = f'\n  AND {dept_expr} IS NOT NULL' if require_not_null else ''
    if dept_code is not None:
        code = str(dept_code or '').strip()
        if not code:
            return ''
        if _is_city_bureau_code(code):
            return f'\n  AND LEFT({dept_expr}, {n}) = LEFT(:dept_code, {n}){not_null}'
        return f'\n  AND {dept_expr} = :dept_code'

    return f"""
  AND (
    :dept_code = ''
    OR IF(
      RIGHT(:dept_code, 6) = '000000',
      LEFT({dept_expr}, {n}) = LEFT(:dept_code, {n}),
      {dept_expr} = :dept_code
    )
  ){not_null}"""


def _dim_where(
    dim_filters: dict[str, str],
    *,
    dim_values: dict[str, str] | None = None,
    qualify_alias: str | None = None,
) -> str:
    """维度过滤。

    传入 dim_values 时：空值跳过；单值用等值；多值用 FIND_IN_SET。
    未传时保留「空串跳过」的兼容写法。
    """
    if not dim_filters:
        return ''
    parts: list[str] = []
    for param, col in dim_filters.items():
        col_expr = AtomicMetricSql.qualify_expr(col, qualify_alias) if qualify_alias else col
        if dim_values is not None:
            value = str(dim_values.get(param) or '').strip()
            if not value:
                continue
            if ',' in value:
                parts.append(f'FIND_IN_SET(CAST({col_expr} AS CHAR), :{param}) > 0')
            else:
                parts.append(f'CAST({col_expr} AS CHAR) = :{param}')
        else:
            parts.append(
                f"(:{param} = '' OR FIND_IN_SET(CAST({col_expr} AS CHAR), :{param}) > 0)"
            )
    if not parts:
        return ''
    return '\n  AND ' + ' AND '.join(parts)


def _case_id_col(columns: set[str]) -> str | None:
    for name in ('jjdbh', 'cjdbh', 'zjjdbh'):
        if name in columns:
            return name
    return None


def _is_jjd_table(table_name: str | None) -> bool:
    """是否接警单表（重复口径仅接警单生效）。"""
    if not table_name:
        return False
    name = str(table_name).strip().lower().split('.')[-1]
    return name == 'jjd_jjd' or name.startswith('jjd_')


def _outer_is_dispute_pred(*, outer_prefix: str, columns: set[str]) -> str:
    """外表是否纠纷类别。

    接警单无名称字段，优先用类别代码 100000（zd_bjlbdm「纠纷」）；
    无 bjlbdm 时再回退字典 IN 子查询。
    """
    if 'bjlbdm' in columns:
        # 义乌字典：100000 = 纠纷（避免逐行 IN 子查询拖慢）
        return f"CAST({outer_prefix}.bjlbdm AS CHAR) = '100000'"
    dispute_like = "LIKE CONCAT('%', CONVERT(UNHEX('E7BAA0E7BAB7') USING utf8mb4), '%')"
    for col_name, dict_table, dict_code, dict_name in (
        ('bjlxdm', 'zd_bjlxdm', 'bjlxdm', 'bjlxmc'),
        ('bjxldm', 'zd_bjxldm', 'bjxldm', 'bjxlmc'),
    ):
        if col_name not in columns:
            continue
        return (
            f"CAST({outer_prefix}.{col_name} AS CHAR) IN ("
            f"SELECT CAST(_zd.{dict_code} AS CHAR) FROM {dict_table} _zd"
            f" WHERE CAST(_zd.{dict_name} AS CHAR) {dispute_like})"
        )
    return '0'


def _repeat_pair_exists(
    *,
    table_name: str,
    outer_prefix: str,
    case_id: str,
    alarm_time: str,
    window_minutes: int,
    extra_and: str = '',
) -> str:
    """同号成对 EXISTS；bjdh 等值走 (bjdh,bjsj) 索引。"""
    outer_case = f'{outer_prefix}.{case_id}'
    outer_time = f'{outer_prefix}.{alarm_time}'
    outer_bjdh = f'{outer_prefix}.bjdh'
    diff = f'ABS(TIMESTAMPDIFF(MINUTE, {outer_time}, _rd.{alarm_time}))'
    # 注意：等值用 _rd.bjdh = 外表.bjdh（勿包函数），才能用 ind_jjd_jjd_bjdh2(bjdh,bjsj)
    return f"""EXISTS (
  SELECT 1
  FROM {table_name} _rd
  WHERE _rd.bjdh = {outer_bjdh}
    AND {outer_bjdh} IS NOT NULL
    AND {outer_bjdh} <> ''
    AND _rd.{case_id} <> {outer_case}
    AND _rd.{alarm_time} >= DATE_SUB({outer_time}, INTERVAL {window_minutes} MINUTE)
    AND _rd.{alarm_time} <= DATE_ADD({outer_time}, INTERVAL {window_minutes} MINUTE)
    AND {diff} >= 8
    AND {diff} <= {window_minutes}
    {extra_and}
)"""


def _repeat_lxdh_exists(
    *,
    table_name: str,
    outer_prefix: str,
    case_id: str,
    alarm_time: str,
    window_minutes: int,
) -> str:
    """无 bjdh 时回退 lxdh（少量行）。"""
    outer_case = f'{outer_prefix}.{case_id}'
    outer_time = f'{outer_prefix}.{alarm_time}'
    outer_bjdh = f'{outer_prefix}.bjdh'
    outer_lxdh = f'{outer_prefix}.lxdh'
    diff = f'ABS(TIMESTAMPDIFF(MINUTE, {outer_time}, _rd.{alarm_time}))'
    return f"""EXISTS (
  SELECT 1
  FROM {table_name} _rd
  WHERE ({outer_bjdh} IS NULL OR {outer_bjdh} = '')
    AND NULLIF(TRIM({outer_lxdh}), '') IS NOT NULL
    AND NULLIF(TRIM(_rd.lxdh), '') = NULLIF(TRIM({outer_lxdh}), '')
    AND _rd.{case_id} <> {outer_case}
    AND _rd.{alarm_time} >= DATE_SUB({outer_time}, INTERVAL {window_minutes} MINUTE)
    AND _rd.{alarm_time} <= DATE_ADD({outer_time}, INTERVAL {window_minutes} MINUTE)
    AND {diff} >= 8
    AND {diff} <= {window_minutes}
)"""


def _repeat_where(
    columns: set[str],
    *,
    enabled: bool,
    qualify_alias: str | None = None,
    table_name: str | None = None,
    time_col: str | None = None,
) -> str:
    """重复警情（仅接警单）：同电话按报警时间判定。

    - 同号且间隔 8 分钟～60 分钟
    - 当前警情为纠纷类别时，同号扩到 8 分钟～72 小时
      （成对另一侧若在统计期内，会作为外表再判一次，等价覆盖「任一侧纠纷」）
    反馈单等非接警单数据源不套用本规则（勾选「重复」时忽略）。

    注意：EXISTS 内必须用别名/表名限定外表列，否则 MySQL 会解析成 _rd 自身列，
    导致 jjdbh <> jjdbh 恒假、结果恒为 0。
    """
    if not enabled:
        return ''
    # 反馈单 / 社区强制 fkd 等：不套用同号时间窗
    if not _is_jjd_table(table_name):
        return ''

    # 重复一律按报警时间 bjsj；无 bjsj 时再回退当前口径时间列
    alarm_time = 'bjsj' if 'bjsj' in columns else (
        time_col if time_col and time_col in columns else None
    )
    if not alarm_time:
        raise ServiceException(message='当前接警单无报警时间字段，无法筛选重复警情')

    case_id = _case_id_col(columns)
    if not case_id:
        raise ServiceException(message='当前接警单无 jjdbh/cjdbh 字段，无法筛选重复警情')

    if 'bjdh' not in columns and 'lxdh' not in columns:
        raise ServiceException(message='当前接警单无报警电话字段，无法筛选重复警情')

    # 外表限定前缀：别名优先，否则用表名（避免 EXISTS 内列名落到 _rd）
    outer_prefix = qualify_alias or table_name
    if not outer_prefix:
        raise ServiceException(message='重复警情筛选缺少表名，无法生成关联条件')

    # 有 bjdh 走索引路径；无 bjdh 才回退 lxdh（勿与 bjdh 路径扁平 OR，否则优化器易退化）
    if 'bjdh' in columns:
        normal = _repeat_pair_exists(
            table_name=table_name,
            outer_prefix=outer_prefix,
            case_id=case_id,
            alarm_time=alarm_time,
            window_minutes=60,
        )
        bjdh_pred = normal
        outer_dispute = _outer_is_dispute_pred(outer_prefix=outer_prefix, columns=columns)
        if outer_dispute != '0':
            dispute_exists = _repeat_pair_exists(
                table_name=table_name,
                outer_prefix=outer_prefix,
                case_id=case_id,
                alarm_time=alarm_time,
                window_minutes=4320,
            )
            bjdh_pred = f'({normal} OR ({outer_dispute} AND {dispute_exists}))'
        return f' AND {bjdh_pred}'

    return (
        f' AND {_repeat_lxdh_exists(table_name=table_name, outer_prefix=outer_prefix, case_id=case_id, alarm_time=alarm_time, window_minutes=60)}'
    )


def _exclude_non_police_where(
    columns: set[str],
    *,
    enabled: bool,
    qualify_alias: str | None = None,
) -> str:
    """除去非警务：类别编码 700000 或名称「非警务」。"""
    if not enabled:
        return ''
    if any(name in columns for name in ('ajlbbh', 'ajlbdm', 'ajlb')):
        candidates = ('ajlbbh', 'ajlbdm', 'ajlb')
    elif any(name in columns for name in ('bjlbdm', 'bjlb')):
        candidates = ('bjlbdm', 'bjlb')
    else:
        candidates = ('alarm_type',)
    col_name = next((name for name in candidates if name in columns), None)
    if not col_name:
        raise ServiceException(message='当前数据源无类别字段，无法排除非警务')
    col = AtomicMetricSql.qualify_expr(col_name, qualify_alias) if qualify_alias else col_name
    return f" AND CAST({col} AS CHAR) NOT IN ('700000', '非警务', '非警务警情')"



def _exclude_traffic_where(
    columns: set[str],
    *,
    enabled: bool,
    qualify_alias: str | None = None,
) -> str:
    """除交通：类别编码 20000 或名称「交通」/「交通警情」。"""
    if not enabled:
        return ''
    if any(name in columns for name in ('ajlbbh', 'ajlbdm', 'ajlb')):
        candidates = ('ajlbbh', 'ajlbdm', 'ajlb')
    elif any(name in columns for name in ('bjlbdm', 'bjlb')):
        candidates = ('bjlbdm', 'bjlb')
    else:
        candidates = ('alarm_type',)
    col_name = next((name for name in candidates if name in columns), None)
    if not col_name:
        raise ServiceException(message='当前数据源无类别字段，无法排除交通')
    col = AtomicMetricSql.qualify_expr(col_name, qualify_alias) if qualify_alias else col_name
    return f" AND CAST({col} AS CHAR) NOT IN ('20000', '交通', '交通警情')"


def _self_received_same_unit_pred(alias: str = '_sr') -> str:
    """接警单位 = 管辖单位（非空）。"""
    return (
        f"NULLIF(TRIM(CAST({alias}.jjdwdm AS CHAR)), '') IS NOT NULL"
        f" AND TRIM(CAST({alias}.jjdwdm AS CHAR)) = TRIM(CAST({alias}.gxdwdm AS CHAR))"
    )


def _self_received_where(
    columns: set[str],
    *,
    enabled: bool,
    qualify_alias: str | None = None,
    table_name: str | None = None,
    exclude: bool = False,
) -> str:
    """自接警 / 除自接警：接警单位代码与管辖单位代码是否相同。

    接警单直接比 jjdwdm/gxdwdm；反馈单无这两列时经 jjdbh 关联 jjd_jjd。

    反馈单路径优先用相关 EXISTS/NOT EXISTS（可走 jjdbh 索引），
    避免 NOT IN (全表自接警子查询) 在高发社区等多表关联下极慢。
    EXISTS 外层 jjdbh 必须带表名/别名，否则会解析成子查询自身列导致恒真。
    """
    if not enabled:
        return ''
    if 'jjdwdm' in columns and 'gxdwdm' in columns:
        jj = AtomicMetricSql.qualify_expr('jjdwdm', qualify_alias) if qualify_alias else 'jjdwdm'
        gx = AtomicMetricSql.qualify_expr('gxdwdm', qualify_alias) if qualify_alias else 'gxdwdm'
        same = (
            f"NULLIF(TRIM(CAST({jj} AS CHAR)), '') IS NOT NULL"
            f" AND TRIM(CAST({jj} AS CHAR)) = TRIM(CAST({gx} AS CHAR))"
        )
        return f" AND NOT ({same})" if exclude else f" AND {same}"
    if 'jjdbh' in columns:
        if qualify_alias:
            outer_jjdbh = f'{qualify_alias}.jjdbh'
        elif table_name:
            outer_jjdbh = f'{table_name}.jjdbh'
        else:
            outer_jjdbh = ''
        same_pred = _self_received_same_unit_pred('_sr')
        if outer_jjdbh:
            exists = (
                f"EXISTS (SELECT 1 FROM jjd_jjd _sr"
                f" WHERE _sr.jjdbh = {outer_jjdbh} AND {same_pred})"
            )
            return f" AND NOT {exists}" if exclude else f" AND {exists}"
        # 无表名时退回 IN（调用方应尽量传 table_name / qualify_alias）
        op = 'NOT IN' if exclude else 'IN'
        return (
            f" AND jjdbh {op} ("
            f"SELECT _sr.jjdbh FROM jjd_jjd _sr"
            f" WHERE {same_pred} AND _sr.jjdbh IS NOT NULL)"
        )
    raise ServiceException(
        message=f"当前数据源无接警单位/管辖单位字段，无法筛选{'除' if exclude else ''}自接警"
    )


def _optional_filter_where(
    columns: set[str],
    *,
    filter_duplicate: bool = False,
    exclude_non_police: bool = False,
    exclude_traffic: bool = False,
    filter_self_received: bool = False,
    exclude_self_received: bool = False,
    qualify_alias: str | None = None,
    table_name: str | None = None,
    time_col: str | None = None,
    extra_where: str = '',
) -> str:
    """重复 / 除去非警务 / 除交通 / 自接警 / 除自接警 / 额外条件拼接。"""
    if filter_self_received and exclude_self_received:
        raise ServiceException(message='不能同时勾选自接警与除自接警')
    return (
        f'{_repeat_where(columns, enabled=filter_duplicate, qualify_alias=qualify_alias, table_name=table_name, time_col=time_col)}'
        f'{_exclude_non_police_where(columns, enabled=exclude_non_police, qualify_alias=qualify_alias)}'
        f'{_exclude_traffic_where(columns, enabled=exclude_traffic, qualify_alias=qualify_alias)}'
        f'{_self_received_where(columns, enabled=filter_self_received, qualify_alias=qualify_alias, table_name=table_name)}'
        f'{_self_received_where(columns, enabled=exclude_self_received, qualify_alias=qualify_alias, table_name=table_name, exclude=True)}'
        f'{extra_where or ""}'
    )


def _case_id_in_where(
    columns: set[str],
    case_ids: list[str] | None,
    *,
    qualify_alias: str | None = None,
    param_prefix: str = 'pkg_cjdbh',
) -> tuple[str, dict[str, Any]]:
    """研判包命中单号过滤：优先 cjdbh，否则 jjdbh。

    case_ids is None → 不过滤；空列表 → 强制无结果（AND 1=0）。
    """
    if case_ids is None:
        return '', {}
    if not case_ids:
        return ' AND 1=0', {}
    col_name = 'cjdbh' if 'cjdbh' in columns else ('jjdbh' if 'jjdbh' in columns else '')
    if not col_name:
        raise ServiceException(message='当前数据源无 cjdbh/jjdbh 字段，无法按研判包过滤警情')
    col = AtomicMetricSql.qualify_expr(col_name, qualify_alias) if qualify_alias else col_name
    placeholders: list[str] = []
    params: dict[str, Any] = {}
    for index, item in enumerate(case_ids):
        key = f'{param_prefix}_{index}'
        placeholders.append(f':{key}')
        params[key] = item
    return f' AND {col} IN ({", ".join(placeholders)})', params


class AtomicMetricSql:
    """原子模式全部可执行 SQL 的拼装入口。"""

    # ------------------------------------------------------------------
    # 1) 口径 / 字段解析
    # ------------------------------------------------------------------

    @classmethod
    def build_case_id_filter(
        cls,
        columns: set[str],
        case_ids: list[str] | None,
        *,
        qualify_alias: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """研判包单号过滤片段 + 绑定参数。"""
        return _case_id_in_where(columns, case_ids, qualify_alias=qualify_alias)

    @classmethod
    def resolve_metric_scope(
        cls,
        columns: set[str],
        data_source: str,
        *,
        has_dimension: bool,
        for_tag_package: bool = False,
    ) -> tuple[str, str, int]:
        """返回 (time_col, dept_expr, dept_prefix_len)。改口径优先改这里。

        for_tag_package=True：研判包按 ywjq_analysis.bjsj 取 cjdbh，统计须同用 bjsj，
        否则无维度时走 insert_time，环比窗内常有数、同比窗（去年）易全空 → 同比恒 0%。
        """
        is_jjd = 'jjd' in (data_source or '').lower()
        if is_jjd:
            return (
                cls.resolve_time_column(columns, data_source),
                cls.resolve_dept_expr(columns, data_source),
                6,
            )
        if has_dimension or for_tag_package:
            # 有维度 / 研判包：对齐报警时间 bjsj（研判包额外对齐取号口径）
            time_col = (
                'bjsj'
                if 'bjsj' in columns
                else (
                    'insert_time'
                    if 'insert_time' in columns
                    else cls.resolve_time_column(columns, data_source)
                )
            )
            if has_dimension:
                dept_expr = (
                    'txfkdwdm'
                    if 'txfkdwdm' in columns
                    else (
                        'fkdwdm'
                        if 'fkdwdm' in columns
                        else cls.resolve_dept_expr(columns, data_source)
                    )
                )
                return time_col, dept_expr, 6
            # 研判包无维度：时间用 bjsj，部门仍对齐总量口径 fkdwdm LEFT 6
            dept_expr = (
                'fkdwdm' if 'fkdwdm' in columns else cls.resolve_dept_expr(columns, data_source)
            )
            return time_col, dept_expr, 6
        # 对齐接警总量：insert_time + fkdwdm + LEFT 6
        time_col = (
            'insert_time'
            if 'insert_time' in columns
            else cls.resolve_time_column(columns, data_source)
        )
        dept_expr = (
            'fkdwdm' if 'fkdwdm' in columns else cls.resolve_dept_expr(columns, data_source)
        )
        return time_col, dept_expr, 6

    @classmethod
    def resolve_time_column(cls, columns: set[str], data_source: str) -> str:
        prefer = ('bjsj', 'insert_time', 'jqfssj_dt', 'fksj_dt', 'alarm_time')
        for name in prefer:
            if name in columns:
                return name
        if 'jjd' in (data_source or '').lower():
            return 'bjsj'
        return 'insert_time'

    @classmethod
    def resolve_dept_expr(cls, columns: set[str], data_source: str) -> str:
        if 'jjd' in (data_source or '').lower():
            # 接警单：管辖单位优先，不再 COALESCE(jjdwdm)
            if 'gxdwdm' in columns:
                return 'gxdwdm'
            if 'jjdwdm' in columns:
                return 'jjdwdm'
        if 'txfkdwdm' in columns and 'fkdwdm' in columns:
            return 'COALESCE(txfkdwdm, fkdwdm)'
        if 'txfkdwdm' in columns:
            return 'txfkdwdm'
        if 'fkdwdm' in columns:
            return 'fkdwdm'
        if 'gxdwdm' in columns:
            return 'gxdwdm'
        return 'fkdwdm'

    @classmethod
    def resolve_case_id_expr(
        cls,
        columns: set[str],
        data_source: str = '',
        *,
        alias: str | None = None,
    ) -> str:
        """去重主键表达式；'*' 表示无单号列。

        接警单：有主单号 zjjdbh 时优先用它，否则 jjdbh。
        """

        def q(col: str) -> str:
            return f'{alias}.{col}' if alias else col

        if 'zjjdbh' in columns and 'jjdbh' in columns:
            z = q('zjjdbh')
            j = q('jjdbh')
            return f"COALESCE(NULLIF(TRIM({z}), ''), {j})"
        if 'jjdbh' in columns:
            return q('jjdbh')
        if 'cjdbh' in columns:
            return q('cjdbh')
        return '*'

    @classmethod
    def resolve_total_agg(cls, columns: set[str], data_source: str = '') -> str:
        """COUNT(...) 聚合表达式（不含 AS total）。"""
        case_id = cls.resolve_case_id_expr(columns, data_source)
        if case_id == '*':
            return 'COUNT(*)'
        return f'COUNT(DISTINCT {case_id})'

    @classmethod
    def resolve_dimension_filters(
        cls,
        columns: set[str],
        data_source: str,
        params: dict[str, Any],
    ) -> dict[str, str]:
        """返回 {bind_param: column_name}；空值仍注册，SQL 用 :param='' 跳过。

        反馈单 fkd_*：类别 ajlbbh / 类型 ajlxbh / 细类 ajxlbh
        接警单 jjd_*：类别 bjlbdm / 类型 bjlxdm / 细类 bjxldm
        """
        source = (data_source or '').lower()
        doc_type = _pick(params, 'document_type', 'documentType')
        # 以数据源为准；避免切到 fkd 后 documentType 仍是 incident 误用 bj* 列
        if 'fkd' in source:
            is_incident = False
        elif 'jjd' in source:
            is_incident = True
        else:
            is_incident = doc_type == 'incident'
        if is_incident:
            mapping: list[tuple[str, tuple[str, ...], str]] = [
                ('bjlb', ('bjlbdm', 'bjlb'), _pick(params, 'bjlb', 'category_code')),
                ('bjlx', ('bjlxdm', 'bjlx'), _pick(params, 'bjlx', 'type_code')),
                ('bjxl', ('bjxldm', 'bjxl'), _pick(params, 'bjxl', 'subtype_code')),
            ]
        else:
            mapping = [
                ('ajlb', ('ajlbbh', 'ajlbdm', 'ajlb'), _pick(params, 'ajlb', 'category_code')),
                ('ajlx', ('ajlxbh', 'ajlxdm', 'ajlx'), _pick(params, 'ajlx', 'type_code')),
                (
                    'ajxl',
                    ('ajxlbh', 'ajxldm', 'ajxl'),
                    _pick(params, 'ajxl', 'subtype_code', 'feedback_subtype_code'),
                ),
            ]
        filters: dict[str, str] = {}
        for param_name, candidates, _value in mapping:
            col = next((c for c in candidates if c in columns), candidates[0])
            filters[param_name] = col
        return filters

    @classmethod
    def resolve_category_group_exprs(cls, columns: set[str], data_source: str) -> tuple[str, str | None]:
        """返回 (类别代码列, 类别名称列)。反馈 ajlb 多为代码，名称走字典。"""
        if 'jjd' in (data_source or '').lower():
            code = next((c for c in ('bjlbdm', 'bjlb') if c in columns), 'bjlbdm')
            name = next((c for c in ('bjlbmc',) if c in columns), None)
            return code, name
        code = next((c for c in ('ajlbbh', 'ajlbdm', 'ajlb') if c in columns), 'ajlb')
        name = next((c for c in ('ajlbmc',) if c in columns), None)
        return code, name

    @classmethod
    def resolve_type_group_exprs(cls, columns: set[str], data_source: str) -> tuple[str, str | None]:
        """返回 (类型代码列, 类型名称列)。反馈 ajlx 多为代码，名称走字典。"""
        if 'jjd' in (data_source or '').lower():
            code = next((c for c in ('bjlxdm', 'bjlx') if c in columns), 'bjlxdm')
            name = next((c for c in ('bjlxmc',) if c in columns), None)
            return code, name
        code = next((c for c in ('ajlxbh', 'ajlxdm', 'ajlx') if c in columns), 'ajlx')
        name = next((c for c in ('ajlxmc',) if c in columns), None)
        return code, name

    @classmethod
    def resolve_subtype_group_exprs(cls, columns: set[str], data_source: str) -> tuple[str, str | None]:
        """返回 (细类代码列, 细类名称列)。反馈 ajxl 多为代码，名称走字典。"""
        if 'jjd' in (data_source or '').lower():
            code = next((c for c in ('bjxldm', 'bjxl') if c in columns), 'bjxldm')
            name = next((c for c in ('bjxlmc',) if c in columns), None)
            return code, name
        code = next((c for c in ('ajxlbh', 'ajxldm', 'ajxl') if c in columns), 'ajxl')
        name = next((c for c in ('ajxlmc',) if c in columns), None)
        return code, name

    @classmethod
    def qualify_expr(cls, expr: str, alias: str) -> str:
        """给列名 / COALESCE(...) 加表别名。"""
        keywords = {
            'COALESCE',
            'IFNULL',
            'NULLIF',
            'CAST',
            'TRIM',
            'LEFT',
            'RIGHT',
            'IF',
            'OR',
            'AND',
            'AS',
            'CHAR',
            'CASE',
            'WHEN',
            'THEN',
            'ELSE',
            'END',
        }
        tokens = re.findall(r'[A-Za-z_][A-Za-z0-9_]*', expr)
        result = expr
        for tok in sorted(set(tokens), key=len, reverse=True):
            if tok.upper() in keywords:
                continue
            result = re.sub(rf'(?<![.\w]){re.escape(tok)}(?!\s*\()', f'{alias}.{tok}', result)
        return result

    # ------------------------------------------------------------------
    # 2) 总量 / 占比分母
    # ------------------------------------------------------------------

    @classmethod
    def build_total_sql(
        cls,
        *,
        table_name: str,
        time_col: str,
        dept_expr: str,
        dim_filters: dict[str, str],
        total_agg: str,
        count_id: str,
        include_yoy: bool,
        include_mom: bool,
        dept_prefix_len: int = 6,
        columns: set[str] | None = None,
        filter_duplicate: bool = False,
        exclude_non_police: bool = False,
        exclude_traffic: bool = False,
        filter_self_received: bool = False,
        exclude_self_received: bool = False,
        extra_where: str = '',
        include_yoy_count: bool = False,
        include_mom_count: bool = False,
        dept_code: str | None = None,
        dim_values: dict[str, str] | None = None,
        date_end: str | None = None,
    ) -> str:
        """★ 总量 SQL：只查当期 COUNT。同比/环比/占比由 service 程序侧计算。"""
        # include_* 保留参数兼容旧调用，不再在 SQL 内算对比指标
        _ = (include_yoy, include_mom, include_yoy_count, include_mom_count, count_id)
        dim_where = _dim_where(dim_filters, dim_values=dim_values)
        dept_where = _dept_where(dept_expr, dept_prefix_len, dept_code=dept_code)
        end_bound = date_end_bound_expr(date_end)
        extra = _optional_filter_where(
            columns or set(),
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            table_name=table_name,
            time_col=time_col,
            extra_where=extra_where,
        )
        return f"""SELECT
  {total_agg} AS total
FROM {table_name}
WHERE {time_col} >= :date_start
  AND {time_col} < {end_bound}{dept_where}{dim_where}{extra}""".strip()

    @classmethod
    def build_base_total_sql(
        cls,
        *,
        table_name: str,
        time_col: str,
        dept_expr: str,
        total_agg: str,
        dept_prefix_len: int = 6,
        columns: set[str] | None = None,
        filter_duplicate: bool = False,
        exclude_non_police: bool = False,
        exclude_traffic: bool = False,
        filter_self_received: bool = False,
        exclude_self_received: bool = False,
        extra_where: str = '',
        dept_code: str | None = None,
        date_end: str | None = None,
    ) -> str:
        """占比分母：同时间/部门、不限类别类型细类。"""
        dept_where = _dept_where(dept_expr, dept_prefix_len, dept_code=dept_code)
        end_bound = date_end_bound_expr(date_end)
        extra = _optional_filter_where(
            columns or set(),
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            table_name=table_name,
            time_col=time_col,
            extra_where=extra_where,
        )
        return f"""SELECT
  {total_agg} AS total
FROM {table_name}
WHERE {time_col} >= :date_start
  AND {time_col} < {end_bound}{dept_where}{extra}""".strip()

    # ------------------------------------------------------------------
    # 3) 类别 / 类型 / 细类占比
    # ------------------------------------------------------------------

    @classmethod
    def _build_dim_share_sql(
        cls,
        *,
        table_name: str,
        time_col: str,
        dept_expr: str,
        dept_prefix_len: int,
        dim_filters: dict[str, str],
        count_id: str,
        columns: set[str],
        code_expr: str,
        name_expr: str | None,
        code_alias: str,
        name_alias: str,
        stats_alias: str,
        scope_total_alias: str,
        filter_duplicate: bool = False,
        exclude_non_police: bool = False,
        exclude_traffic: bool = False,
        filter_self_received: bool = False,
        exclude_self_received: bool = False,
        extra_where: str = '',
        dept_code: str | None = None,
        dim_values: dict[str, str] | None = None,
        date_end: str | None = None,
    ) -> str:
        """按维度代码分组：只返回当期量。

        有单号列时先按案件去重（每案每期只保留一个维度码），再按维度聚合，
        避免 fkd 多反馈行导致同一 cjdbh 跨类型重复计数（类型合计 > 总量）。
        同比/环比/占比由 service 程序侧计算。
        """
        dim_where = _dim_where(dim_filters, dim_values=dim_values)
        dept_where = _dept_where(dept_expr, dept_prefix_len, dept_code=dept_code)
        end_bound = date_end_bound_expr(date_end)
        extra = _optional_filter_where(
            columns,
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            table_name=table_name,
            time_col=time_col,
            extra_where=extra_where,
        )
        code_sql = f'TRIM(CAST({code_expr} AS CHAR))'
        if name_expr:
            name_pick_sql = f'TRIM(CAST({name_expr} AS CHAR))'
        else:
            name_pick_sql = code_sql
        code_not_empty = (
            f'AND {code_expr} IS NOT NULL AND TRIM(CAST({code_expr} AS CHAR)) <> \'\''
        )
        # 只查当期量；同比/环比/占比由 service 在程序侧计算
        # stats_alias / scope_total_alias 保留参数兼容旧调用，SQL 不再使用
        _ = (stats_alias, scope_total_alias)
        if count_id == '*':
            return f"""SELECT
  {code_sql} AS {code_alias},
  MAX({name_pick_sql}) AS {name_alias},
  COUNT(*) AS cur_total
FROM {table_name}
WHERE {time_col} >= :date_start
  AND {time_col} < {end_bound}{dept_where}{dim_where}{extra}
  {code_not_empty}
GROUP BY {code_sql}
HAVING COUNT(*) > 0
ORDER BY cur_total DESC, {code_alias}""".strip()

        pick_code = (
            f"SUBSTRING_INDEX(GROUP_CONCAT({code_sql} ORDER BY {time_col} DESC SEPARATOR '|'), '|', 1)"
        )
        pick_name = (
            f"SUBSTRING_INDEX(GROUP_CONCAT({name_pick_sql} ORDER BY {time_col} DESC SEPARATOR '|'), '|', 1)"
        )
        return f"""WITH cur_cases AS (
  SELECT
    {count_id} AS case_id,
    {pick_code} AS {code_alias},
    {pick_name} AS {name_alias}
  FROM {table_name}
  WHERE {time_col} >= :date_start
    AND {time_col} < {end_bound}{dept_where}{dim_where}{extra}
    {code_not_empty}
    AND {count_id} IS NOT NULL
    AND TRIM(CAST({count_id} AS CHAR)) <> ''
  GROUP BY {count_id}
)
SELECT
  {code_alias},
  MAX({name_alias}) AS {name_alias},
  COUNT(*) AS cur_total
FROM cur_cases
GROUP BY {code_alias}
HAVING COUNT(*) > 0
ORDER BY cur_total DESC, {code_alias}""".strip()

    @classmethod
    def build_dim_combo_sql(
        cls,
        *,
        table_name: str,
        time_col: str,
        dept_expr: str,
        dim_filters: dict[str, str],
        count_id: str,
        columns: set[str],
        data_source: str,
        levels: list[str],
        dept_prefix_len: int = 6,
        filter_duplicate: bool = False,
        exclude_non_police: bool = False,
        exclude_traffic: bool = False,
        filter_self_received: bool = False,
        exclude_self_received: bool = False,
        extra_where: str = '',
    ) -> str:
        """类别/类型/细类任意组合 GROUP BY，返回各组合当期数量。

        levels 取值：category / type / subtype（顺序即表头顺序）。
        """
        normalized: list[str] = []
        for raw in levels or []:
            level = str(raw or '').strip().lower()
            if level in {'category', 'type', 'subtype'} and level not in normalized:
                normalized.append(level)
        if not normalized:
            raise ServiceException(message='请至少选择类别、类型或细类之一')

        dim_specs: list[tuple[str, str, str, str | None]] = []
        for level in normalized:
            if level == 'category':
                code_expr, name_expr = cls.resolve_category_group_exprs(columns, data_source)
                dim_specs.append(('category_code', 'category_name', code_expr, name_expr))
            elif level == 'type':
                code_expr, name_expr = cls.resolve_type_group_exprs(columns, data_source)
                dim_specs.append(('type_code', 'type_name', code_expr, name_expr))
            else:
                code_expr, name_expr = cls.resolve_subtype_group_exprs(columns, data_source)
                dim_specs.append(('subtype_code', 'subtype_name', code_expr, name_expr))

        dim_where = _dim_where(dim_filters)
        dept_where = _dept_where(dept_expr, dept_prefix_len)
        extra = _optional_filter_where(
            columns,
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            table_name=table_name,
            time_col=time_col,
            extra_where=extra_where,
        )

        select_parts: list[str] = []
        group_parts: list[str] = []
        not_empty_parts: list[str] = []
        for code_alias, name_alias, code_expr, name_expr in dim_specs:
            code_sql = f'TRIM(CAST({code_expr} AS CHAR))'
            name_sql = (
                f'TRIM(CAST({name_expr} AS CHAR))' if name_expr else code_sql
            )
            select_parts.append(f'{code_sql} AS {code_alias}')
            select_parts.append(f'MAX({name_sql}) AS {name_alias}')
            group_parts.append(code_sql)
            not_empty_parts.append(
                f"({code_expr} IS NOT NULL AND TRIM(CAST({code_expr} AS CHAR)) <> '')"
            )

        if count_id == '*':
            count_expr = 'COUNT(*)'
        else:
            count_expr = f'COUNT(DISTINCT {count_id})'

        not_empty = ' AND '.join(not_empty_parts)
        return f"""SELECT
  {', '.join(select_parts)},
  {count_expr} AS cur_total
FROM {table_name}
WHERE {time_col} >= :date_start
  AND {time_col} < {DATE_END_EXCLUSIVE_EXPR}
  {dept_where}
  {dim_where}{extra}
  AND {not_empty}
GROUP BY {', '.join(group_parts)}
HAVING cur_total > 0
ORDER BY cur_total DESC, {', '.join(group_parts)}""".strip()

    @classmethod
    def build_category_share_sql(
        cls,
        *,
        table_name: str,
        time_col: str,
        dept_expr: str,
        dim_filters: dict[str, str],
        count_id: str,
        columns: set[str],
        data_source: str,
        dept_prefix_len: int = 6,
        filter_duplicate: bool = False,
        exclude_non_police: bool = False,
        exclude_traffic: bool = False,
        filter_self_received: bool = False,
        exclude_self_received: bool = False,
        extra_where: str = '',
        dept_code: str | None = None,
        dim_values: dict[str, str] | None = None,
        date_end: str | None = None,
    ) -> str:
        """按类别代码分组：当期量、同比、占范围内全部类别比重。"""
        code_expr, name_expr = cls.resolve_category_group_exprs(columns, data_source)
        return cls._build_dim_share_sql(
            table_name=table_name,
            time_col=time_col,
            dept_expr=dept_expr,
            dept_prefix_len=dept_prefix_len,
            dim_filters=dim_filters,
            count_id=count_id,
            columns=columns,
            code_expr=code_expr,
            name_expr=name_expr,
            code_alias='category_code',
            name_alias='category_name',
            stats_alias='category_stats',
            scope_total_alias='scope_total',
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            extra_where=extra_where,
            dept_code=dept_code,
            dim_values=dim_values,
            date_end=date_end,
        )

    @classmethod
    def build_type_share_sql(
        cls,
        *,
        table_name: str,
        time_col: str,
        dept_expr: str,
        dim_filters: dict[str, str],
        count_id: str,
        columns: set[str],
        data_source: str,
        dept_prefix_len: int = 6,
        filter_duplicate: bool = False,
        exclude_non_police: bool = False,
        exclude_traffic: bool = False,
        filter_self_received: bool = False,
        exclude_self_received: bool = False,
        extra_where: str = '',
        dept_code: str | None = None,
        dim_values: dict[str, str] | None = None,
        date_end: str | None = None,
    ) -> str:
        """按类型代码分组：当期量、同比、占范围内全部类型比重。"""
        code_expr, name_expr = cls.resolve_type_group_exprs(columns, data_source)
        return cls._build_dim_share_sql(
            table_name=table_name,
            time_col=time_col,
            dept_expr=dept_expr,
            dept_prefix_len=dept_prefix_len,
            dim_filters=dim_filters,
            count_id=count_id,
            columns=columns,
            code_expr=code_expr,
            name_expr=name_expr,
            code_alias='type_code',
            name_alias='type_name',
            stats_alias='type_stats',
            scope_total_alias='category_total',
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            extra_where=extra_where,
            dept_code=dept_code,
            dim_values=dim_values,
            date_end=date_end,
        )

    @classmethod
    def build_subtype_share_sql(
        cls,
        *,
        table_name: str,
        time_col: str,
        dept_expr: str,
        dim_filters: dict[str, str],
        count_id: str,
        columns: set[str],
        data_source: str,
        dept_prefix_len: int = 6,
        filter_duplicate: bool = False,
        exclude_non_police: bool = False,
        exclude_traffic: bool = False,
        filter_self_received: bool = False,
        exclude_self_received: bool = False,
        extra_where: str = '',
        dept_code: str | None = None,
        dim_values: dict[str, str] | None = None,
        date_end: str | None = None,
    ) -> str:
        """按细类代码分组：当期量、同比、占范围内全部细类比重。"""
        code_expr, name_expr = cls.resolve_subtype_group_exprs(columns, data_source)
        return cls._build_dim_share_sql(
            table_name=table_name,
            time_col=time_col,
            dept_expr=dept_expr,
            dept_prefix_len=dept_prefix_len,
            dim_filters=dim_filters,
            count_id=count_id,
            columns=columns,
            code_expr=code_expr,
            name_expr=name_expr,
            code_alias='subtype_code',
            name_alias='subtype_name',
            stats_alias='subtype_stats',
            scope_total_alias='scope_total',
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            extra_where=extra_where,
            dept_code=dept_code,
            dim_values=dim_values,
            date_end=date_end,
        )

    # ------------------------------------------------------------------
    # 4) 高发社区
    # ------------------------------------------------------------------

    @classmethod
    def _community_dict_join(
        cls,
        *,
        sdsq_expr: str,
        z_alias: str = 'z',
    ) -> str:
        """关联 zd_fasqdm：先按编码等值，未命中再按名称（避免 OR+CAST 全表嵌套循环）。"""
        sdsq = f'NULLIF(TRIM({sdsq_expr}), \'\')'
        return f"""
LEFT JOIN zd_fasqdm {z_alias}_c
  ON ({z_alias}_c.scbz IS NULL OR {z_alias}_c.scbz = 0)
 AND CAST({z_alias}_c.fasqdm AS CHAR) = {sdsq}
LEFT JOIN zd_fasqdm {z_alias}_n
  ON {z_alias}_c.fasqdm IS NULL
 AND ({z_alias}_n.scbz IS NULL OR {z_alias}_n.scbz = 0)
 AND {z_alias}_n.fasqmc = {sdsq}""".rstrip()

    @classmethod
    def _community_dict_select(cls, z_alias: str = 'z') -> tuple[str, str, str]:
        """返回 (fasqdm表达式, fasqmc表达式, 命中条件)。"""
        code = f'COALESCE({z_alias}_c.fasqdm, {z_alias}_n.fasqdm)'
        name = f'COALESCE({z_alias}_c.fasqmc, {z_alias}_n.fasqmc)'
        gx = f'COALESCE({z_alias}_c.gxdwdm, {z_alias}_n.gxdwdm)'
        return code, name, gx

    @classmethod
    def build_jjd_jjdbh_exists(
        cls,
        *,
        fkd_alias: str = 'a',
        time_start_expr: str,
        time_end_expr: str,
        jjd_table: str = 'jjd_jjd',
    ) -> str:
        """接警口径社区：用 jjdbh 关联 jjd，时间/部门/类别类型细类按接警单过滤。

        绑定：:dept_code :bjlb :bjlx :bjxl（空串跳过维度）。
        """
        return f"""
    AND EXISTS (
      SELECT 1
      FROM {jjd_table} j
      WHERE j.jjdbh = {fkd_alias}.jjdbh
        AND NULLIF(TRIM(CAST({fkd_alias}.jjdbh AS CHAR)), '') IS NOT NULL
        AND j.bjsj >= {time_start_expr}
        AND j.bjsj < {time_end_expr}
        AND (
          :dept_code = ''
          OR IF(
            RIGHT(:dept_code, 6) = '000000',
            LEFT(j.gxdwdm, 6) = LEFT(:dept_code, 6),
            j.gxdwdm = :dept_code
          )
        )
        AND j.gxdwdm IS NOT NULL
        AND (:bjlb = '' OR FIND_IN_SET(CAST(j.bjlbdm AS CHAR), :bjlb) > 0)
        AND (:bjlx = '' OR FIND_IN_SET(CAST(j.bjlxdm AS CHAR), :bjlx) > 0)
        AND (:bjxl = '' OR FIND_IN_SET(CAST(j.bjxldm AS CHAR), :bjxl) > 0)
    )"""

    @classmethod
    def build_hot_community_sql(
        cls,
        *,
        table_name: str,
        time_col: str,
        dept_expr: str,
        dim_filters: dict[str, str],
        count_id: str,
        columns: set[str],
        data_source: str,
        top_n: int | None = None,
        filter_duplicate: bool = False,
        exclude_non_police: bool = False,
        exclude_traffic: bool = False,
        filter_self_received: bool = False,
        exclude_self_received: bool = False,
        extra_where: str = '',
        jjd_bridge: bool = False,
    ) -> str | None:
        """高发社区：查反馈单 sdsq + zd_fasqdm，文案形如 五爱社区：30起。

        jjd_bridge=True：按接警单 jjdbh 关联过滤（维度用 bj*），社区字段仍取 fkd.sdsq。
        聚合使用 COUNT(DISTINCT case_id) 去重（zjjdbh 优先，否则 jjdbh/cjdbh）。
        """
        if 'sdsq' not in columns:
            return None
        if jjd_bridge and 'jjdbh' not in columns:
            return None

        aliased_time = cls.qualify_expr(time_col, 'a')
        aliased_dept = cls.qualify_expr(dept_expr, 'a')
        # 接警桥接时维度在 jjd 上，勿再按反馈 aj* 过滤
        dim_where = '' if jjd_bridge else _dim_where(dim_filters, qualify_alias='a')
        bridge_where = (
            cls.build_jjd_jjdbh_exists(
                fkd_alias='a',
                time_start_expr='p.cur_start',
                time_end_expr='p.cur_end',
            )
            if jjd_bridge
            else ''
        )
        extra = _optional_filter_where(
            columns,
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            table_name=table_name,
            qualify_alias='a',
            time_col=time_col,
            extra_where=extra_where,
        )

        a_dept_where = f"""
    AND (
      :dept_code = ''
      OR IF(
        RIGHT(:dept_code, 6) = '000000',
        LEFT({aliased_dept}, 6) = LEFT(:dept_code, 6),
        {aliased_dept} = :dept_code
      )
    )
    AND {aliased_dept} IS NOT NULL"""

        fasqdm_expr, fasqmc_expr, gx_expr = cls._community_dict_select('z')
        z_dept_where = f"""
    AND (
      :dept_code = ''
      OR IF(
        RIGHT(:dept_code, 6) = '000000',
        LEFT({gx_expr}, 6) = LEFT(:dept_code, 6),
        {gx_expr} = :dept_code
      )
    )
    AND {gx_expr} IS NOT NULL"""

        # 社区统计必须去重：无单号列时退回 COUNT(*)（极少见）
        if count_id == '*':
            count_expr = 'COUNT(*)'
            filtered_id = '1 AS case_id'
        else:
            case_id_expr = cls.resolve_case_id_expr(columns, data_source, alias='a')
            count_expr = 'COUNT(DISTINCT case_id)'
            filtered_id = f'{case_id_expr} AS case_id'

        # 接警桥接：时间/部门在 jjd EXISTS 内，fkd 只取有社区的关联行
        if jjd_bridge:
            filtered_where = f"""
  WHERE NULLIF(TRIM(a.sdsq), '') IS NOT NULL
    {bridge_where}
    {extra}"""
        else:
            filtered_where = f"""
  WHERE {aliased_time} >= p.cur_start
    AND {aliased_time} < p.cur_end
    AND NULLIF(TRIM(a.sdsq), '') IS NOT NULL
    {a_dept_where}
    {dim_where}{extra}"""

        limit_n = int(top_n) if top_n and top_n > 0 else 500
        return f"""WITH params AS (
  SELECT
    CAST(:date_start AS DATETIME) AS cur_start,
    CASE
      WHEN CHAR_LENGTH(:date_end) <= 10 THEN DATE_ADD(:date_end, INTERVAL 1 DAY)
      ELSE DATE_ADD(:date_end, INTERVAL 1 SECOND)
    END AS cur_end
),
filtered AS (
  SELECT
    TRIM(a.sdsq) AS sdsq,
    {filtered_id}
  FROM {table_name} a
  CROSS JOIN params p
  {filtered_where}
),
base AS (
  SELECT
    {fasqdm_expr} AS fasqdm,
    {fasqmc_expr} AS fasqmc,
    a.case_id AS case_id
  FROM filtered a
  {cls._community_dict_join(sdsq_expr='a.sdsq', z_alias='z')}
  WHERE {fasqdm_expr} IS NOT NULL
    {z_dept_where}
)
SELECT
  fasqdm,
  fasqmc,
  {count_expr} AS total
FROM base
GROUP BY fasqdm, fasqmc
HAVING {count_expr} > 0
ORDER BY total DESC, fasqmc ASC
LIMIT {limit_n}""".strip()

    @classmethod
    def build_hot_period_sql(
        cls,
        *,
        table_name: str,
        time_col: str,
        dept_expr: str,
        dept_prefix_len: int,
        dim_filters: dict[str, str],
        count_id: str,
        columns: set[str],
        hour_span: int = 1,
        top_n: int | None = None,
        filter_duplicate: bool = False,
        exclude_non_police: bool = False,
        exclude_traffic: bool = False,
        filter_self_received: bool = False,
        exclude_self_received: bool = False,
        extra_where: str = '',
    ) -> str:
        """按 N 小时分桶统计高发时段。

        返回列：slot_start（0/1/2…）, slot_end, total
        """
        span = max(1, min(int(hour_span or 2), 12))
        dim_where = _dim_where(dim_filters)
        dept_where = _dept_where(dept_expr, dept_prefix_len)
        extra = _optional_filter_where(
            columns,
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            table_name=table_name,
            time_col=time_col,
            extra_where=extra_where,
        )
        if count_id == '*':
            count_expr = 'COUNT(*)'
        else:
            count_expr = f'COUNT(DISTINCT {count_id})'
        slot_expr = f'FLOOR(HOUR({time_col}) / {span}) * {span}'
        limit_n = int(top_n) if top_n and top_n > 0 else 500
        return f"""WITH params AS (
  SELECT
    CAST(:date_start AS DATETIME) AS cur_start,
    CASE
      WHEN CHAR_LENGTH(:date_end) <= 10 THEN DATE_ADD(:date_end, INTERVAL 1 DAY)
      ELSE DATE_ADD(:date_end, INTERVAL 1 SECOND)
    END AS cur_end
),
slots AS (
  SELECT
    {slot_expr} AS slot_start,
    {count_expr} AS total
  FROM {table_name}
  CROSS JOIN params p
  WHERE {time_col} >= p.cur_start
    AND {time_col} < p.cur_end
    {dept_where}
    {dim_where}{extra}
    AND {time_col} IS NOT NULL
  GROUP BY {slot_expr}
)
SELECT
  slot_start,
  LEAST(slot_start + {span}, 24) AS slot_end,
  total
FROM slots
WHERE total > 0
ORDER BY total DESC, slot_start ASC
LIMIT {limit_n}""".strip()

    @classmethod
    def build_community_yoy_sql(
        cls,
        *,
        table_name: str,
        time_col: str,
        dept_expr: str,
        dim_filters: dict[str, str],
        count_id: str,
        columns: set[str],
        data_source: str,
        filter_duplicate: bool = False,
        exclude_non_police: bool = False,
        exclude_traffic: bool = False,
        filter_self_received: bool = False,
        exclude_self_received: bool = False,
        extra_where: str = '',
        jjd_bridge: bool = False,
    ) -> str | None:
        """社区同比：与高发社区同一口径。

        jjd_bridge=True：按接警单 jjdbh 关联过滤；否则直接按 fkd 维度过滤。
        返回列：unit_code(fasqdm), unit_name(fasqmc), today_cnt, mom_cnt, yoy_cnt
        """
        if 'sdsq' not in columns:
            return None
        if jjd_bridge and 'jjdbh' not in columns:
            return None

        aliased_time = cls.qualify_expr(time_col, 'a')
        aliased_dept = cls.qualify_expr(dept_expr, 'a')
        dim_where = '' if jjd_bridge else _dim_where(dim_filters, qualify_alias='a')
        extra = _optional_filter_where(
            columns,
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            table_name=table_name,
            qualify_alias='a',
            time_col=time_col,
            extra_where=extra_where,
        )
        a_dept_where = f"""
    AND (
      :dept_code = ''
      OR IF(
        RIGHT(:dept_code, 6) = '000000',
        LEFT({aliased_dept}, 6) = LEFT(:dept_code, 6),
        {aliased_dept} = :dept_code
      )
    )
    AND {aliased_dept} IS NOT NULL"""

        fasqdm_expr, fasqmc_expr, gx_expr = cls._community_dict_select('z')
        z_dept_where = f"""
    AND (
      :dept_code = ''
      OR IF(
        RIGHT(:dept_code, 6) = '000000',
        LEFT({gx_expr}, 6) = LEFT(:dept_code, 6),
        {gx_expr} = :dept_code
      )
    )
    AND {gx_expr} IS NOT NULL"""

        if count_id == '*':
            filtered_id = '1 AS dedup_key'
            today_expr = "SUM(CASE WHEN period_code = 'cur' THEN 1 ELSE 0 END)"
            mom_expr = "SUM(CASE WHEN period_code = 'mom' THEN 1 ELSE 0 END)"
            yoy_expr = "SUM(CASE WHEN period_code = 'yoy' THEN 1 ELSE 0 END)"
        else:
            case_id_expr = cls.resolve_case_id_expr(columns, data_source, alias='a')
            filtered_id = f'{case_id_expr} AS dedup_key'
            today_expr = "COUNT(DISTINCT CASE WHEN period_code = 'cur' THEN dedup_key END)"
            mom_expr = "COUNT(DISTINCT CASE WHEN period_code = 'mom' THEN dedup_key END)"
            yoy_expr = "COUNT(DISTINCT CASE WHEN period_code = 'yoy' THEN dedup_key END)"

        end_excl = DATE_END_EXCLUSIVE_EXPR
        dict_join = cls._community_dict_join(sdsq_expr='a.sdsq', z_alias='z')

        def period_block(period_code: str, start_col: str, end_col: str) -> str:
            if jjd_bridge:
                bridge_where = cls.build_jjd_jjdbh_exists(
                    fkd_alias='a',
                    time_start_expr=f'p.{start_col}',
                    time_end_expr=f'p.{end_col}',
                )
                period_where = f"""
    WHERE NULLIF(TRIM(a.sdsq), '') IS NOT NULL
      {bridge_where}
      {extra}"""
            else:
                period_where = f"""
    WHERE {aliased_time} >= p.{start_col}
      AND {aliased_time} < p.{end_col}
      AND NULLIF(TRIM(a.sdsq), '') IS NOT NULL
      {a_dept_where}
      {dim_where}{extra}"""
            return f"""SELECT '{period_code}' AS period_code,
    {fasqdm_expr} AS unit_code,
    {fasqmc_expr} AS unit_name,
    a.dedup_key AS dedup_key
  FROM (
    SELECT
      TRIM(a.sdsq) AS sdsq,
      {filtered_id}
    FROM {table_name} a
    CROSS JOIN params p
    {period_where}
  ) a
  {dict_join}
  WHERE {fasqdm_expr} IS NOT NULL
    {z_dept_where}"""

        return f"""WITH params AS (
  SELECT
    CAST(:date_start AS DATETIME) AS start_date,
    {end_excl} AS end_date,
    DATE_SUB(
      CAST(:date_start AS DATETIME),
      INTERVAL TIMESTAMPDIFF(
        SECOND,
        CAST(:date_start AS DATETIME),
        {end_excl}
      ) SECOND
    ) AS prev_start_date,
    CAST(:date_start AS DATETIME) AS prev_end_date,
    DATE_SUB(CAST(:date_start AS DATETIME), INTERVAL 1 YEAR) AS last_year_start_date,
    DATE_SUB({end_excl}, INTERVAL 1 YEAR) AS last_year_end_date
),
period_rows AS (
  {period_block('cur', 'start_date', 'end_date')}
  UNION ALL
  {period_block('mom', 'prev_start_date', 'prev_end_date')}
  UNION ALL
  {period_block('yoy', 'last_year_start_date', 'last_year_end_date')}
)
SELECT
  unit_code,
  unit_name,
  {today_expr} AS today_cnt,
  {mom_expr} AS mom_cnt,
  {yoy_expr} AS yoy_cnt
FROM period_rows
GROUP BY unit_code, unit_name
HAVING {today_expr} > 0
ORDER BY today_cnt DESC, unit_name ASC""".strip()

    # ------------------------------------------------------------------
    # 5) 地区表（同比趋势 / 同比分析共用；单位过滤含市局、指挥中心）
    # ------------------------------------------------------------------

    @classmethod
    def _resolve_alarm_unit_scope(
        cls,
        *,
        columns: set[str],
        data_source: str,
        dept_prefix_len: int = 6,
        dept_col: str | None = None,
    ) -> dict[str, Any]:
        """地区表：部门列、去重键、LEFT 位数。

        dept_col 应由总量口径传入（无维 fkdwdm / 有维 txfkdwdm），避免地区与总量分叉。
        """
        is_jjd = 'jjd' in (data_source or '').lower()
        prefix_len = 6
        override = str(dept_col or '').strip()
        if is_jjd:
            resolved_dept = (
                override
                if override
                else (
                    'gxdwdm'
                    if 'gxdwdm' in columns
                    else ('jjdwdm' if 'jjdwdm' in columns else 'gxdwdm')
                )
            )
            if 'zjjdbh' in columns and 'jjdbh' in columns:
                dedup_key = "COALESCE(NULLIF(b.zjjdbh, ''), b.jjdbh)"
            elif 'jjdbh' in columns:
                dedup_key = 'b.jjdbh'
            elif 'cjdbh' in columns:
                dedup_key = 'b.cjdbh'
            else:
                dedup_key = 'b.jjdbh'
        else:
            resolved_dept = (
                override
                if override
                else (
                    'fkdwdm'
                    if 'fkdwdm' in columns
                    else ('txfkdwdm' if 'txfkdwdm' in columns else 'fkdwdm')
                )
            )
            if 'jjdbh' in columns:
                dedup_key = 'b.jjdbh'
            elif 'cjdbh' in columns:
                dedup_key = 'b.cjdbh'
            else:
                dedup_key = 'NULL'
        # jz_dept 常缺交警中队编码；回退业务表单位名称（txfkdwmc 等）
        name_fallbacks: list[str] = []
        preferred_name = {
            'txfkdwdm': 'txfkdwmc',
            'fkdwdm': 'fkdwmc',
            'jjdwdm': 'jjdwmc',
            'gxdwdm': 'gxdwmc',
        }.get(resolved_dept)
        for col in (preferred_name, 'txfkdwmc', 'fkdwmc', 'jjdwmc', 'gxdwmc'):
            if col and col in columns and col not in name_fallbacks:
                name_fallbacks.append(col)
        coalesce_parts = [
            "NULLIF(TRIM(REPLACE(COALESCE(d.short_dept_name, d.detail_dept_name), '派出所', '')), '')"
        ]
        for col in name_fallbacks:
            coalesce_parts.append(
                "NULLIF(TRIM(REPLACE(REPLACE(REPLACE("
                f"COALESCE(b.{col}, ''), '派出所', ''), '义乌', ''), '交警', '')), '')"
            )
        unit_name_expr = (
            f"COALESCE({', '.join(coalesce_parts)})"
            if len(coalesce_parts) > 1
            else coalesce_parts[0]
        )
        return {
            'is_jjd': is_jjd,
            'dept_col': resolved_dept,
            'dedup_key': dedup_key,
            'prefix_len': prefix_len,
            'unit_name_expr': unit_name_expr,
        }

    @classmethod
    def build_region_station_sql(
        cls,
        *,
        table_name: str,
        time_col: str,
        data_source: str,
        dim_filters: dict[str, str],
        columns: set[str],
        dept_col: str | None = None,
        dept_prefix_len: int = 6,
        filter_duplicate: bool = False,
        exclude_non_police: bool = False,
        exclude_traffic: bool = False,
        filter_self_received: bool = False,
        exclude_self_received: bool = False,
        extra_where: str = '',
        include_squad_brigade: bool = False,
    ) -> str:
        """地区表：只查当期量 + jz_dept 单位名 + 全市行。

        返回列：unit_code, unit_name, today_cnt, mom_cnt=0, yoy_cnt=0
        （unit_code='00' 为全市 DISTINCT 总量，勿用各所相加）。
        同比/环比由 service 另查基期后程序合并。
        include_squad_brigade=True（交通类别）时保留中队/大队，仍排除分局/市局/指挥中心。
        """
        scope = cls._resolve_alarm_unit_scope(
            columns=columns,
            data_source=data_source,
            dept_prefix_len=dept_prefix_len,
            dept_col=dept_col,
        )
        dept_col = scope['dept_col']
        dedup_key = scope['dedup_key']
        prefix_len = scope['prefix_len']
        unit_name_expr = scope['unit_name_expr']

        dim_where = _dim_where(dim_filters, qualify_alias='b')
        extra = _optional_filter_where(
            columns,
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            table_name=table_name,
            qualify_alias='b',
            time_col=time_col,
            extra_where=extra_where,
        )
        # 只查传入时间窗的当期量；同比/环比由 service 另查基期后程序合并
        end_excl = DATE_END_EXCLUSIVE_EXPR
        dept_where = f"""
      AND (
            :dept_code = ''
            OR IF(
              RIGHT(:dept_code, 6) = '000000',
              LEFT(b.{dept_col}, {prefix_len}) = LEFT(:dept_code, {prefix_len}),
              b.{dept_col} = :dept_code
            )
          )
      AND b.{dept_col} IS NOT NULL"""

        # 默认排除中队/大队；交通类别需保留（仍排除分局/市局/指挥中心）
        unit_name_exclude = [
            "AND unit_name NOT LIKE '%分局%'",
            "AND unit_name NOT LIKE '%市局%'",
            "AND unit_name NOT LIKE '%指挥中心%'",
        ]
        if not include_squad_brigade:
            unit_name_exclude = [
                "AND unit_name NOT LIKE '%中队%'",
                "AND unit_name NOT LIKE '%大队%'",
                *unit_name_exclude,
            ]
        unit_name_exclude_sql = '\n    '.join(unit_name_exclude)

        return f"""WITH period_rows AS (
  SELECT
    b.{dept_col} AS unit_code,
    {unit_name_expr} AS unit_name,
    {dedup_key} AS dedup_key
  FROM {table_name} b
  LEFT JOIN jz_dept d
    ON CAST(b.{dept_col} AS CHAR) COLLATE utf8mb4_unicode_ci
     = CAST(d.dept_code AS CHAR) COLLATE utf8mb4_unicode_ci
   AND d.del_flag = '0'
  WHERE b.{time_col} >= CAST(:date_start AS DATETIME)
    AND b.{time_col} < {end_excl}{dim_where}{extra}{dept_where}
),
station_stat AS (
  SELECT
    unit_code,
    MAX(unit_name) AS unit_name,
    COUNT(DISTINCT dedup_key) AS today_cnt,
    0 AS mom_cnt,
    0 AS yoy_cnt
  FROM period_rows
  WHERE unit_name IS NOT NULL
    AND TRIM(unit_name) <> ''
    {unit_name_exclude_sql}
  GROUP BY unit_code
),
all_stat AS (
  SELECT
    '00' AS unit_code,
    '全市' AS unit_name,
    COUNT(DISTINCT dedup_key) AS today_cnt,
    0 AS mom_cnt,
    0 AS yoy_cnt
  FROM period_rows
),
merged_stat AS (
  SELECT * FROM all_stat
  UNION ALL
  SELECT * FROM station_stat WHERE today_cnt > 0
)
SELECT
  unit_code,
  unit_name,
  today_cnt,
  mom_cnt,
  yoy_cnt
FROM merged_stat
ORDER BY CASE WHEN unit_code = '00' THEN 0 ELSE 1 END, today_cnt DESC, unit_name
LIMIT 500""".strip()

    # ------------------------------------------------------------------
    # 6) 同比分析下钻：指定派出所 × 类别/类型
    # ------------------------------------------------------------------

    @classmethod
    def build_station_dim_yoy_sql(
        cls,
        *,
        table_name: str,
        time_col: str,
        dept_expr: str,
        count_id: str,
        columns: set[str],
        data_source: str,
        level: str,
        station_param_keys: list[str],
        filter_duplicate: bool = False,
        exclude_non_police: bool = False,
        exclude_traffic: bool = False,
        filter_self_received: bool = False,
        exclude_self_received: bool = False,
        extra_where: str = '',
        date_end: str | None = None,
    ) -> str:
        """按派出所 + 类别/类型分组：只查当期量。

        同比量/同比%由 service 另查基期后程序合并。
        station_param_keys 非空时：dept IN (:k0, :k1, ...)；空则强制无结果。
        维度过滤全部跳过（拆该所下全部类别/类型）。
        """
        level_key = (level or '').strip().lower()
        if level_key == 'category':
            code_expr, name_expr = cls.resolve_category_group_exprs(columns, data_source)
            code_alias = 'dim_code'
            name_alias = 'dim_name'
        else:
            code_expr, name_expr = cls.resolve_type_group_exprs(columns, data_source)
            code_alias = 'dim_code'
            name_alias = 'dim_name'

        dim_code_sql = f'TRIM(CAST({code_expr} AS CHAR))'
        if name_expr:
            dim_name_sql = f'MAX(TRIM(CAST({name_expr} AS CHAR)))'
        else:
            dim_name_sql = f'MAX({dim_code_sql})'

        if station_param_keys:
            in_list = ', '.join(f':{key}' for key in station_param_keys)
            dept_where = f'\n    AND {dept_expr} IN ({in_list})'
        else:
            dept_where = '\n    AND 1=0'

        extra = _optional_filter_where(
            columns,
            filter_duplicate=filter_duplicate,
            exclude_non_police=exclude_non_police,
            exclude_traffic=exclude_traffic,
            filter_self_received=filter_self_received,
            exclude_self_received=exclude_self_received,
            table_name=table_name,
            time_col=time_col,
            extra_where=extra_where,
        )
        end_bound = date_end_bound_expr(date_end)
        if count_id == '*':
            total_expr = 'COUNT(*)'
        else:
            total_expr = f'COUNT(DISTINCT {count_id})'

        return f"""SELECT
  TRIM(CAST({dept_expr} AS CHAR)) AS unit_code,
  {dim_code_sql} AS {code_alias},
  {dim_name_sql} AS {name_alias},
  {total_expr} AS cur_total,
  0 AS yoy_total,
  NULL AS yoy
FROM {table_name}
WHERE {time_col} >= :date_start
  AND {time_col} < {end_bound}
  {dept_where}{extra}
  AND {dept_expr} IS NOT NULL
  AND {code_expr} IS NOT NULL
  AND TRIM(CAST({code_expr} AS CHAR)) <> ''
GROUP BY TRIM(CAST({dept_expr} AS CHAR)), {dim_code_sql}
HAVING {total_expr} > 0
ORDER BY unit_code, cur_total DESC, {code_alias}""".strip()
