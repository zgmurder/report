"""智能标签 / 研判包组合查询服务。"""

import json
from datetime import datetime
from pathlib import Path
import re
from typing import Any

from sqlalchemy import delete, inspect, select, text, update
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.orm import Session

from app.domain.atomic_metric.exceptions import ServiceException
from app.core.security import CurrentUser
from app.models.intelligence import IntelTagPackage, IntelTagTaxonomy
from app.schemas.tag import (
    IntelligenceAlarmVerifyModel,
    IntelligenceSelectedSmartTagModel,
    IntelligenceTagPackageSaveModel,
    IntelligenceTagSearchRequest,
)
from app.utils.excel_util import ExcelUtil


# 兼容旧研判包种子与文本匹配规则（目录已改为读 intel_tag_taxonomy）
SMART_TAGS: list[dict[str, str]] = [
    {'id': 'elderly', 'name': '老年人', 'category': '人员属性', 'source': '警情要素', 'description': '警情文本命中老人、老年人等表述'},
    {'id': 'minor', 'name': '未成年人', 'category': '人员属性', 'source': '警情要素', 'description': '警情文本命中未成年、学生、儿童等表述'},
    {'id': 'floating', 'name': '流动人口', 'category': '人员属性', 'source': '地址标签', 'description': '出租房、暂住、外来人员等线索'},
    {'id': 'key-control', 'name': '重点管控人员', 'category': '第三方标签', 'source': '管控库', 'description': '文本或第三方字段命中重点、管控等线索'},
    {'id': 'fraud-suspect', 'name': '疑似涉诈', 'category': '警情要素', 'source': '警情要素', 'description': '诈骗、刷单、转账、银行卡等疑似涉诈线索'},
    {'id': 'telecom-fraud', 'name': '电信诈骗', 'category': '警情要素', 'source': '案事件库', 'description': '明确电信诈骗或电信网络诈骗线索'},
    {'id': 'porn-risk', 'name': '疑似涉黄', 'category': '警情要素', 'source': '警情要素', 'description': '涉黄、卖淫嫖娼、招嫖等线索'},
    {'id': 'night', 'name': '夜间时段', 'category': '时空特征', 'source': '警情要素', 'description': '22:00至次日06:00发生'},
    {'id': 'repeat-police', 'name': '多次涉警', 'category': '风险特征', 'source': '警情要素', 'description': '同一人员关联警情数大于等于3起'},
    {'id': 'dispute', 'name': '矛盾纠纷', 'category': '警情要素', 'source': '警情要素', 'description': '纠纷、争吵、矛盾等线索'},
    {'id': 'domestic', 'name': '家庭矛盾', 'category': '警情要素', 'source': '警情要素', 'description': '家庭、夫妻、家暴等线索'},
    {'id': 'rental-house', 'name': '出租房', 'category': '时空特征', 'source': '地址标签', 'description': '地址或文本命中出租房线索'},
    {'id': 'school-zone', 'name': '校园周边', 'category': '时空特征', 'source': '地址标签', 'description': '学校、校园、幼儿园等周边线索'},
    {'id': 'repeat-alarm', 'name': '重复报警', 'category': '风险特征', 'source': '警情要素', 'description': '重复报警或同一事项反复报警'},
    {'id': 'mental-risk', 'name': '精神障碍风险', 'category': '第三方标签', 'source': '卫健协同', 'description': '精神障碍、精神病、异常行为等风险线索'},
    {'id': 'traffic-risk', 'name': '交通风险', 'category': '警情要素', 'source': '警情要素', 'description': '交通事故、酒驾、车辆等线索'},
]

TAG_BY_ID = {item['id']: item for item in SMART_TAGS}
TAG_NAME_BY_ID = {item['id']: item['name'] for item in SMART_TAGS}
PRESET_PACKAGES = [
    {
        'name': '涉黄监管研判包',
        'remark': '夜间涉黄线索排查，自动排除未成年人和老年人。',
        'tags': [
            {**TAG_BY_ID['porn-risk'], 'mode': 'include'},
            {**TAG_BY_ID['night'], 'mode': 'include'},
            {**TAG_BY_ID['minor'], 'mode': 'exclude'},
            {**TAG_BY_ID['elderly'], 'mode': 'exclude'},
        ],
    },
    {
        'name': '重点管控人员涉警研判包',
        'remark': '重点人员近期多次涉警快速筛查。',
        'tags': [
            {**TAG_BY_ID['key-control'], 'mode': 'include'},
            {**TAG_BY_ID['repeat-police'], 'mode': 'include'},
        ],
    },
]

TAXONOMY_SEED_PATH = Path(__file__).resolve().parents[1] / 'domain' / 'tag' / 'tag_taxonomy_seed.json'

# 人物基本信息中的自由提取字段，不当作可选研判标签
EXCLUDED_TAXONOMY_TAG_NAMES = {'姓名', '证件号码', '联系电话', '国籍'}

# 研判包检索本地表（原第三方接口数据源）
YWJQ_ANALYSIS_TABLE = 'ywjq_analysis'
YWJQ_ANALYSIS_COLUMNS = [
    'id',
    'cjdbh',
    'bjsj',
    'fkdwmc',
    'fkrxm',
    'ywsj_dt',
    'cjqk',
    'result',
    'manual_verified',
    'verified_by',
    'verified_at',
    'can_restore',
]
# result JSON 中非「警情标签类」的保留键
RESULT_RESERVED_KEYS = {'时间地点', '人物关系', '人物分析', '处置结果'}
_FULLTEXT_SPECIAL_RE = re.compile(r'[+\-><()~*\"@\\]+')
# id 为空时用处警单号兜底，避免列表选中态全部高亮、核对找不到行
_ALARM_ROW_KEY_SQL = "COALESCE(NULLIF(TRIM(CAST(`id` AS CHAR)), ''), NULLIF(TRIM(`cjdbh`), ''))"


