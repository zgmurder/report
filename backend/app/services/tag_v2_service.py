"""警情打标 v2：tag_dict_v2 + jq_tag_result。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.atomic_metric.exceptions import ServiceException
from app.core.security import CurrentUser
from app.models.intelligence import JqTagResult, TagDictV2
from app.schemas.tag_v2 import IntelligenceTagV2VerifyModel
from app.domain.warning.dept_data_scope import resolve_dept_data_scope
import logging
logger = logging.getLogger(__name__)

FKD_TABLE = 'fkd_fkd'
# fkd_fkd.fkdbh=utf8mb4_0900_ai_ci，jq_tag_result.fkdbh=utf8mb4_unicode_ci
FKD_JOIN_ON = (
    f'`{FKD_TABLE}` f ON f.`fkdbh` COLLATE utf8mb4_unicode_ci = r.`fkdbh` COLLATE utf8mb4_unicode_ci'
)
TAG_RESULT_TABLE = 'jq_tag_result'
PERSON_TAG_RESULT_TABLE = 'jq_person_tag_result'
PERSON_ZJ_TAGS_TABLE = 'jq_person_zj_tags'
TAG_DICT_TABLE = 'tag_dict_v2'

PERSON_ROLE_LABELS: dict[str, str] = {
    'bjr': '报警人',
    'sxr': '涉事人',
    'shr': '受害人',
    'xyr': '嫌疑人',
    'qtr': '其他人员',
}


class TagV2Service:
    """基于四级标签字典与打标结果表的检索 / 核对。"""

    @classmethod
    def list_catalog(cls, db: Session, domain: str | None = None) -> dict[str, Any]:
        stmt = (
            select(TagDictV2)
            .where(TagDictV2.status == '0')
            .order_by(TagDictV2.domain.asc(), TagDictV2.tag_id.asc())
        )
        domain_name = str(domain or '').strip()
        if domain_name and domain_name not in ('全部', 'all'):
            stmt = stmt.where(TagDictV2.domain == domain_name)
        rows = (db.execute(stmt)).scalars().all()
        tags = [cls._dict_tag_to_item(row) for row in rows]
        domains = sorted({item['domain'] for item in tags if item.get('domain')})
        if not domains:
            domain_rows = (
                db.execute(
                    select(TagDictV2.domain)
                    .where(TagDictV2.status == '0')
                    .distinct()
                    .order_by(TagDictV2.domain.asc())
                )
            ).all()
            domains = [str(item[0]) for item in domain_rows if item and item[0]]
        data_range = cls._load_result_data_range(db)
        return {'domains': domains, 'tags': tags, 'dataRange': data_range}

    @classmethod
    def _dict_tag_to_item(cls, row: TagDictV2) -> dict[str, Any]:
        return {
            'id': row.tag_code,
            'tagCode': row.tag_code,
            'domain': row.domain or '',
            'level1': row.level1 or '',
            'level2': row.level2 or '',
            'level3': row.level3 or '',
            'level4': row.level4 or '',
            'tagPath': row.tag_path or '',
            'tagRule': row.tag_rule or '',
            'method': row.method or 'llm',
            'name': (row.tag_path or '').split('/')[-1] if row.tag_path else row.tag_code,
            'category': row.domain or '',
        }

    @classmethod
    def _load_result_data_range(cls, db: Session) -> dict[str, Any]:
        """打标结果表时间跨度（试点数据可能与报告缓存周不一致）。"""
        sql = f"""
            SELECT
              MIN(r.`bjsj`) AS min_bjsj,
              MAX(r.`bjsj`) AS max_bjsj,
              COUNT(DISTINCT r.`fkdbh`) AS alarm_count
            FROM `{TAG_RESULT_TABLE}` r
        """
        row = (db.execute(text(sql))).mappings().first() or {}
        return {
            'beginTime': cls._format_dt(row.get('min_bjsj')),
            'endTime': cls._format_dt(row.get('max_bjsj')),
            'alarmCount': int(row.get('alarm_count') or 0),
        }

    @classmethod
    def parse_csv(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [part.strip() for part in str(value).split(',') if part.strip()]

    @classmethod
    def search(
        cls,
        db: Session,
        *,
        current_user: CurrentUser,
        include_tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        domain: str | None = None,
        fkdbh: str | None = None,
        cjdbh: str | None = None,
        fkdwmc: str | None = None,
        fkdwdm: str | None = None,
        fkrxm: str | None = None,
        keyword: str | None = None,
        begin_time: str | None = None,
        end_time: str | None = None,
        has_manual: bool | None = None,
        ajlb_codes: list[str] | str | None = None,
        ajlx_codes: list[str] | str | None = None,
        ajxl_codes: list[str] | str | None = None,
        page_num: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        page_num = max(1, int(page_num or 1))
        page_size = max(1, min(200, int(page_size or 20)))
        include = cls.parse_csv(include_tags)
        exclude = cls.parse_csv(exclude_tags)
        filters: dict[str, Any] = {
            'fkdbh': str(fkdbh or '').strip(),
            'cjdbh': str(cjdbh or '').strip(),
            'fkdwmc': str(fkdwmc or '').strip(),
            'fkdwdm': str(fkdwdm or '').strip(),
            'fkrxm': str(fkrxm or '').strip(),
            'keyword': str(keyword or '').strip(),
            'beginTime': str(begin_time or '').strip(),
            'endTime': str(end_time or '').strip(),
            'domain': str(domain or '').strip(),
            'ajlbCodes': cls.parse_csv(ajlb_codes),
            'ajlxCodes': cls.parse_csv(ajlx_codes),
            'ajxlCodes': cls.parse_csv(ajxl_codes),
        }
        if not cls._has_search_scope(include, exclude, filters):
            raise ServiceException(message='请至少选择时间范围、标签或其它筛选条件后再检索')

        dept_scope = resolve_dept_data_scope(current_user, db)
        need_fkd = cls._needs_fkd_join(filters, dept_scope)
        where_sql, params = cls._build_search_where(
            include,
            exclude,
            filters,
            has_manual=has_manual,
            dept_scope=dept_scope,
            need_fkd=need_fkd,
        )
        offset = (page_num - 1) * page_size

        # 以 jq_tag_result（百级）为驱动，禁止先扫 fkd_fkd 大表
        from_sql = f'`{TAG_RESULT_TABLE}` r'
        if need_fkd:
            from_sql = f'`{TAG_RESULT_TABLE}` r INNER JOIN {FKD_JOIN_ON}'

        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM (
              SELECT r.`fkdbh`
              FROM {from_sql}
              WHERE {where_sql}
              GROUP BY r.`fkdbh`
            ) AS t
        """
        list_sql = f"""
            SELECT
              r.`fkdbh`,
              COUNT(r.`id`) AS tag_count,
              SUM(CASE WHEN r.`source` = 'manual' THEN 1 ELSE 0 END) AS manual_count,
              MAX(r.`create_time`) AS last_tag_time,
              MAX(r.`bjsj`) AS tag_bjsj,
              MAX(r.`jqqh`) AS jqqh,
              MAX(r.`cjqk`) AS result_cjqk,
              MAX(r.`czyj`) AS czyj
            FROM {from_sql}
            WHERE {where_sql}
            GROUP BY r.`fkdbh`
            ORDER BY MAX(r.`bjsj`) DESC, r.`fkdbh` DESC
            LIMIT :limit OFFSET :offset
        """
        count_row = (db.execute(text(count_sql), params)).mappings().first() or {}
        total = int(count_row.get('total') or 0)
        list_params = {**params, 'limit': page_size, 'offset': offset}
        agg_rows = (db.execute(text(list_sql), list_params)).mappings().all()
        fkdbh_list = [str(item.get('fkdbh') or '') for item in agg_rows if item.get('fkdbh')]
        fkd_map = cls._load_fkd_by_fkdbh(db, fkdbh_list)
        tags_by_fk = cls._load_tags_by_fkdbh(db, fkdbh_list)
        persons_by_fk = cls._load_persons_by_fkdbh(db, fkdbh_list)

        result_rows: list[dict[str, Any]] = []
        for item in agg_rows:
            key = str(item.get('fkdbh') or '')
            fkd = fkd_map.get(key) or {}
            tags = tags_by_fk.get(key, [])
            persons = persons_by_fk.get(key, [])
            manual_count = int(item.get('manual_count') or 0)
            zrmj = fkd.get('zrmj')
            result_rows.append(
                {
                    'id': key,
                    'fkdbh': key,
                    # 本库 fkd_fkd 无 cjdbh，接口字段保留为空
                    'cjdbh': None,
                    'jjdbh': fkd.get('jjdbh'),
                    'bjsj': cls._format_dt(fkd.get('bjsj') or item.get('tag_bjsj')),
                    'fkdwmc': fkd.get('fkdwmc'),
                    'fkdwdm': fkd.get('fkdwdm') or None,
                    'zrmj': zrmj,
                    # 本库无 fkrxm，用责任民警兜底展示
                    'fkrxm': zrmj,
                    'cjqk': fkd.get('cjqk') or item.get('result_cjqk'),
                    'jqqh': item.get('jqqh'),
                    'czyj': item.get('czyj'),
                    'tagCount': int(item.get('tag_count') or len(tags)),
                    'personCount': len(persons),
                    'manualVerified': manual_count > 0,
                    'lastTagTime': cls._format_dt(item.get('last_tag_time')),
                    'tags': tags,
                    'persons': persons,
                }
            )
        return {
            'rows': result_rows,
            'total': total,
            'pageNum': page_num,
            'pageSize': page_size,
        }

    @classmethod
    def stats(
        cls,
        db: Session,
        *,
        current_user: CurrentUser,
        level: str = '1',
        include_tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        domain: str | None = None,
        fkdbh: str | None = None,
        cjdbh: str | None = None,
        fkdwmc: str | None = None,
        fkdwdm: str | None = None,
        fkrxm: str | None = None,
        keyword: str | None = None,
        begin_time: str | None = None,
        end_time: str | None = None,
        has_manual: bool | None = None,
        ajlb_codes: list[str] | str | None = None,
        ajlx_codes: list[str] | str | None = None,
        ajxl_codes: list[str] | str | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        """按标签路径层级统计：1/2/3/4 级展示字典全量（无数据填 0），combo 为全路径。"""
        level_key = str(level or '1').strip().lower()
        if level_key in ('combo', '组合', '组合标签', 'path', 'full'):
            level_key = 'combo'
        elif level_key not in ('1', '2', '3', '4'):
            level_key = '1'

        include = cls.parse_csv(include_tags)
        exclude = cls.parse_csv(exclude_tags)
        filters: dict[str, Any] = {
            'fkdbh': str(fkdbh or '').strip(),
            'cjdbh': str(cjdbh or '').strip(),
            'fkdwmc': str(fkdwmc or '').strip(),
            'fkdwdm': str(fkdwdm or '').strip(),
            'fkrxm': str(fkrxm or '').strip(),
            'keyword': str(keyword or '').strip(),
            'beginTime': str(begin_time or '').strip(),
            'endTime': str(end_time or '').strip(),
            'domain': str(domain or '').strip(),
            'ajlbCodes': cls.parse_csv(ajlb_codes),
            'ajlxCodes': cls.parse_csv(ajlx_codes),
            'ajxlCodes': cls.parse_csv(ajxl_codes),
        }
        if not cls._has_search_scope(include, exclude, filters):
            raise ServiceException(message='请至少选择时间范围、标签或其它筛选条件后再统计')

        dept_scope = resolve_dept_data_scope(current_user, db)
        need_fkd = cls._needs_fkd_join(filters, dept_scope)
        where_sql, params = cls._build_search_where(
            include,
            exclude,
            filters,
            has_manual=has_manual,
            dept_scope=dept_scope,
            need_fkd=need_fkd,
        )
        from_sql = f'`{TAG_RESULT_TABLE}` r'
        if need_fkd:
            from_sql = f'`{TAG_RESULT_TABLE}` r INNER JOIN {FKD_JOIN_ON}'

        if level_key == 'combo':
            bucket_expr = 'r.`tag_path`'
        else:
            depth = int(level_key)
            bucket_expr = f"SUBSTRING_INDEX(r.`tag_path`, '/', {depth})"

        # 有数据的桶（不加 LIMIT，后面与字典全量合并）
        stats_sql = f"""
            SELECT
              bucket_label AS label,
              COUNT(DISTINCT fkdbh) AS alarm_count,
              COUNT(*) AS hit_count
            FROM (
              SELECT
                {bucket_expr} AS bucket_label,
                r.`fkdbh` AS fkdbh
              FROM {from_sql}
              WHERE {where_sql}
                AND r.`tag_path` IS NOT NULL
                AND r.`tag_path` <> ''
            ) AS t
            WHERE bucket_label IS NOT NULL AND bucket_label <> ''
            GROUP BY bucket_label
        """
        count_rows = (db.execute(text(stats_sql), params)).mappings().all()
        count_map = {
            str(item.get('label') or ''): (
                int(item.get('alarm_count') or 0),
                int(item.get('hit_count') or 0),
            )
            for item in count_rows
            if item.get('label')
        }

        total_sql = f"""
            SELECT COUNT(DISTINCT r.`fkdbh`) AS alarm_count
            FROM {from_sql}
            WHERE {where_sql}
        """
        total_row = (db.execute(text(total_sql), params)).mappings().first() or {}

        # 1/2/3/4：从字典拉全量前缀；combo：字典全路径；均无数据填 0
        dict_labels = cls._list_dict_stat_labels(
            db,
            level_key=level_key,
            domain=filters.get('domain') or None,
        )
        # 字典未覆盖但结果表里有的前缀也保留
        for label in count_map:
            if label not in dict_labels:
                dict_labels.append(label)

        limit = max(1, min(2000, int(limit or 500)))
        items = []
        for label in dict_labels:
            alarm_count, hit_count = count_map.get(label, (0, 0))
            items.append(
                {
                    'label': label,
                    'pathPrefix': label,
                    'alarmCount': alarm_count,
                    'hitCount': hit_count,
                }
            )
        items.sort(key=lambda row: (-int(row['alarmCount']), str(row['label'])))
        if len(items) > limit:
            items = items[:limit]

        return {
            'level': level_key,
            'totalAlarms': int(total_row.get('alarm_count') or 0),
            'items': items,
        }

    @classmethod
    def _list_dict_stat_labels(
        cls,
        db: Session,
        *,
        level_key: str,
        domain: str | None = None,
    ) -> list[str]:
        """从 tag_dict_v2 取指定层级的全量路径前缀（或 combo 全路径）。"""
        dict_params: dict[str, Any] = {}
        domain_clause = ''
        if domain and domain not in ('全部', 'all'):
            domain_clause = ' AND d.`domain` = :dict_domain'
            dict_params['dict_domain'] = domain

        if level_key == 'combo':
            label_expr = 'd.`tag_path`'
            depth_clause = ''
        else:
            depth = int(level_key)
            label_expr = f"SUBSTRING_INDEX(d.`tag_path`, '/', {depth})"
            # 至少 depth 段（斜杠数 >= depth-1）
            dict_params['min_slashes'] = depth - 1
            depth_clause = (
                " AND (CHAR_LENGTH(d.`tag_path`) - CHAR_LENGTH(REPLACE(d.`tag_path`, '/', '')))"
                ' >= :min_slashes'
            )

        sql = f"""
            SELECT DISTINCT {label_expr} AS label
            FROM `{TAG_DICT_TABLE}` d
            WHERE d.`status` = '0'
              AND d.`tag_path` IS NOT NULL
              AND d.`tag_path` <> ''
              {depth_clause}
              {domain_clause}
            ORDER BY label ASC
        """
        rows = (db.execute(text(sql), dict_params)).mappings().all()
        labels: list[str] = []
        seen: set[str] = set()
        for row in rows:
            label = str(row.get('label') or '').strip()
            if not label or label in seen:
                continue
            seen.add(label)
            labels.append(label)
        return labels

    @classmethod
    def _is_city_bureau_name(cls, name: str | None) -> bool:
        text = str(name or '').strip()
        return bool(text) and ('市局' in text or text.endswith('公安局'))

    @classmethod
    def _needs_fkd_join(cls, filters: dict[str, Any], dept_scope: Any) -> bool:
        # 结果表已有 ajlb*/fkdwdm/cjqk：类别、部门、关键词不再 join 大表
        if filters.get('cjdbh') or filters.get('fkrxm'):
            return True
        # 仅有单位名称且无代码时才被迫 join；市局名称本身不能用来过滤 fkd 大表
        fkdwmc = str(filters.get('fkdwmc') or '').strip()
        if fkdwmc and not filters.get('fkdwdm') and not cls._is_city_bureau_name(fkdwmc):
            return True
        return False

    @classmethod
    def _city_dept_prefix(cls, dept_scope: Any) -> str:
        """市局行政区划前缀（默认义乌 330782），用于 fkdwdm 前缀过滤。"""
        digits = ''.join(ch for ch in str(getattr(dept_scope, 'dept_code', '') or '') if ch.isdigit())
        if len(digits) >= 6:
            return digits[:6]
        return '330782'

    @classmethod
    def _has_search_scope(
        cls,
        include: list[str],
        exclude: list[str],
        filters: dict[str, Any],
    ) -> bool:
        if include or exclude:
            return True
        if filters.get('ajlbCodes') or filters.get('ajlxCodes') or filters.get('ajxlCodes'):
            return True
        for key in (
            'fkdbh',
            'cjdbh',
            'fkdwmc',
            'fkdwdm',
            'fkrxm',
            'keyword',
            'beginTime',
            'endTime',
            'domain',
        ):
            if filters.get(key):
                return True
        return False

    @classmethod
    def _append_in_filter(
        cls,
        clauses: list[str],
        params: dict[str, Any],
        *,
        column: str,
        codes: list[str],
        prefix: str,
    ) -> None:
        values = [str(code).strip() for code in codes if str(code or '').strip()]
        if not values:
            return
        keys: list[str] = []
        for index, code in enumerate(values):
            key = f'{prefix}_{index}'
            params[key] = code
            keys.append(f':{key}')
        clauses.append(f'{column} IN ({", ".join(keys)})')

    @classmethod
    def _append_feedback_class_filters(
        cls,
        clauses: list[str],
        params: dict[str, Any],
        filters: dict[str, Any],
    ) -> None:
        """类别/类型/细类：直接过滤 jq_tag_result 冗余字段。"""
        ajlb = filters.get('ajlbCodes') or []
        ajlx = filters.get('ajlxCodes') or []
        ajxl = filters.get('ajxlCodes') or []
        if isinstance(ajlb, str):
            ajlb = cls.parse_csv(ajlb)
        if isinstance(ajlx, str):
            ajlx = cls.parse_csv(ajlx)
        if isinstance(ajxl, str):
            ajxl = cls.parse_csv(ajxl)
        # ajlbbh 为 decimal：用 UNSIGNED 与字典编码对齐（如 20000）
        cls._append_in_filter(
            clauses,
            params,
            column='CAST(r.`ajlbbh` AS UNSIGNED)',
            codes=[str(int(float(code))) if str(code).replace('.', '', 1).isdigit() else code for code in ajlb],
            prefix='ajlb',
        )
        cls._append_in_filter(clauses, params, column='r.`ajlxbh`', codes=list(ajlx), prefix='ajlx')
        cls._append_in_filter(clauses, params, column='r.`ajxlbh`', codes=list(ajxl), prefix='ajxl')

    @classmethod
    def _append_dept_code_filters(
        cls,
        clauses: list[str],
        params: dict[str, Any],
        filters: dict[str, Any],
        dept_scope: Any = None,
    ) -> None:
        """部门：优先用结果表 fkdwdm；派出所未选手动部门时强制本部门代码。"""
        code = str(filters.get('fkdwdm') or '').strip()
        if not code and dept_scope is not None and not getattr(dept_scope, 'unrestricted', False):
            code = str(getattr(dept_scope, 'dept_code', '') or '').strip()
        if not code:
            return
        digits = ''.join(ch for ch in code if ch.isdigit()) or code
        clauses.append('(r.`fkdwdm` = :fkdwdm OR r.`fkdwdm` LIKE :fkdwdm_like)')
        params['fkdwdm'] = digits
        params['fkdwdm_like'] = f'{digits}%'

    @classmethod
    def _build_search_where(
        cls,
        include: list[str],
        exclude: list[str],
        filters: dict[str, Any],
        *,
        has_manual: bool | None,
        dept_scope: Any = None,
        need_fkd: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        clauses = ['1=1']
        params: dict[str, Any] = {}

        if filters.get('beginTime'):
            clauses.append('r.`bjsj` >= :begin_time')
            params['begin_time'] = filters['beginTime']
        if filters.get('endTime'):
            clauses.append('r.`bjsj` < :end_time')
            params['end_time'] = filters['endTime']
        if filters.get('fkdbh'):
            clauses.append('r.`fkdbh` LIKE :fkdbh')
            params['fkdbh'] = f"%{filters['fkdbh']}%"
        if filters.get('domain') and filters['domain'] not in ('全部', 'all'):
            clauses.append('r.`domain` = :domain')
            params['domain'] = filters['domain']
        if filters.get('keyword'):
            clauses.append('r.`cjqk` LIKE :keyword')
            params['keyword'] = f"%{filters['keyword']}%"

        # 市局未选手动部门时：用结果表 fkdwdm 前缀圈本市，避免 jqqh 字段稀疏/无索引导致全表慢查，
        # 也避免误带市局名称后去 join fkd 大表。
        if dept_scope is not None and getattr(dept_scope, 'unrestricted', False) and not str(
            filters.get('fkdwdm') or ''
        ).strip():
            clauses.append('r.`fkdwdm` LIKE :city_fkdwdm_like')
            params['city_fkdwdm_like'] = f"{cls._city_dept_prefix(dept_scope)}%"

        cls._append_dept_code_filters(clauses, params, filters, dept_scope=dept_scope)
        cls._append_feedback_class_filters(clauses, params, filters)

        if need_fkd:
            # 本库 fkd_fkd 无 cjdbh/fkrxm：处警单号按接警单号 jjdbh，反馈人按责任民警 zrmj
            if filters.get('cjdbh'):
                clauses.append('f.`jjdbh` LIKE :cjdbh')
                params['cjdbh'] = f"%{filters['cjdbh']}%"
            if (
                filters.get('fkdwmc')
                and not filters.get('fkdwdm')
                and not cls._is_city_bureau_name(str(filters.get('fkdwmc') or ''))
            ):
                clauses.append('f.`fkdwmc` LIKE :fkdwmc')
                params['fkdwmc'] = f"%{filters['fkdwmc']}%"
            if filters.get('fkrxm'):
                clauses.append('f.`zrmj` LIKE :fkrxm')
                params['fkrxm'] = f"%{filters['fkrxm']}%"

        for index, tag in enumerate(include):
            key = f'include_tag_{index}'
            clauses.append(
                f"""EXISTS (
                  SELECT 1 FROM `{TAG_RESULT_TABLE}` ri
                  WHERE ri.`fkdbh` = r.`fkdbh`
                    AND (ri.`tag_path` = :{key} OR ri.`tag_path` LIKE :{key}_like OR ri.`tag_code` = :{key})
                )"""
            )
            params[key] = tag
            params[f'{key}_like'] = f'{tag}/%'

        for index, tag in enumerate(exclude):
            key = f'exclude_tag_{index}'
            clauses.append(
                f"""NOT EXISTS (
                  SELECT 1 FROM `{TAG_RESULT_TABLE}` re
                  WHERE re.`fkdbh` = r.`fkdbh`
                    AND (re.`tag_path` = :{key} OR re.`tag_path` LIKE :{key}_like OR re.`tag_code` = :{key})
                )"""
            )
            params[key] = tag
            params[f'{key}_like'] = f'{tag}/%'

        if has_manual is True:
            clauses.append(
                f"""EXISTS (
                  SELECT 1 FROM `{TAG_RESULT_TABLE}` rm
                  WHERE rm.`fkdbh` = r.`fkdbh` AND rm.`source` = 'manual'
                )"""
            )
        elif has_manual is False:
            clauses.append(
                f"""NOT EXISTS (
                  SELECT 1 FROM `{TAG_RESULT_TABLE}` rm
                  WHERE rm.`fkdbh` = r.`fkdbh` AND rm.`source` = 'manual'
                )"""
            )

        return ' AND '.join(clauses), params

    @classmethod
    def _load_fkd_by_fkdbh(cls, db: Session, fkdbh_list: list[str]) -> dict[str, dict[str, Any]]:
        if not fkdbh_list:
            return {}
        placeholders = ', '.join(f':fk_{index}' for index in range(len(fkdbh_list)))
        params = {f'fk_{index}': value for index, value in enumerate(fkdbh_list)}
        sql = f"""
            SELECT
              f.`fkdbh`, f.`jjdbh`, f.`bjsj`, f.`fkdwmc`, f.`fkdwdm`,
              f.`zrmj`, f.`cjqk`
            FROM `{FKD_TABLE}` f
            WHERE f.`fkdbh` IN ({placeholders})
        """
        rows = (db.execute(text(sql), params)).mappings().all()
        return {str(row.get('fkdbh') or ''): dict(row) for row in rows}

    @classmethod
    def _load_tags_by_fkdbh(cls, db: Session, fkdbh_list: list[str]) -> dict[str, list[dict[str, Any]]]:
        if not fkdbh_list:
            return {}
        placeholders = ', '.join(f':fk_{index}' for index in range(len(fkdbh_list)))
        params = {f'fk_{index}': value for index, value in enumerate(fkdbh_list)}
        sql = f"""
            SELECT
              r.`id`, r.`fkdbh`, r.`tag_code`, r.`tag_path`, r.`domain`,
              r.`source`, r.`confidence`, r.`evidence`, r.`batch`, r.`create_time`,
              d.`tag_rule`, d.`method`
            FROM `{TAG_RESULT_TABLE}` r
            LEFT JOIN `{TAG_DICT_TABLE}` d ON d.`tag_code` = r.`tag_code`
            WHERE r.`fkdbh` IN ({placeholders})
            ORDER BY r.`domain` ASC, r.`tag_path` ASC, r.`id` ASC
        """
        rows = (db.execute(text(sql), params)).mappings().all()
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            key = str(row.get('fkdbh') or '')
            grouped.setdefault(key, []).append(cls._result_tag_to_item(row))
        return grouped

    @classmethod
    def _person_role_label(cls, role: str | None) -> str:
        key = str(role or '').strip().lower()
        return PERSON_ROLE_LABELS.get(key, str(role or '').strip() or '涉警人员')

    @classmethod
    def _person_tag_to_item(cls, row: Any) -> dict[str, Any]:
        tag_path = str(row.get('tag_path') or '').strip()
        return {
            'id': row.get('id'),
            'tagCode': row.get('tag_code'),
            'tagPath': tag_path,
            'source': row.get('source'),
            'enrichStatus': str(row.get('enrich_status') or '0'),
            'evidence': row.get('evidence'),
            'batch': row.get('batch'),
            'createTime': cls._format_dt(row.get('create_time')),
            'name': tag_path.split('/')[-1] if tag_path else '',
        }

    @classmethod
    def _normalize_id_no(cls, value: Any) -> str:
        return str(value or '').strip().upper()

    @classmethod
    def _zj_tag_to_item(cls, row: Any) -> dict[str, Any]:
        tag_name = str(row.get('tag_name') or '').strip()
        tag_code = str(row.get('tag_code') or '').strip()
        tag_path = f'治安标签/{tag_name}' if tag_name else (tag_code or '治安标签')
        return {
            'id': row.get('id'),
            'tagCode': tag_code or None,
            'tagPath': tag_path,
            'source': str(row.get('source') or 'zj-api'),
            'enrichStatus': '1',
            'evidence': None,
            'batch': row.get('batch'),
            'createTime': cls._format_dt(row.get('create_time')),
            'name': tag_name or tag_code or '治安标签',
        }

    @classmethod
    def _person_has_zj_tag(cls, tags: list[dict[str, Any]], tag: dict[str, Any]) -> bool:
        """仅按编码/路径去重，避免与 LLM 人员角色标签误判撞名。"""
        tag_code = str(tag.get('tagCode') or '').strip()
        tag_path = str(tag.get('tagPath') or '').strip()
        for existing in tags:
            existing_code = str(existing.get('tagCode') or '').strip()
            existing_path = str(existing.get('tagPath') or '').strip()
            if tag_code and existing_code == tag_code:
                return True
            if tag_path and existing_path == tag_path:
                return True
        return False

    @classmethod
    def _load_zj_tags_by_id_no(
        cls, db: Session, id_no_list: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        id_nos = sorted({cls._normalize_id_no(value) for value in id_no_list if cls._normalize_id_no(value)})
        if not id_nos:
            return {}
        placeholders = ', '.join(f':id_{index}' for index in range(len(id_nos)))
        params = {f'id_{index}': value for index, value in enumerate(id_nos)}
        sql = f"""
            SELECT `id`, `id_no`, `tag_code`, `tag_name`, `source`, `batch`, `create_time`
            FROM `{PERSON_ZJ_TAGS_TABLE}`
            WHERE UPPER(TRIM(`id_no`)) IN ({placeholders})
            ORDER BY `id_no` ASC, `tag_name` ASC, `id` ASC
        """
        try:
            rows = (db.execute(text(sql), params)).mappings().all()
        except Exception as exc:
            logger.warning(f'加载治安标签失败（{PERSON_ZJ_TAGS_TABLE}）: {exc}')
            return {}

        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            key = cls._normalize_id_no(row.get('id_no'))
            if not key:
                continue
            grouped.setdefault(key, []).append(cls._zj_tag_to_item(row))
        return grouped

    @classmethod
    def _enrich_persons_with_zj_tags(
        cls,
        persons: list[dict[str, Any]],
        zj_by_id_no: dict[str, list[dict[str, Any]]],
    ) -> None:
        for person in persons:
            id_no = cls._normalize_id_no(person.get('idNo'))
            if not id_no:
                person.setdefault('zjTags', [])
                continue
            zj_tags = zj_by_id_no.get(id_no) or []
            person['zjTags'] = list(zj_tags)
            if zj_tags:
                for zj_tag in zj_tags:
                    if not cls._person_has_zj_tag(person.get('tags') or [], zj_tag):
                        person.setdefault('tags', []).append(zj_tag)
                person['enrichStatus'] = cls._merge_person_enrich_status(person.get('enrichStatus'), '1')
            elif str(person.get('enrichStatus') or '0') == '0':
                person['enrichStatus'] = '2'

    @classmethod
    def _person_group_key(cls, row: Any) -> tuple[str, str, str]:
        role = str(row.get('person_role') or '').strip().lower()
        id_no = str(row.get('id_no') or '').strip()
        name = str(row.get('person_name') or '').strip()
        return role, id_no, name

    @classmethod
    def _merge_person_enrich_status(cls, current: str, incoming: str) -> str:
        order = {'1': 3, '0': 2, '2': 1, '9': 0}
        cur = str(current or '0')
        inc = str(incoming or '0')
        return inc if order.get(inc, 0) > order.get(cur, 0) else cur

    @classmethod
    def _load_persons_by_fkdbh(
        cls, db: Session, fkdbh_list: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        if not fkdbh_list:
            return {}
        placeholders = ', '.join(f':fk_{index}' for index in range(len(fkdbh_list)))
        params = {f'fk_{index}': value for index, value in enumerate(fkdbh_list)}
        sql = f"""
            SELECT
              `id`, `fkdbh`, `id_no`, `person_name`, `phone`, `person_role`,
              `tag_code`, `tag_path`, `source`, `enrich_status`, `evidence`,
              `batch`, `create_time`
            FROM `{PERSON_TAG_RESULT_TABLE}`
            WHERE `fkdbh` IN ({placeholders})
            ORDER BY `person_role` ASC, `person_name` ASC, `id` ASC
        """
        try:
            rows = (db.execute(text(sql), params)).mappings().all()
        except Exception:
            return {}

        grouped_by_fk: dict[str, dict[tuple[str, str, str], dict[str, Any]]] = {}
        role_order = {'bjr': 0, 'shr': 1, 'sxr': 2, 'xyr': 3, 'qtr': 9}

        for row in rows:
            fk = str(row.get('fkdbh') or '')
            if not fk:
                continue
            person_key = cls._person_group_key(row)
            bucket = grouped_by_fk.setdefault(fk, {})
            person = bucket.get(person_key)
            if not person:
                role = person_key[0]
                person = {
                    'idNo': person_key[1] or None,
                    'personName': person_key[2] or None,
                    'phone': row.get('phone'),
                    'personRole': role,
                    'personRoleLabel': cls._person_role_label(role),
                    'enrichStatus': str(row.get('enrich_status') or '0'),
                    'tags': [],
                    'zjTags': [],
                }
                bucket[person_key] = person
            person['enrichStatus'] = cls._merge_person_enrich_status(
                person.get('enrichStatus'), str(row.get('enrich_status') or '0')
            )
            tag_path = str(row.get('tag_path') or '').strip()
            if tag_path:
                person['tags'].append(cls._person_tag_to_item(row))
            elif not person.get('personName') and row.get('person_name'):
                person['personName'] = row.get('person_name')
            if not person.get('phone') and row.get('phone'):
                person['phone'] = row.get('phone')

        result: dict[str, list[dict[str, Any]]] = {}
        all_id_nos: list[str] = []
        for bucket in grouped_by_fk.values():
            for person in bucket.values():
                id_no = str(person.get('idNo') or '').strip()
                if id_no:
                    all_id_nos.append(id_no)
        zj_by_id_no = cls._load_zj_tags_by_id_no(db, all_id_nos)

        for fk, bucket in grouped_by_fk.items():
            persons = list(bucket.values())
            cls._enrich_persons_with_zj_tags(persons, zj_by_id_no)
            persons.sort(
                key=lambda item: (
                    role_order.get(str(item.get('personRole') or ''), 8),
                    str(item.get('personName') or ''),
                )
            )
            result[fk] = persons
        return result

    @classmethod
    def _result_tag_to_item(cls, row: Any) -> dict[str, Any]:
        confidence = row.get('confidence')
        if isinstance(confidence, Decimal):
            confidence = float(confidence)
        return {
            'id': row.get('id'),
            'tagCode': row.get('tag_code'),
            'tagPath': row.get('tag_path'),
            'domain': row.get('domain'),
            'source': row.get('source'),
            'confidence': confidence,
            'evidence': row.get('evidence'),
            'batch': row.get('batch'),
            'tagRule': row.get('tag_rule'),
            'method': row.get('method'),
            'createTime': cls._format_dt(row.get('create_time')),
            'name': str(row.get('tag_path') or '').split('/')[-1],
        }

    @classmethod
    def _format_dt(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        text_value = str(value).strip()
        return text_value or None

    @classmethod
    def get_alarm_detail(cls, db: Session, fkdbh: str) -> dict[str, Any]:
        key = str(fkdbh or '').strip()
        if not key:
            raise ServiceException(message='反馈单编号不能为空')
        sql = f"""
            SELECT
              f.`fkdbh`, f.`jjdbh`, f.`bjsj`, f.`fkdwmc`, f.`fkdwdm`,
              f.`zrmj`, f.`cjqk`,
              (
                SELECT r.`jqqh` FROM `{TAG_RESULT_TABLE}` r
                WHERE r.`fkdbh` COLLATE utf8mb4_unicode_ci = f.`fkdbh` COLLATE utf8mb4_unicode_ci
                ORDER BY r.`id` DESC LIMIT 1
              ) AS jqqh,
              (
                SELECT r.`czyj` FROM `{TAG_RESULT_TABLE}` r
                WHERE r.`fkdbh` COLLATE utf8mb4_unicode_ci = f.`fkdbh` COLLATE utf8mb4_unicode_ci
                ORDER BY r.`id` DESC LIMIT 1
              ) AS czyj,
              (
                SELECT r.`cjqk` FROM `{TAG_RESULT_TABLE}` r
                WHERE r.`fkdbh` COLLATE utf8mb4_unicode_ci = f.`fkdbh` COLLATE utf8mb4_unicode_ci
                ORDER BY r.`id` DESC LIMIT 1
              ) AS result_cjqk
            FROM `{FKD_TABLE}` f
            WHERE f.`fkdbh` = :fkdbh
            LIMIT 1
        """
        row = (db.execute(text(sql), {'fkdbh': key})).mappings().first()
        if not row:
            raise ServiceException(message='未找到对应反馈单')
        tags = (cls._load_tags_by_fkdbh(db, [key])).get(key, [])
        persons = (cls._load_persons_by_fkdbh(db, [key])).get(key, [])
        manual_count = sum(1 for item in tags if item.get('source') == 'manual')
        zrmj = row.get('zrmj')
        return {
            'id': key,
            'fkdbh': key,
            'cjdbh': None,
            'jjdbh': row.get('jjdbh'),
            'bjsj': cls._format_dt(row.get('bjsj')),
            'fkdwmc': row.get('fkdwmc'),
            'fkdwdm': row.get('fkdwdm'),
            'zrmj': zrmj,
            'fkrxm': zrmj,
            'cjqk': row.get('cjqk') or row.get('result_cjqk'),
            'jqqh': row.get('jqqh'),
            'jqxz': None,
            'czyj': row.get('czyj'),
            'tagCount': len(tags),
            'personCount': len(persons),
            'manualVerified': manual_count > 0,
            'tags': tags,
            'persons': persons,
        }

    @classmethod
    def verify_alarm(
        cls,
        db: Session,
        body: IntelligenceTagV2VerifyModel,
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        fkdbh = str(body.fkdbh or '').strip()
        if not fkdbh:
            raise ServiceException(message='反馈单编号不能为空')

        detail_sql = f"""
            SELECT
              f.`fkdbh`, f.`bjsj`,
              (
                SELECT r.`jqqh` FROM `{TAG_RESULT_TABLE}` r
                WHERE r.`fkdbh` COLLATE utf8mb4_unicode_ci = f.`fkdbh` COLLATE utf8mb4_unicode_ci
                ORDER BY r.`id` DESC LIMIT 1
              ) AS jqqh
            FROM `{FKD_TABLE}` f
            WHERE f.`fkdbh` = :fkdbh
            LIMIT 1
        """
        alarm = (db.execute(text(detail_sql), {'fkdbh': fkdbh})).mappings().first()
        if not alarm:
            raise ServiceException(message='未找到对应反馈单')

        requested_paths = []
        seen = set()
        for item in body.tag_paths or []:
            path = str(item or '').strip()
            if not path or path in seen:
                continue
            seen.add(path)
            requested_paths.append(path)

        dict_map: dict[str, TagDictV2] = {}
        if requested_paths:
            rows = (
                db.execute(
                    select(TagDictV2).where(
                        TagDictV2.status == '0',
                        TagDictV2.tag_path.in_(tuple(requested_paths)),
                    )
                )
            ).scalars().all()
            dict_map = {str(row.tag_path): row for row in rows}
            missing = [path for path in requested_paths if path not in dict_map]
            if missing:
                raise ServiceException(message=f'无效标签路径：{", ".join(missing[:5])}')

        existing = (
            db.execute(select(JqTagResult).where(JqTagResult.fkdbh == fkdbh))
        ).scalars().all()
        existing_by_path = {str(row.tag_path): row for row in existing}

        # 删除取消勾选的
        for path, row in existing_by_path.items():
            if path not in seen:
                db.delete(row)

        # 保留仍选中的标记为 manual（即使未改标签，也算人工已核对）；新增的记为 manual
        operator = str(
            getattr(current_user, 'username', None)
            or 'system'
        )
        batch = f'manual-{operator}'[:32]
        for path in requested_paths:
            if path in existing_by_path:
                row = existing_by_path[path]
                # 仅确认未改标签时，也要写入 manual，否则列表刷新后仍显示「未核对」
                if str(row.source or '').strip().lower() != 'manual':
                    row.source = 'manual'
                    row.confidence = Decimal('1.00')
                    row.batch = batch
                    prev = str(row.evidence or '').strip()
                    row.evidence = (f'{prev}；人工核对确认' if prev else '人工核对确认')[:1000]
                continue
            dict_row = dict_map[path]
            db.add(
                JqTagResult(
                    fkdbh=fkdbh,
                    jqqh=alarm.get('jqqh'),
                    bjsj=alarm.get('bjsj'),
                    tag_code=dict_row.tag_code,
                    tag_path=dict_row.tag_path,
                    domain=dict_row.domain,
                    source='manual',
                    confidence=Decimal('1.00'),
                    evidence='人工核对新增',
                    batch=batch,
                )
            )

        db.commit()
        return cls.get_alarm_detail(db, fkdbh)