class TagService:
    @classmethod
    def ensure_taxonomy_table(cls, db: Session) -> None:
        table_existed = inspect(db.get_bind()).has_table(IntelTagTaxonomy.__tablename__)
        IntelTagTaxonomy.__table__.create(db.get_bind(), checkfirst=True)
        if not table_existed:
            cls.seed_taxonomy(db)
            return
        has_row = (db.execute(select(IntelTagTaxonomy.tag_id).limit(1))).first()
        if not has_row:
            cls.seed_taxonomy(db)
        else:
            cls.cleanup_excluded_taxonomy_tags(db)

    @classmethod
    def cleanup_excluded_taxonomy_tags(cls, db: Session) -> None:
        db.execute(
            delete(IntelTagTaxonomy).where(
                IntelTagTaxonomy.sheet_name == '个人基本信息',
                IntelTagTaxonomy.category_name == '人物基本信息',
                IntelTagTaxonomy.tag_name.in_(tuple(EXCLUDED_TAXONOMY_TAG_NAMES)),
            )
        )
        db.commit()

    @classmethod
    def load_taxonomy_seed(cls) -> list[dict[str, Any]]:
        if not TAXONOMY_SEED_PATH.exists():
            return []
        try:
            data = json.loads(TAXONOMY_SEED_PATH.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        return [
            item
            for item in data
            if not (
                str(item.get('sheet_name') or '') == '个人基本信息'
                and str(item.get('category_name') or '') == '人物基本信息'
                and str(item.get('tag_name') or '') in EXCLUDED_TAXONOMY_TAG_NAMES
            )
        ]

    @classmethod
    def seed_taxonomy(cls, db: Session) -> None:
        seed = cls.load_taxonomy_seed()
        if not seed:
            return
        now = datetime.now()
        for item in seed:
            tag_code = str(item.get('tag_code') or '').strip()
            tag_name = str(item.get('tag_name') or '').strip()
            if not tag_code or not tag_name:
                continue
            db.add(
                IntelTagTaxonomy(
                    tag_code=tag_code,
                    sheet_name=str(item.get('sheet_name') or '').strip() or '未分组',
                    category_name=str(item.get('category_name') or '').strip() or str(item.get('sheet_name') or ''),
                    tag_name=tag_name,
                    extract_content=str(item.get('extract_content') or '').strip() or None,
                    description=str(item.get('description') or '').strip() or None,
                    sort_order=int(item.get('sort_order') or 0),
                    status='0',
                    create_by='system',
                    create_time=now,
                    update_by='system',
                    update_time=now,
                )
            )
        db.commit()

    @classmethod
    def ensure_package_table(cls, db: Session) -> None:
        table_existed = inspect(db.get_bind()).has_table(IntelTagPackage.__tablename__)
        IntelTagPackage.__table__.create(db.get_bind(), checkfirst=True)
        if not table_existed:
            cls.seed_preset_packages(db)

    @classmethod
    def seed_preset_packages(cls, db: Session) -> None:
        now = datetime.now()
        for item in PRESET_PACKAGES:
            db.add(
                IntelTagPackage(
                    package_name=item['name'],
                    remark=item['remark'],
                    tags_json=json.dumps(item['tags'], ensure_ascii=False),
                    preset_flag='1',
                    create_by='system',
                    create_time=now,
                    update_by='system',
                    update_time=now,
                )
            )
        db.commit()

    @classmethod
    def list_catalog(cls, db: Session, sheet: str | None = None) -> dict[str, Any]:
        cls.ensure_taxonomy_table(db)
        sheet_name = (sheet or '').strip()
        if sheet_name in ('', '全部'):
            sheet_name = ''

        categories = cls.list_taxonomy_categories(db)
        stmt = (
            select(IntelTagTaxonomy)
            .where(IntelTagTaxonomy.status == '0')
            .order_by(IntelTagTaxonomy.sort_order.asc(), IntelTagTaxonomy.tag_id.asc())
        )
        if sheet_name:
            stmt = stmt.where(IntelTagTaxonomy.sheet_name == sheet_name)
        rows = list((db.execute(stmt)).scalars().all())
        tags = [cls.taxonomy_to_smart_tag(row) for row in rows if row.tag_name]
        return {'categories': categories, 'tags': tags, 'sheet': sheet_name or '全部'}

    @classmethod
    def list_taxonomy_categories(cls, db: Session) -> list[str]:
        rows = list(
            (
                db.execute(
                    select(IntelTagTaxonomy.sheet_name)
                    .where(IntelTagTaxonomy.status == '0')
                    .distinct()
                    .order_by(IntelTagTaxonomy.sheet_name.asc())
                )
            )
            .scalars()
            .all()
        )
        categories = ['全部']
        for name in rows:
            text = str(name or '').strip()
            if text and text not in categories:
                categories.append(text)
        return categories

    @classmethod
    def taxonomy_to_smart_tag(cls, row: IntelTagTaxonomy) -> dict[str, str]:
        # 不展示「事件角色：报警人、受害人…」这类整段枚举说明
        description = cls.normalize_tag_description(row.description)
        return {
            'id': row.tag_code,
            'name': row.tag_name,
            'category': row.sheet_name or row.category_name or '未分组',
            'source': row.category_name or row.sheet_name or '',
            'description': description,
        }

    @classmethod
    def normalize_tag_description(cls, value: str | None) -> str:
        text = str(value or '').strip()
        if not text:
            return ''
        if ('：' in text or ':' in text) and ('、' in text or '，' in text):
            return ''
        if text.startswith('提取：') or text.startswith('提取:'):
            return ''
        return text

    @classmethod
    def list_packages(cls, db: Session, keyword: str | None = None) -> list[dict[str, Any]]:
        cls.ensure_package_table(db)
        stmt = select(IntelTagPackage).order_by(IntelTagPackage.preset_flag.desc(), IntelTagPackage.package_id.desc())
        if keyword:
            stmt = stmt.where(
                (IntelTagPackage.package_name.like(f'%{keyword}%')) | (IntelTagPackage.remark.like(f'%{keyword}%'))
            )
        rows = list((db.execute(stmt)).scalars().all())
        return [cls.package_to_dict(row) for row in rows]

    @classmethod
    def list_cjdbh_by_package(
        cls,
        db: Session,
        package_id: int,
        *,
        begin_time: str | None = None,
        end_time: str | None = None,
        limit: int = 20000,
    ) -> list[str]:
        """按研判包组合标签检索 ywjq_analysis，返回去重后的处警单号 cjdbh。"""
        package = cls.get_package(db, package_id)
        if not package:
            raise ServiceException(message=f'研判包不存在: {package_id}')
        tags = package.get('tags') if isinstance(package, dict) else None
        include: list[str] = []
        exclude: list[str] = []
        for tag in tags or []:
            if not isinstance(tag, dict):
                continue
            name = str(tag.get('name') or '').strip()
            if not name:
                continue
            if str(tag.get('mode') or 'include').lower() == 'exclude':
                exclude.append(name)
            else:
                include.append(name)
        if not include and not exclude:
            return []
        filters: dict[str, Any] = {}
        if begin_time:
            filters['beginTime'] = str(begin_time).strip()
        if end_time:
            filters['endTime'] = str(end_time).strip()
        where_sql, params = cls._build_ywjq_where(include, exclude, None, filters or None)
        bind = {**params, 'limit': max(1, int(limit))}

        def build_cjdbh_sql(where_clause: str) -> str:
            return f"""
                SELECT DISTINCT NULLIF(TRIM(`cjdbh`), '') AS cjdbh
                FROM `{YWJQ_ANALYSIS_TABLE}`
                WHERE {where_clause}
                  AND NULLIF(TRIM(`cjdbh`), '') IS NOT NULL
                LIMIT :limit
            """

        try:
            rows = (db.execute(text(build_cjdbh_sql(where_sql)), bind)).mappings().all()
        except Exception as exc:
            if cls._should_fallback_from_fulltext(exc) and include:
                try:
                    db.rollback()
                except Exception:
                    pass
                where_sql, params = cls._build_ywjq_where(
                    include, exclude, None, filters or None, use_fulltext=False
                )
                bind = {**params, 'limit': max(1, int(limit))}
                try:
                    rows = (db.execute(text(build_cjdbh_sql(where_sql)), bind)).mappings().all()
                except Exception as retry_exc:
                    raise ServiceException(message=f'研判包警情单号检索失败: {retry_exc}') from retry_exc
            else:
                raise ServiceException(message=f'研判包警情单号检索失败: {exc}') from exc
        result: list[str] = []
        seen: set[str] = set()
        for row in rows:
            value = str(row.get('cjdbh') or '').strip()
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    @classmethod
    def get_package(cls, db: Session, package_id: int) -> dict[str, Any] | None:
        cls.ensure_package_table(db)
        row = db.get(IntelTagPackage, package_id)
        if not row:
            return None
        return cls.package_to_dict(row)

    @classmethod
    def save_package(
        cls,
        db: Session,
        body: IntelligenceTagPackageSaveModel,
        current_user: CurrentUser,
        package_id: int | None = None,
    ) -> dict[str, Any]:
        cls.ensure_package_table(db)
        if not body.name.strip():
            raise ServiceException(message='请输入研判包名称')
        if not body.tags:
            raise ServiceException(message='研判包至少需要一个标签')
        now = datetime.now()
        user_name = current_user.username if current_user else 'admin'
        tags_json = json.dumps([tag.model_dump(by_alias=True) for tag in body.tags], ensure_ascii=False)
        if package_id:
            row = db.get(IntelTagPackage, package_id)
            if not row:
                raise ServiceException(message='研判包不存在')
            db.execute(
                update(IntelTagPackage)
                .where(IntelTagPackage.package_id == package_id)
                .values(
                    package_name=body.name.strip(),
                    remark=body.remark,
                    tags_json=tags_json,
                    update_by=user_name,
                    update_time=now,
                )
            )
            db.commit()
            return {'id': str(package_id)}
        row = IntelTagPackage(
            package_name=body.name.strip(),
            remark=body.remark,
            tags_json=tags_json,
            preset_flag='0',
            dept_id=None,
            create_by=user_name,
            create_time=now,
            update_by=user_name,
            update_time=now,
        )
        db.add(row)
        db.flush()
        new_id = row.package_id
        db.commit()
        return {'id': str(new_id)}

    @classmethod
    def delete_package(cls, db: Session, package_id: int) -> None:
        cls.ensure_package_table(db)
        db.execute(delete(IntelTagPackage).where(IntelTagPackage.package_id == package_id))
        db.commit()

    @classmethod
    def package_to_dict(cls, row: IntelTagPackage) -> dict[str, Any]:
        try:
            tags = json.loads(row.tags_json or '[]')
        except json.JSONDecodeError:
            tags = []
        return {
            'id': str(row.package_id),
            'name': row.package_name,
            'createdAt': row.create_time.strftime('%Y-%m-%d %H:%M') if row.create_time else '',
            'remark': row.remark or '',
            'tags': tags if isinstance(tags, list) else [],
            'preset': row.preset_flag == '1',
        }

    @classmethod
    def build_search_request(
        cls,
        include_tags: str | list[str] | None = None,
        exclude_tags: str | list[str] | None = None,
        sort_key: str = 'bjsj',
        sort_asc: bool = False,
        selected_ids: list[str] | None = None,
        page_num: int = 1,
        page_size: int = 10,
        cjdbh: str | None = None,
        fkdwmc: str | None = None,
        fkrxm: str | None = None,
        keyword: str | None = None,
        begin_time: str | None = None,
        end_time: str | None = None,
        manual_verified: bool | None = None,
    ) -> IntelligenceTagSearchRequest:
        include_list = cls.parse_tag_query(include_tags)
        exclude_list = cls.parse_tag_query(exclude_tags)
        tags = [
            IntelligenceSelectedSmartTagModel(
                id=name,
                name=name,
                category='',
                source='',
                mode='include',
            )
            for name in include_list
        ] + [
            IntelligenceSelectedSmartTagModel(
                id=name,
                name=name,
                category='',
                source='',
                mode='exclude',
            )
            for name in exclude_list
        ]
        key = sort_key if sort_key in ('policeStation', 'incidentCount', 'bjsj') else 'bjsj'
        return IntelligenceTagSearchRequest(
            tags=tags,
            sort_key=key,  # type: ignore[arg-type]
            sort_asc=bool(sort_asc),
            selected_ids=selected_ids,
            page_num=max(1, int(page_num or 1)),
            page_size=min(200, max(1, int(page_size or 10))),
            cjdbh=(cjdbh or '').strip() or None,
            fkdwmc=(fkdwmc or '').strip() or None,
            fkrxm=(fkrxm or '').strip() or None,
            keyword=(keyword or '').strip() or None,
            begin_time=(begin_time or '').strip() or None,
            end_time=(end_time or '').strip() or None,
            manual_verified=manual_verified,
        )

    @classmethod
    def parse_tag_query(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            raw_items = value
        else:
            text = str(value).strip()
            if not text:
                return []
            if text.startswith('['):
                try:
                    parsed = json.loads(text)
                    raw_items = parsed if isinstance(parsed, list) else [text]
                except json.JSONDecodeError:
                    raw_items = [text]
            else:
                raw_items = re.split(r'[,，、]+', text)
        result: list[str] = []
        seen: set[str] = set()
        for item in raw_items:
            name = str(item or '').strip()
            if not name or name in seen:
                continue
            seen.add(name)
            result.append(name)
        return result

    @classmethod
    def search(
        cls,
        db: Session,
        body: IntelligenceTagSearchRequest,
        current_user: CurrentUser | None = None,
    ) -> dict[str, Any]:
        from app.domain.warning.dept_data_scope import resolve_dept_data_scope, restrict_fkdwmc

        scope = resolve_dept_data_scope(current_user, db)
        include = [cls.resolve_tag_name(tag) for tag in body.tags if tag.mode == 'include']
        exclude = [cls.resolve_tag_name(tag) for tag in body.tags if tag.mode == 'exclude']
        page_num = max(1, int(body.page_num or 1))
        page_size = min(200, max(1, int(body.page_size or 10)))
        # 仅在用户主动传了反馈单位时写入 LIKE；本部门强制由 dept_scope SQL 保证
        requested_fkdwmc = (body.fkdwmc or '').strip()
        fkdwmc_filter = restrict_fkdwmc(requested_fkdwmc, scope) if requested_fkdwmc else None
        payload = cls.query_ywjq_analysis(
            db,
            include_tags=include,
            exclude_tags=exclude,
            sort_key=body.sort_key,
            sort_asc=bool(body.sort_asc),
            page_num=page_num,
            page_size=page_size,
            selected_ids=body.selected_ids,
            filters={
                'cjdbh': body.cjdbh,
                'fkdwmc': fkdwmc_filter,
                'fkrxm': body.fkrxm,
                'keyword': body.keyword,
                'beginTime': body.begin_time,
                'endTime': body.end_time,
                'manualVerified': body.manual_verified,
            },
            dept_scope=scope,
        )
        return cls.normalize_tag_search_response(payload, page_num=page_num, page_size=page_size)

    @classmethod
    def _escape_like(cls, value: str) -> str:
        return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

    @classmethod
    def _escape_fulltext_term(cls, value: str) -> str:
        cleaned = _FULLTEXT_SPECIAL_RE.sub(' ', str(value or '')).strip()
        return re.sub(r'\s+', ' ', cleaned)

    @classmethod
    def _build_fulltext_boolean_query(cls, include_tags: list[str], exclude_tags: list[str]) -> str | None:
        """单包含标签才走 FULLTEXT；多标签 BOOLEAN 分组易触发 FTS 缓存上限(188)，改走 LIKE。"""
        include_terms = [
            f'"{term}"'
            for tag in include_tags
            if (term := cls._escape_fulltext_term(tag))
        ]
        if len(include_terms) != 1:
            return None
        parts = [f'+{include_terms[0]}']
        for tag in exclude_tags:
            term = cls._escape_fulltext_term(tag)
            if term:
                parts.append(f'-"{term}"')
        return ' '.join(parts)

    @classmethod
    def _is_missing_fulltext_error(cls, exc: BaseException) -> bool:
        text_msg = str(exc or '')
        return (
            '1191' in text_msg
            or 'FULLTEXT' in text_msg.upper()
            or "Can't find FULLTEXT index" in text_msg
        )

    @classmethod
    def _is_fts_overflow_error(cls, exc: BaseException) -> bool:
        text_msg = str(exc or '')
        return (
            '(188' in text_msg
            or ' 188,' in text_msg
            or 'FTS query exceeds result cache limit' in text_msg
            or 'result cache limit' in text_msg.lower()
        )

    @classmethod
    def _should_fallback_from_fulltext(cls, exc: BaseException) -> bool:
        return cls._is_missing_fulltext_error(exc) or cls._is_fts_overflow_error(exc)

    @classmethod
    def _build_ywjq_where(
        cls,
        include_tags: list[str],
        exclude_tags: list[str],
        selected_ids: list[str] | None,
        filters: dict[str, Any] | None,
        *,
        use_fulltext: bool = True,
        dept_scope: Any = None,
    ) -> tuple[str, dict[str, Any]]:
        from app.domain.warning.dept_data_scope import ywjq_dept_scope_sql

        where: list[str] = ['1=1']
        params: dict[str, Any] = {}
        ft_query = cls._build_fulltext_boolean_query(include_tags, exclude_tags) if use_fulltext else None
        if ft_query:
            where.append('MATCH(`result`) AGAINST (:ft_query IN BOOLEAN MODE)')
            params['ft_query'] = ft_query
        else:
            # FULLTEXT 不可用或无包含标签：用 LIKE；多包含标签为或
            include_parts: list[str] = []
            for index, tag in enumerate(include_tags):
                text_value = str(tag or '').strip()
                if not text_value:
                    continue
                key = f'include_tag_{index}'
                include_parts.append(f"`result` LIKE :{key} ESCAPE '\\\\'")
                params[key] = f'%{cls._escape_like(text_value)}%'
            if include_parts:
                where.append(f'({" OR ".join(include_parts)})')
            for index, tag in enumerate(exclude_tags):
                text_value = str(tag or '').strip()
                if not text_value:
                    continue
                key = f'exclude_tag_{index}'
                where.append(f"`result` NOT LIKE :{key} ESCAPE '\\\\'")
                params[key] = f'%{cls._escape_like(text_value)}%'

        ids = [str(item).strip() for item in (selected_ids or []) if str(item).strip()]
        if ids:
            placeholders = []
            for index, item_id in enumerate(ids):
                key = f'sel_id_{index}'
                placeholders.append(f':{key}')
                params[key] = item_id
            where.append(f'{_ALARM_ROW_KEY_SQL} IN ({", ".join(placeholders)})')

        filter_map = filters or {}
        for field, key in (('cjdbh', 'cjdbh'), ('fkdwmc', 'fkdwmc'), ('fkrxm', 'fkrxm')):
            value = str(filter_map.get(key) or '').strip()
            if value:
                where.append(f"`{field}` LIKE :{key} ESCAPE '\\\\'")
                params[key] = f'%{cls._escape_like(value)}%'
        keyword = str(filter_map.get('keyword') or '').strip()
        if keyword:
            where.append("`cjqk` LIKE :keyword ESCAPE '\\\\'")
            params['keyword'] = f'%{cls._escape_like(keyword)}%'
        begin_time = str(filter_map.get('beginTime') or '').strip()
        if begin_time:
            where.append('`bjsj` >= :begin_time')
            params['begin_time'] = begin_time
        end_time = str(filter_map.get('endTime') or '').strip()
        if end_time:
            where.append('`bjsj` <= :end_time')
            params['end_time'] = end_time
        verified = filter_map.get('manualVerified')
        if verified is True or verified == 1 or str(verified).strip().lower() in ('1', 'true'):
            where.append('IFNULL(`manual_verified`, 0) = 1')
        elif verified is False or verified == 0 or str(verified).strip().lower() in ('0', 'false'):
            where.append('IFNULL(`manual_verified`, 0) = 0')

        scope_sql, scope_params = ywjq_dept_scope_sql(dept_scope) if dept_scope is not None else ('', {})
        if scope_sql:
            # scope_sql 形如 " AND (...)"，并入 where
            where.append(scope_sql.lstrip().removeprefix('AND').strip())
            params.update(scope_params)
        return ' AND '.join(where), params

    @classmethod
    def _resolve_sort_sql(cls, sort_key: str, sort_asc: bool) -> str:
        direction = 'ASC' if sort_asc else 'DESC'
        if sort_key == 'policeStation':
            return f'`fkdwmc` {direction}, `bjsj` DESC'
        if sort_key == 'incidentCount':
            # 前端文案为「标签数量」：用 result 文本长度近似排序
            return f'CHAR_LENGTH(IFNULL(`result`, \'\')) {direction}, `bjsj` DESC'
        return f'`bjsj` {direction}'

    @classmethod
    def _has_ywjq_search_scope(
        cls,
        include_tags: list[str],
        exclude_tags: list[str],
        selected_ids: list[str] | None,
        filters: dict[str, Any] | None,
    ) -> bool:
        """无标签/时间/关键词等条件时禁止全表扫描。"""
        if include_tags or exclude_tags:
            return True
        if any(str(item).strip() for item in (selected_ids or [])):
            return True
        filter_map = filters or {}
        for key in ('cjdbh', 'fkdwmc', 'fkrxm', 'keyword', 'beginTime', 'endTime'):
            if str(filter_map.get(key) or '').strip():
                return True
        return False

    @classmethod
    def query_ywjq_analysis(
        cls,
        db: Session,
        *,
        include_tags: list[str],
        exclude_tags: list[str],
        sort_key: str,
        sort_asc: bool,
        page_num: int,
        page_size: int,
        selected_ids: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        dept_scope: Any = None,
    ) -> dict[str, Any]:
        """直接查询本地 ywjq_analysis，替代原第三方标签检索接口。"""
        page_num = max(1, int(page_num or 1))
        page_size = max(1, int(page_size or 10))
        if not cls._has_ywjq_search_scope(include_tags, exclude_tags, selected_ids, filters):
            raise ServiceException(message='请至少选择时间范围、标签或其它筛选条件后再检索')
        where_sql, params = cls._build_ywjq_where(
            include_tags, exclude_tags, selected_ids, filters, dept_scope=dept_scope
        )
        order_sql = cls._resolve_sort_sql(sort_key, sort_asc)
        offset = (page_num - 1) * page_size

        def build_sqls(where_clause: str) -> tuple[str, str, dict[str, Any]]:
            list_bind = {**params, 'limit': page_size, 'offset': offset}
            count = f"""
                SELECT
                  COUNT(DISTINCT COALESCE(NULLIF(`cjdbh`, ''), `id`)) AS total,
                  COUNT(DISTINCT NULLIF(`fkdwmc`, '')) AS station_total
                FROM `{YWJQ_ANALYSIS_TABLE}`
                WHERE {where_clause}
            """
            listing = f"""
                SELECT `id`, `cjdbh`, `bjsj`, `fkdwmc`, `fkrxm`, `ywsj_dt`, `cjqk`, `result`,
                       `manual_verified`, `verified_by`, `verified_at`,
                       CASE WHEN `result_original` IS NOT NULL AND TRIM(`result_original`) <> '' THEN 1 ELSE 0 END AS `can_restore`
                FROM (
                  SELECT
                    `id`, `cjdbh`, `bjsj`, `fkdwmc`, `fkrxm`, `ywsj_dt`, `cjqk`, `result`,
                    `manual_verified`, `verified_by`, `verified_at`, `result_original`,
                    ROW_NUMBER() OVER (
                      PARTITION BY COALESCE(NULLIF(`cjdbh`, ''), `id`)
                      ORDER BY IFNULL(`ywsj_dt`, `bjsj`) DESC, `id` DESC
                    ) AS `_rn`
                  FROM `{YWJQ_ANALYSIS_TABLE}`
                  WHERE {where_clause}
                ) AS `t`
                WHERE `t`.`_rn` = 1
                ORDER BY {order_sql}
                LIMIT :limit OFFSET :offset
            """
            return count, listing, list_bind

        count_sql, list_sql, list_params = build_sqls(where_sql)
        try:
            count_row = (db.execute(text(count_sql), params)).mappings().first() or {}
            rows_result = db.execute(text(list_sql), list_params)
        except Exception as exc:
            # 内网库可能缺 FULLTEXT，或多标签 BOOLEAN 触发 FTS 缓存上限(188)：回退 LIKE
            if cls._should_fallback_from_fulltext(exc) and include_tags:
                try:
                    db.rollback()
                except Exception:
                    pass
                where_sql, params = cls._build_ywjq_where(
                    include_tags,
                    exclude_tags,
                    selected_ids,
                    filters,
                    use_fulltext=False,
                    dept_scope=dept_scope,
                )
                count_sql, list_sql, list_params = build_sqls(where_sql)
                try:
                    count_row = (db.execute(text(count_sql), params)).mappings().first() or {}
                    rows_result = db.execute(text(list_sql), list_params)
                except Exception as retry_exc:
                    raise ServiceException(message=f'本地研判数据检索失败: {retry_exc}') from retry_exc
            else:
                raise ServiceException(message=f'本地研判数据检索失败: {exc}') from exc

        total = int(count_row.get('total') or 0)
        station_total = int(count_row.get('station_total') or 0)
        rows: list[dict[str, Any]] = []
        people_names: set[str] = set()
        for raw in rows_result.mappings().all():
            item = dict(raw)
            result_raw = item.get('result')
            if result_raw is not None and not isinstance(result_raw, str):
                try:
                    result_raw = json.dumps(result_raw, ensure_ascii=False)
                except (TypeError, ValueError):
                    result_raw = str(result_raw)
            row = {
                'id': cls.resolve_alarm_row_key(item),
                'cjdbh': item.get('cjdbh'),
                'bjsj': cls.format_datetime(item.get('bjsj')),
                'fkdwmc': item.get('fkdwmc'),
                'fkrxm': item.get('fkrxm'),
                'ywsj_dt': cls.format_datetime(item.get('ywsj_dt')),
                'cjqk': item.get('cjqk'),
                'result': result_raw,
                'resultOriginal': cls._serialize_result_value(item.get('result_original')),
                'manualVerified': int(item.get('manual_verified') or 0) == 1,
                'verifiedBy': item.get('verified_by') or None,
                'verifiedAt': cls.format_datetime(item.get('verified_at')),
                'canRestore': int(item.get('can_restore') or 0) == 1,
            }
            rows.append(row)
            for person in cls.extract_people_from_result(result_raw):
                name = str(person.get('姓名') or '').strip()
                if name:
                    people_names.add(name)
        return {
            'columns': list(YWJQ_ANALYSIS_COLUMNS),
            'rows': rows,
            'total': total,
            'pageNum': page_num,
            'pageSize': page_size,
            'sql': None,
            'incidentTotal': total,
            'stationTotal': station_total,
            # 全量 JSON 人员统计过重，这里仅按当前页估算
            'peopleTotal': len(people_names),
        }

    @classmethod
    def normalize_tag_search_response(
        cls,
        payload: dict[str, Any],
        page_num: int,
        page_size: int,
    ) -> dict[str, Any]:
        columns = payload.get('columns')
        if not isinstance(columns, list) or not columns:
            columns = list(YWJQ_ANALYSIS_COLUMNS)
        rows = payload.get('rows')
        if not isinstance(rows, list):
            rows = []
        total = int(payload.get('total') or len(rows))
        stations = {
            str(item.get('fkdwmc') or '').strip()
            for item in rows
            if isinstance(item, dict) and str(item.get('fkdwmc') or '').strip()
        }
        people: set[str] = set()
        for item in rows:
            if not isinstance(item, dict):
                continue
            for person in cls.extract_people_from_result(item.get('result')):
                name = str(person.get('姓名') or '').strip()
                if name:
                    people.add(name)
        return {
            'columns': columns,
            'rows': rows,
            'total': total,
            'pageNum': int(payload.get('pageNum') or page_num),
            'pageSize': int(payload.get('pageSize') or page_size),
            'sql': payload.get('sql'),
            'incidentTotal': int(payload.get('incidentTotal') or total),
            'stationTotal': int(payload.get('stationTotal') or len(stations)),
            'peopleTotal': int(payload.get('peopleTotal') or len(people)),
        }

    @classmethod
    def export_search(
        cls,
        db: Session,
        body: IntelligenceTagSearchRequest,
        current_user: CurrentUser | None = None,
    ) -> bytes:
        export_type = str(getattr(body, 'export_type', None) or 'alarms').strip().lower()
        if export_type == 'people':
            return cls.export_people(db, body, current_user)
        return cls.export_alarms(db, body, current_user)

    @classmethod
    def _fetch_export_rows(
        cls,
        db: Session,
        body: IntelligenceTagSearchRequest,
        current_user: CurrentUser | None = None,
    ) -> list[dict[str, Any]]:
        """导出专用：查本地表，不受 search() 分页上限限制。"""
        from app.domain.warning.dept_data_scope import resolve_dept_data_scope, restrict_fkdwmc

        scope = resolve_dept_data_scope(current_user, db)
        include = [cls.resolve_tag_name(tag) for tag in body.tags if tag.mode == 'include']
        exclude = [cls.resolve_tag_name(tag) for tag in body.tags if tag.mode == 'exclude']
        requested_fkdwmc = (body.fkdwmc or '').strip()
        fkdwmc_filter = restrict_fkdwmc(requested_fkdwmc, scope) if requested_fkdwmc else None
        payload = cls.query_ywjq_analysis(
            db,
            include_tags=include,
            exclude_tags=exclude,
            sort_key=body.sort_key,
            sort_asc=bool(body.sort_asc),
            page_num=1,
            page_size=min(10000, max(1, int(body.page_size or 10000))),
            selected_ids=body.selected_ids,
            filters={
                'cjdbh': body.cjdbh,
                'fkdwmc': fkdwmc_filter,
                'fkrxm': body.fkrxm,
                'keyword': body.keyword,
                'beginTime': body.begin_time,
                'endTime': body.end_time,
                'manualVerified': body.manual_verified,
            },
            dept_scope=scope,
        )
        result = cls.normalize_tag_search_response(payload, page_num=1, page_size=10000)
        return list(result.get('rows') or [])

    @classmethod
    def _normalize_tag_list(cls, values: list[str] | None) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in values or []:
            name = str(item or '').strip()
            if not name or name in seen:
                continue
            seen.add(name)
            result.append(name)
        return result

    @classmethod
    def _extract_alarm_tags_from_result(cls, data: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        seen: set[str] = set()
        for key, value in data.items():
            if key in RESULT_RESERVED_KEYS:
                continue
            for item in cls._normalize_tag_list(
                value if isinstance(value, list) else ([str(value)] if value not in (None, '') else [])
            ):
                if item in seen:
                    continue
                seen.add(item)
                tags.append(item)
        return tags

    @classmethod
    def _apply_verify_tags_to_result(
        cls,
        raw_result: str | None,
        *,
        alarm_tags: list[str],
        dispose: list[str],
        times: list[str],
        places: list[str],
        people: list[Any] | None = None,
        relations_text: str | None = None,
    ) -> str:
        data: dict[str, Any] = {}
        if raw_result:
            try:
                parsed = json.loads(raw_result)
                if isinstance(parsed, dict):
                    data = parsed
            except (TypeError, ValueError, json.JSONDecodeError):
                data = {}

        old_people = data.get('人物分析')
        new_alarm_tags = cls._normalize_tag_list(alarm_tags)
        new_dispose = cls._normalize_tag_list(dispose)
        new_times = cls._normalize_tag_list(times)
        new_places = cls._normalize_tag_list(places)

        old_alarm_tags = cls._extract_alarm_tags_from_result(data)
        removed = set(old_alarm_tags) - set(new_alarm_tags)
        added = [tag for tag in new_alarm_tags if tag not in set(old_alarm_tags)]

        # 从原分类中剔除人工去掉的标签；空分类删除
        for key in list(data.keys()):
            if key in RESULT_RESERVED_KEYS:
                continue
            value = data.get(key)
            if not isinstance(value, list):
                if key not in RESULT_RESERVED_KEYS:
                    data.pop(key, None)
                continue
            kept = [str(item).strip() for item in value if str(item).strip() and str(item).strip() not in removed]
            if kept:
                data[key] = kept
            else:
                data.pop(key, None)

        if added:
            existing_manual = data.get('人工标签')
            manual_list = existing_manual if isinstance(existing_manual, list) else []
            merged = cls._normalize_tag_list([*[str(x) for x in manual_list], *added])
            data['人工标签'] = merged

        data['处置结果'] = new_dispose
        data['时间地点'] = {
            '发生时间段': new_times,
            '发生地址': new_places,
        }

        if people is not None:
            old_list = old_people if isinstance(old_people, list) else []
            next_people: list[dict[str, Any]] = []
            for index, person in enumerate(people):
                if hasattr(person, 'model_dump'):
                    payload = person.model_dump()
                elif isinstance(person, dict):
                    payload = person
                else:
                    continue
                base: dict[str, Any] = {}
                if index < len(old_list) and isinstance(old_list[index], dict):
                    base = dict(old_list[index])
                name = str(payload.get('name') or payload.get('姓名') or '').strip()
                id_no = str(payload.get('id_no') or payload.get('idNo') or payload.get('证件号码') or '').strip()
                phone = str(payload.get('phone') or payload.get('联系电话') or '').strip()
                nationality = str(payload.get('nationality') or payload.get('国籍') or '').strip()
                roles = cls._normalize_tag_list(payload.get('roles') or payload.get('事件角色') or [])
                tags = cls._normalize_tag_list(payload.get('tags') or payload.get('人物标签') or [])
                identities = cls._normalize_tag_list(
                    payload.get('identities') or payload.get('人物身份') or []
                )
                base['姓名'] = name
                base['证件号码'] = id_no
                base['联系电话'] = phone
                base['国籍'] = nationality
                base['事件角色'] = roles
                base['人物标签'] = tags
                base['人物身份'] = identities
                # 清理旧别名，避免前端/检索读到过期值
                for alias in ('身份证', '证件号', '电话', '手机号', '角色', '标签', '身份'):
                    base.pop(alias, None)
                next_people.append(base)
            data['人物分析'] = next_people
        elif isinstance(old_people, list):
            data['人物分析'] = old_people
        elif '人物分析' in data:
            data.pop('人物分析', None)

        if relations_text is not None:
            text = str(relations_text).strip()
            if text and text not in {'——', '—'}:
                data['人物关系'] = text
            else:
                data['人物关系'] = ''
        elif '人物关系' not in data:
            data['人物关系'] = ''

        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def _serialize_result_value(cls, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)

    @classmethod
    def _row_to_alarm_payload(
        cls,
        row: dict[str, Any],
        *,
        result_raw: str | None,
        manual_verified: bool,
        verified_by: str | None = None,
        verified_at: str | None = None,
        can_restore: bool = False,
    ) -> dict[str, Any]:
        return {
            'id': cls.resolve_alarm_row_key(row),
            'cjdbh': row.get('cjdbh'),
            'bjsj': cls.format_datetime(row.get('bjsj')),
            'fkdwmc': row.get('fkdwmc'),
            'fkrxm': row.get('fkrxm'),
            'ywsj_dt': cls.format_datetime(row.get('ywsj_dt')),
            'cjqk': row.get('cjqk'),
            'result': result_raw,
            'resultOriginal': cls._serialize_result_value(row.get('result_original')),
            'manualVerified': manual_verified,
            'verifiedBy': verified_by,
            'verifiedAt': verified_at,
            'canRestore': can_restore,
        }

    @classmethod
    def resolve_alarm_row_key(cls, row: dict[str, Any] | None) -> str:
        """列表/核对主键：优先表 id，为空则用 cjdbh（内网脏数据兜底）。"""
        if not row:
            return ''
        raw_id = row.get('id')
        if raw_id is not None and str(raw_id).strip():
            return str(raw_id).strip()
        cjdbh = row.get('cjdbh')
        if cjdbh is not None and str(cjdbh).strip():
            return str(cjdbh).strip()
        return ''

    @classmethod
    def _get_alarm_row_by_key(cls, db: Session, alarm_key: str) -> dict[str, Any] | None:
        """按 id 或 cjdbh 定位一行（id 为空时按处警单号，取最新）。"""
        key = str(alarm_key or '').strip()
        if not key:
            return None
        row = (
            db.execute(
                text(
                    f"""
                    SELECT `id`, `cjdbh`, `bjsj`, `fkdwmc`, `fkrxm`, `ywsj_dt`, `cjqk`, `result`,
                           `result_original`, `manual_verified`, `verified_by`, `verified_at`
                    FROM `{YWJQ_ANALYSIS_TABLE}`
                    WHERE {_ALARM_ROW_KEY_SQL} = :key
                    ORDER BY IFNULL(`ywsj_dt`, `bjsj`) DESC, `id` DESC
                    LIMIT 1
                    """
                ),
                {'key': key},
            )
        ).mappings().first()
        return dict(row) if row else None

    @classmethod
    def _update_alarm_by_row(
        cls,
        db: Session,
        row: dict[str, Any],
        *,
        set_sql: str,
        params: dict[str, Any],
    ) -> None:
        """按实际行更新：有 id 用 id，否则用 cjdbh（避免 WHERE id=null 更新 0 行）。"""
        raw_id = row.get('id')
        if raw_id is not None and str(raw_id).strip():
            db.execute(
                text(
                    f"""
                    UPDATE `{YWJQ_ANALYSIS_TABLE}`
                    SET {set_sql}
                    WHERE `id` = :match_id
                    """
                ),
                {**params, 'match_id': str(raw_id).strip()},
            )
            return
        cjdbh = str(row.get('cjdbh') or '').strip()
        if not cjdbh:
            raise ServiceException(message='警情缺少 id/cjdbh，无法更新')
        db.execute(
            text(
                f"""
                UPDATE `{YWJQ_ANALYSIS_TABLE}`
                SET {set_sql}
                WHERE (NULLIF(TRIM(CAST(`id` AS CHAR)), '') IS NULL)
                  AND `cjdbh` = :match_cjdbh
                """
            ),
            {**params, 'match_cjdbh': cjdbh},
        )

    @classmethod
    def verify_alarm(
        cls,
        db: Session,
        body: IntelligenceAlarmVerifyModel,
        user: CurrentUser,
    ) -> dict[str, Any]:
        alarm_id = str(body.id or '').strip()
        if not alarm_id:
            raise ServiceException(message='缺少警情 ID')

        row = cls._get_alarm_row_by_key(db, alarm_id)
        if not row:
            raise ServiceException(message='警情不存在或已删除')

        current_result = cls._serialize_result_value(row.get('result'))
        original_result = cls._serialize_result_value(row.get('result_original'))
        # 首次核对前备份 AI 原始结果，后续再次核对不覆盖
        backup_result = original_result if (original_result and original_result.strip()) else current_result

        result_json = cls._apply_verify_tags_to_result(
            current_result,
            alarm_tags=body.alarm_tags,
            dispose=body.dispose,
            times=body.times,
            places=body.places,
            people=body.people,
            relations_text=body.relations_text,
        )
        verifier = ''
        if user and user.user:
            verifier = str(getattr(user, 'display_name', None) or getattr(user, 'username', None) or '').strip()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cls._update_alarm_by_row(
            db,
            row,
            set_sql="""
                `result` = :result,
                `result_original` = :result_original,
                `manual_verified` = 1,
                `verified_by` = :verified_by,
                `verified_at` = :verified_at
            """,
            params={
                'result': result_json,
                'result_original': backup_result,
                'verified_by': verifier or None,
                'verified_at': now,
            },
        )
        db.commit()
        payload_row = {
            **row,
            'result_original': backup_result,
        }
        return cls._row_to_alarm_payload(
            payload_row,
            result_raw=result_json,
            manual_verified=True,
            verified_by=verifier or None,
            verified_at=now,
            can_restore=bool(backup_result and str(backup_result).strip()),
        )

    @classmethod
    def restore_alarm(cls, db: Session, alarm_id: str) -> dict[str, Any]:
        alarm_id = str(alarm_id or '').strip()
        if not alarm_id:
            raise ServiceException(message='缺少警情 ID')

        row = cls._get_alarm_row_by_key(db, alarm_id)
        if not row:
            raise ServiceException(message='警情不存在或已删除')

        original_result = cls._serialize_result_value(row.get('result_original'))
        if not original_result or not original_result.strip():
            raise ServiceException(message='没有可恢复的AI原始结果（需先完成一次核对保存才会备份）')

        cls._update_alarm_by_row(
            db,
            row,
            set_sql="""
                `result` = :result,
                `manual_verified` = 0,
                `verified_by` = NULL,
                `verified_at` = NULL
            """,
            params={'result': original_result},
        )
        db.commit()
        return cls._row_to_alarm_payload(
            row,
            result_raw=original_result,
            manual_verified=False,
            verified_by=None,
            verified_at=None,
            can_restore=True,
        )

    @classmethod
    def export_alarms(
        cls,
        db: Session,
        body: IntelligenceTagSearchRequest,
        current_user: CurrentUser | None = None,
    ) -> bytes:
        alarm_rows = cls._fetch_export_rows(db, body, current_user)
        export_rows = []
        for index, row in enumerate(alarm_rows, start=1):
            people = cls.extract_people_from_result(row.get('result'))
            person_names = '、'.join(str(p.get('姓名') or '') for p in people if p.get('姓名'))
            export_rows.append(
                {
                    'index': index,
                    'cjdbh': row.get('cjdbh') or '',
                    'bjsj': row.get('bjsj') or '',
                    'fkdwmc': row.get('fkdwmc') or '',
                    'fkrxm': row.get('fkrxm') or '',
                    'ywsj_dt': row.get('ywsj_dt') or '',
                    'personNames': person_names,
                    'tags': '、'.join(sorted(cls.extract_tags_from_alarm_row(row))),
                    'cjqk': row.get('cjqk') or '',
                }
            )
        return ExcelUtil.export_list2excel(
            export_rows,
            {
                'index': '序号',
                'cjdbh': '处警单号',
                'bjsj': '报警时间',
                'fkdwmc': '反馈单位',
                'fkrxm': '反馈人',
                'ywsj_dt': '业务时间',
                'personNames': '涉及人员',
                'tags': '关联标签',
                'cjqk': '处警情况',
            },
        )

    @classmethod
    def export_people(
        cls,
        db: Session,
        body: IntelligenceTagSearchRequest,
        current_user: CurrentUser | None = None,
    ) -> bytes:
        """导出涉及人员：基本信息 + 标签 + 反馈派出所等。"""
        alarm_rows = cls._fetch_export_rows(db, body, current_user)
        export_rows: list[dict[str, Any]] = []
        index = 0
        for row in alarm_rows:
            people = cls.extract_people_from_result(row.get('result'))
            alarm_tags = '、'.join(sorted(cls.extract_tags_from_alarm_row(row)))
            if not people:
                continue
            for person in people:
                if not isinstance(person, dict):
                    continue
                index += 1
                export_rows.append(
                    {
                        'index': index,
                        'name': cls._person_scalar(person, '姓名'),
                        'idNo': cls._person_scalar(person, '证件号码', '身份证', '证件号'),
                        'phone': cls._person_scalar(person, '联系电话', '电话', '手机号'),
                        'nationality': cls._person_scalar(person, '国籍'),
                        'roles': cls._person_list_join(person, '事件角色', '角色'),
                        'identities': cls._person_list_join(person, '人物身份', '身份'),
                        'personTags': cls._person_list_join(person, '人物标签', '标签'),
                        'fkdwmc': row.get('fkdwmc') or '',
                        'fkrxm': row.get('fkrxm') or '',
                        'cjdbh': row.get('cjdbh') or '',
                        'bjsj': row.get('bjsj') or '',
                        'alarmTags': alarm_tags,
                        'cjqk': row.get('cjqk') or '',
                    }
                )
        return ExcelUtil.export_list2excel(
            export_rows,
            {
                'index': '序号',
                'name': '姓名',
                'idNo': '证件号码',
                'phone': '联系电话',
                'nationality': '国籍',
                'roles': '事件角色',
                'identities': '人物身份',
                'personTags': '人物标签',
                'fkdwmc': '反馈派出所',
                'fkrxm': '反馈人',
                'cjdbh': '处警单号',
                'bjsj': '报警时间',
                'alarmTags': '关联标签',
                'cjqk': '处警情况',
            },
        )

    @classmethod
    def _person_scalar(cls, person: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = person.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                text = '、'.join(str(item).strip() for item in value if str(item).strip())
            else:
                text = str(value).strip()
            if text:
                return text
        return ''

    @classmethod
    def _person_list_join(cls, person: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = person.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                text = '、'.join(str(item).strip() for item in value if str(item).strip())
            else:
                text = str(value).strip()
            if text:
                return text
        return ''

    @classmethod
    def resolve_tag_name(cls, tag: IntelligenceSelectedSmartTagModel) -> str:
        return (tag.name or '').strip() or TAG_NAME_BY_ID.get(tag.id, tag.id)

    @classmethod
    def build_alarm_search_rows(cls, db: Session) -> list[dict[str, Any]]:
        table, columns = cls.resolve_alarm_table(db)
        if not table:
            return []
        selected_columns = cls.pick_columns(columns)
        # 尽量带上样例接口字段
        for extra in ('id', 'cjdbh', 'bjsj', 'fkdwmc', 'fkrxm', 'ywsj_dt', 'cjqk', 'result', 'fkdbh'):
            if extra in columns and extra not in selected_columns:
                selected_columns.append(extra)
        if not selected_columns:
            return []
        sql = f"SELECT {', '.join(f'`{col}`' for col in selected_columns)} FROM `{table}` LIMIT 5000"
        result = db.execute(text(sql))
        raw_rows = [dict(row._mapping) for row in result.fetchall()]
        rows: list[dict[str, Any]] = []
        for raw in raw_rows:
            mapped = cls.map_alarm_row_to_search_item(raw)
            if mapped:
                rows.append(mapped)
        return rows

    @classmethod
    def map_alarm_row_to_search_item(cls, row: dict[str, Any]) -> dict[str, Any] | None:
        def first(*keys: str) -> Any:
            for key in keys:
                value = row.get(key)
                if value is not None and str(value).strip():
                    return value
            return None

        cjdbh = first('cjdbh', 'jjdbh', 'alarm_no', 'fkdbh')
        cjqk = first('cjqk', 'alarm_content', 'remark')
        if not cjdbh and not cjqk:
            return None
        bjsj = first('bjsj', 'jqfssj', 'jqfssj_dt', 'alarm_time', 'fksj', 'fksj_dt')
        ywsj = first('ywsj_dt', 'fksj_dt', 'fksj', 'bjsj', 'alarm_time')
        result_raw = first('result')
        if result_raw is not None and not isinstance(result_raw, str):
            try:
                result_raw = json.dumps(result_raw, ensure_ascii=False)
            except (TypeError, ValueError):
                result_raw = str(result_raw)
        item_id = cls.resolve_alarm_row_key(
            {
                'id': first('id', 'fkdbh', 'alarm_id'),
                'cjdbh': cjdbh,
            }
        ) or str(cjdbh or '')
        return {
            'id': item_id,
            'cjdbh': str(cjdbh or ''),
            'bjsj': cls.format_datetime(bjsj),
            'fkdwmc': first('fkdwmc', 'txfkdwmc', 'sdpcs', 'station_name'),
            'fkrxm': first('fkrxm', 'cjrxm', 'zrmj', 'caller_name'),
            'ywsj_dt': cls.format_datetime(ywsj),
            'cjqk': str(cjqk or ''),
            'result': result_raw,
        }

    @classmethod
    def format_datetime(cls, value: Any) -> str | None:
        if value is None:
            return None
        if hasattr(value, 'strftime'):
            try:
                return value.strftime('%Y-%m-%d %H:%M:%S')
            except (TypeError, ValueError):
                return str(value)
        text = str(value).strip()
        return text or None

    @classmethod
    def extract_people_from_result(cls, result_raw: Any) -> list[dict[str, Any]]:
        data = cls.parse_result_json(result_raw)
        people = data.get('人物分析')
        return people if isinstance(people, list) else []

    @classmethod
    def extract_tags_from_alarm_row(cls, row: dict[str, Any]) -> set[str]:
        tags: set[str] = set()
        data = cls.parse_result_json(row.get('result'))
        # 时间地点
        time_place = data.get('时间地点')
        if isinstance(time_place, dict):
            for key in ('发生地址', '发生时间段'):
                values = time_place.get(key)
                if isinstance(values, list):
                    tags.update(str(v).strip() for v in values if str(v).strip())
                elif values:
                    tags.add(str(values).strip())
        # 各类标签数组
        for key, value in data.items():
            if key in ('时间地点', '人物关系', '人物分析', '处置结果'):
                continue
            if isinstance(value, list):
                tags.update(str(v).strip() for v in value if str(v).strip())
        # 处置结果
        dispose = data.get('处置结果')
        if isinstance(dispose, list):
            tags.update(str(v).strip() for v in dispose if str(v).strip())
        # 人物标签 / 身份 / 角色
        for person in cls.extract_people_from_result(row.get('result')):
            for key in ('人物标签', '人物身份', '事件角色'):
                values = person.get(key)
                if isinstance(values, list):
                    tags.update(str(v).strip() for v in values if str(v).strip())
        # 无 result 时回退启发式
        if not tags:
            normalized = {
                'content': str(row.get('cjqk') or ''),
                'time': row.get('bjsj'),
                'name': str(row.get('fkrxm') or ''),
                'phone': '',
                'id_card': '',
                'station': str(row.get('fkdwmc') or ''),
                'residence_status': '',
                'is_valid': '',
            }
            tags.update(cls.match_row_tags(normalized))
        return {tag for tag in tags if tag}

    @classmethod
    def parse_result_json(cls, result_raw: Any) -> dict[str, Any]:
        if result_raw is None:
            return {}
        if isinstance(result_raw, dict):
            return result_raw
        text = str(result_raw).strip()
        if not text:
            return {}
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    @classmethod
    def build_tagged_people(cls, db: Session) -> list[dict[str, Any]]:
        table, columns = cls.resolve_alarm_table(db)
        if not table:
            return []
        selected_columns = cls.pick_columns(columns)
        if not selected_columns:
            return []
        sql = f"SELECT {', '.join(f'`{col}`' for col in selected_columns)} FROM `{table}` LIMIT 10000"
        result = db.execute(text(sql))
        raw_rows = [dict(row._mapping) for row in result.fetchall()]
        grouped: dict[str, dict[str, Any]] = {}
        for raw in raw_rows:
            normalized = cls.normalize_alarm_row(raw)
            name = normalized['name'] or normalized['phone'] or '未知人员'
            key = f"{name}|{normalized['phone']}|{normalized['station']}"
            item = grouped.setdefault(
                key,
                {
                    'id': key,
                    'name': name,
                    'idCard': normalized['id_card'],
                    'policeStation': normalized['station'],
                    'residenceStatus': normalized['residence_status'],
                    'tags': set(),
                    'incidentCount': 0,
                },
            )
            item['incidentCount'] += 1
            item['tags'].update(cls.match_row_tags(normalized))
        rows = []
        for item in grouped.values():
            if item['incidentCount'] >= 3:
                item['tags'].add('多次涉警')
            item['tags'] = sorted(item['tags'])
            rows.append(item)
        return rows

    @classmethod
    def resolve_alarm_table(cls, db: Session) -> tuple[str | None, set[str]]:
        for table in ('fkd_fkd',):
            try:
                columns = {
                    col['name'] for col in inspect(db.get_bind()).get_columns(table)
                }
            except NoSuchTableError:
                columns = set()
            if columns:
                return table, columns
        return None, set()

    @classmethod
    def pick_columns(cls, columns: set[str]) -> list[str]:
        candidates = [
            'alarm_id', 'alarm_no', 'alarm_time', 'alarm_type', 'station_name', 'street_name', 'address',
            'alarm_content', 'caller_name', 'caller_phone', 'status', 'is_valid', 'remark',
            'fkdbh', 'cjdbh', 'jjdbh', 'fksj', 'jqfssj', 'jqfssj_dt', 'fksj_dt', 'bjsj', 'ywsj_dt', 'ajlb', 'ajlx',
            'cjqk', 'fkrxm', 'cjrxm', 'zrmj', 'sdpcs', 'sdpcsdm', 'fkdwmc', 'txfkdwmc', 'jqxz', 'xzjdmc', 'sdsq', 'sdxq',
            'fsdw', 'czyj', 'czyjdm', 'result', 'id',
        ]
        return [name for name in candidates if name in columns]

    @classmethod
    def normalize_alarm_row(cls, row: dict[str, Any]) -> dict[str, Any]:
        def first(*keys: str) -> str:
            for key in keys:
                value = row.get(key)
                if value is not None and str(value).strip():
                    return str(value).strip()
            return ''

        content_parts = [
            first('alarm_type', 'ajlb', 'ajlx'),
            first('alarm_content', 'cjqk'),
            first('address', 'jqxz'),
            first('remark', 'czyj'),
            first('street_name', 'xzjdmc', 'sdsq', 'sdxq', 'fsdw'),
        ]
        time_value = row.get('alarm_time') or row.get('jqfssj') or row.get('jqfssj_dt') or row.get('fksj') or row.get('fksj_dt')
        return {
            'name': first('caller_name', 'fkrxm', 'cjrxm', 'zrmj'),
            'phone': first('caller_phone'),
            'id_card': first('id_card', 'sfzh', 'zjhm'),
            'station': first('station_name', 'sdpcs', 'fkdwmc', 'txfkdwmc') or '未标注派出所',
            'residence_status': first('residence_status', 'czkzt') or '未知',
            'content': ' '.join(part for part in content_parts if part),
            'time': time_value,
            'is_valid': first('is_valid'),
        }

    @classmethod
    def match_row_tags(cls, row: dict[str, Any]) -> set[str]:
        text_value = row['content']
        tags: set[str] = set()
        if any(word in text_value for word in ('老人', '老年', '走失老人')):
            tags.add('老年人')
        if any(word in text_value for word in ('未成年', '学生', '儿童', '孩子', '校园')):
            tags.add('未成年人')
        if any(word in text_value for word in ('出租房', '暂住', '外来')):
            tags.add('流动人口')
        if any(word in text_value for word in ('重点', '管控')):
            tags.add('重点管控人员')
        if any(word in text_value for word in ('诈骗', '刷单', '转账', '银行卡', '涉诈')):
            tags.add('疑似涉诈')
        if any(word in text_value for word in ('电信诈骗', '电信网络诈骗')):
            tags.add('电信诈骗')
        if any(word in text_value for word in ('涉黄', '卖淫', '嫖娼', '招嫖')):
            tags.add('疑似涉黄')
        if any(word in text_value for word in ('纠纷', '争吵', '矛盾')):
            tags.add('矛盾纠纷')
        if any(word in text_value for word in ('家庭', '夫妻', '家暴')):
            tags.add('家庭矛盾')
        if '出租房' in text_value:
            tags.add('出租房')
        if any(word in text_value for word in ('学校', '校园', '幼儿园')):
            tags.add('校园周边')
        if '重复报警' in text_value:
            tags.add('重复报警')
        if any(word in text_value for word in ('精神障碍', '精神病', '异常行为')):
            tags.add('精神障碍风险')
        if any(word in text_value for word in ('交通', '事故', '酒驾', '车辆')):
            tags.add('交通风险')
        if cls.is_night(row.get('time')):
            tags.add('夜间时段')
        return tags

    @classmethod
    def is_night(cls, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, datetime):
            hour = value.hour
        else:
            text_value = str(value)
            try:
                hour = datetime.fromisoformat(text_value.replace('T', ' ')[:19]).hour
            except ValueError:
                return False
        return hour >= 22 or hour < 6
