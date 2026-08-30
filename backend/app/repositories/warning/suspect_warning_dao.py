"""嫌疑人前科/精神障碍比对预警 DAO（jq-total-qk）。"""

from datetime import datetime

from sqlalchemy import String, bindparam, cast, func, or_, select, text, update
from sqlalchemy.orm import Session

from app.models.intelligence import IntelSuspectWarning
from app.schemas.warning import IntelligenceSuspectWarningQueryModel
from app.domain.warning.dept_data_scope import DeptDataScope, sqlalchemy_dept_match
from app.utils.page_util import PageUtil


class SuspectWarningDao:
    @classmethod
    def _dept_scope_condition(cls, query: IntelligenceSuspectWarningQueryModel):
        code = (query.dept_scope_code or '').strip()
        name = (query.dept_scope_name or '').strip()
        if not code and not name:
            return None
        return sqlalchemy_dept_match(
            IntelSuspectWarning.sdpcsdm,
            IntelSuspectWarning.sdpcs,
            DeptDataScope(unrestricted=False, dept_code=code, dept_name=name),
        )

    @classmethod
    def _org_condition(cls, org_code: str | None, org_name: str | None):
        code = (org_code or '').strip()
        name = (org_name or '').strip()
        parts = []
        if code:
            code_str = cast(IntelSuspectWarning.sdpcsdm, String)
            left6 = code[:6] if len(code) >= 6 else code
            left8 = code[:8] if len(code) >= 8 else code
            parts.append(func.left(code_str, 6) == left6)
            parts.append(func.left(code_str, 8) == left8)
        if name:
            parts.append(IntelSuspectWarning.sdpcs == name)
        if not parts:
            return None
        return or_(*parts)

    @classmethod
    def _jjd_category_exists(cls, bjlb: str | None, bjlx: str | None):
        """按接警单报警类别/类型过滤：经 jjdbh 碰撞 jjd_jjd。"""
        category = str(bjlb or '').strip()
        alarm_type = str(bjlx or '').strip()
        if not category and not alarm_type:
            return None
        clauses = [
            'EXISTS (SELECT 1 FROM jjd_jjd j',
            'WHERE (TRIM(j.jjdbh) = TRIM(`jq-total-qk`.`jjdbh`)',
            "OR j.jjdbh = RPAD(TRIM(`jq-total-qk`.`jjdbh`), 30, ' '))",
        ]
        params: dict[str, str] = {}
        if category:
            clauses.append('AND CAST(CAST(j.bjlbdm AS SIGNED) AS CHAR) = :filter_bjlb')
            params['filter_bjlb'] = category
        if alarm_type:
            clauses.append('AND CAST(CAST(j.bjlxdm AS SIGNED) AS CHAR) = :filter_bjlx')
            params['filter_bjlx'] = alarm_type
        clauses.append(')')
        return text(' '.join(clauses)).bindparams(**params)

    @classmethod
    def _build_filters(cls, query: IntelligenceSuspectWarningQueryModel):
        conditions = []
        keyword = (query.keyword or '').strip()
        if keyword:
            like = f'%{keyword}%'
            conditions.append(
                or_(
                    IntelSuspectWarning.ryxm.like(like),
                    IntelSuspectWarning.rysfz.like(like),
                    IntelSuspectWarning.sdpcs.like(like),
                    IntelSuspectWarning.tsrybq.like(like),
                    cast(IntelSuspectWarning.jjdbh, String).like(like),
                )
            )
        if (query.rysfz or '').strip():
            conditions.append(IntelSuspectWarning.rysfz.like(f'%{query.rysfz.strip()}%'))
        if (query.ryxm or '').strip():
            conditions.append(IntelSuspectWarning.ryxm.like(f'%{query.ryxm.strip()}%'))
        if (query.sdpcs or '').strip():
            conditions.append(IntelSuspectWarning.sdpcs.like(f'%{query.sdpcs.strip()}%'))
        # org_code 优先走文档机构匹配；否则兼容精确 sdpcsdm
        if (query.org_code or '').strip() or (query.org_name or '').strip():
            org_cond = cls._org_condition(query.org_code, query.org_name)
            if org_cond is not None:
                conditions.append(org_cond)
        elif (query.sdpcsdm or '').strip():
            org_cond = cls._org_condition(query.sdpcsdm, None)
            if org_cond is not None:
                conditions.append(org_cond)
        if (query.jjdbh or '').strip():
            conditions.append(cast(IntelSuspectWarning.jjdbh, String).like(f'%{query.jjdbh.strip()}%'))
        if (query.tjwdbq or '').strip():
            conditions.append(IntelSuspectWarning.tjwdbq == query.tjwdbq.strip())
        jjd_exists = cls._jjd_category_exists(query.bjlb, query.bjlx)
        if jjd_exists is not None:
            conditions.append(jjd_exists)
        if (query.handle_status or '').strip() in {'0', '1', '2'}:
            status = query.handle_status.strip()
            if status == '0':
                conditions.append(
                    (IntelSuspectWarning.handle_status == '0')
                    | (IntelSuspectWarning.handle_status == 0)
                    | (IntelSuspectWarning.handle_status.is_(None))
                )
            else:
                conditions.append(
                    (IntelSuspectWarning.handle_status == status)
                    | (IntelSuspectWarning.handle_status == int(status))
                )
        if (query.begin_rq or '').strip():
            conditions.append(IntelSuspectWarning.rq >= query.begin_rq.strip())
        if (query.end_rq or '').strip():
            conditions.append(IntelSuspectWarning.rq <= query.end_rq.strip())
        if (query.begin_bjsj or '').strip():
            conditions.append(IntelSuspectWarning.bjsj >= query.begin_bjsj.strip())
        if (query.end_bjsj or '').strip():
            conditions.append(IntelSuspectWarning.bjsj <= query.end_bjsj.strip())
        scope_cond = cls._dept_scope_condition(query)
        if scope_cond is not None:
            conditions.append(scope_cond)
        return conditions

    @classmethod
    def list_page(cls, db: Session, query: IntelligenceSuspectWarningQueryModel):
        stmt = select(IntelSuspectWarning)
        for condition in cls._build_filters(query):
            stmt = stmt.where(condition)
        stmt = stmt.order_by(IntelSuspectWarning.bjsj.desc(), IntelSuspectWarning.xlbh.desc())
        return PageUtil.paginate(db, stmt, query.page_num, query.page_size, is_page=True)

    @classmethod
    def list_summary_page(cls, db: Session, query: IntelligenceSuspectWarningQueryModel):
        """按派出所+日期聚合摘要（警情数按接警单号去重）。"""
        stmt = select(
            IntelSuspectWarning.sdpcsdm,
            IntelSuspectWarning.sdpcs,
            IntelSuspectWarning.rq,
            func.count(func.distinct(IntelSuspectWarning.jjdbh)).label('alarm_count'),
            func.min(IntelSuspectWarning.xlbh).label('xlbh'),
            func.max(IntelSuspectWarning.tjwdbq).label('tjwdbq'),
            func.max(IntelSuspectWarning.tjsj).label('tjsj'),
        )
        for condition in cls._build_filters(query):
            stmt = stmt.where(condition)
        stmt = stmt.group_by(
            IntelSuspectWarning.sdpcsdm,
            IntelSuspectWarning.sdpcs,
            IntelSuspectWarning.rq,
        ).order_by(IntelSuspectWarning.rq.desc(), func.count(func.distinct(IntelSuspectWarning.jjdbh)).desc())
        return PageUtil.paginate(db, stmt, query.page_num, query.page_size, is_page=True)

    @classmethod
    def list_city_summaries(cls, db: Session, query: IntelligenceSuspectWarningQueryModel) -> list:
        """全市维度：按日期聚合（接警单号去重）。"""
        stmt = (
            select(
                IntelSuspectWarning.rq,
                func.count(func.distinct(IntelSuspectWarning.jjdbh)).label('alarm_count'),
                func.min(IntelSuspectWarning.xlbh).label('xlbh'),
                func.max(IntelSuspectWarning.tjwdbq).label('tjwdbq'),
                func.max(IntelSuspectWarning.tjsj).label('tjsj'),
                func.min(IntelSuspectWarning.sdpcsdm).label('sdpcsdm_sample'),
            )
            .group_by(IntelSuspectWarning.rq)
            .order_by(IntelSuspectWarning.rq.desc())
        )
        for condition in cls._build_filters(query):
            stmt = stmt.where(condition)
        return (db.execute(stmt)).all()

    @classmethod
    def list_group_details(
        cls,
        db: Session,
        sdpcsdm: str | None,
        rq: str | None,
        sdpcs: str | None = None,
        page_num: int = 1,
        page_size: int = 50,
        bjlb: str | None = None,
        bjlx: str | None = None,
        dept_scope_code: str | None = None,
        dept_scope_name: str | None = None,
    ):
        stmt = select(IntelSuspectWarning)
        if sdpcsdm is not None and str(sdpcsdm).strip() != '':
            stmt = stmt.where(cast(IntelSuspectWarning.sdpcsdm, String) == str(sdpcsdm).strip())
        if (rq or '').strip():
            stmt = stmt.where(IntelSuspectWarning.rq == rq.strip())
        if (sdpcs or '').strip():
            stmt = stmt.where(IntelSuspectWarning.sdpcs == sdpcs.strip())
        jjd_exists = cls._jjd_category_exists(bjlb, bjlx)
        if jjd_exists is not None:
            stmt = stmt.where(jjd_exists)
        scope_code = (dept_scope_code or '').strip()
        scope_name = (dept_scope_name or '').strip()
        if scope_code or scope_name:
            scope_cond = sqlalchemy_dept_match(
                IntelSuspectWarning.sdpcsdm,
                IntelSuspectWarning.sdpcs,
                DeptDataScope(unrestricted=False, dept_code=scope_code, dept_name=scope_name),
            )
            if scope_cond is not None:
                stmt = stmt.where(scope_cond)
        stmt = stmt.order_by(IntelSuspectWarning.bjsj.desc(), IntelSuspectWarning.xlbh.desc())
        return PageUtil.paginate(db, stmt, page_num, page_size, is_page=True)

    @classmethod
    def fetch_jjd_alarms(cls, db: Session, jjdbh_list: list[str]) -> dict[str, dict]:
        """按接警单号批量碰撞 jjd_jjd，返回 {jjdbh: row}。"""
        ids = []
        seen = set()
        for raw in jjdbh_list:
            value = str(raw or '').strip()
            if not value or value in seen:
                continue
            seen.add(value)
            ids.append(value)
        if not ids:
            return {}

        # CHAR(30) 右侧空格填充，等值匹配才能走主键
        padded_ids = [value.ljust(30)[:30] for value in ids]
        sql = text(
            """
            SELECT
                TRIM(j.jjdbh) AS jjdbh,
                j.bjsj AS jjd_bjsj,
                j.bjrxm,
                j.yhxm,
                j.yhsfz,
                j.bjdh,
                j.lxdh,
                j.bjnr,
                j.afdd,
                j.yhdz,
                j.bjlbdm,
                j.bjlxdm,
                j.bjxldm,
                j.jjdwmc,
                j.gxdwdm,
                lb.bjlbmc,
                lx.bjlxmc,
                xl.bjxlmc
            FROM jjd_jjd j
            LEFT JOIN zd_bjlbdm lb ON CAST(lb.bjlbdm AS CHAR) = CAST(j.bjlbdm AS CHAR)
            LEFT JOIN zd_bjlxdm lx ON CAST(lx.bjlxdm AS CHAR) = CAST(j.bjlxdm AS CHAR)
            LEFT JOIN zd_bjxldm xl ON CAST(xl.bjxldm AS CHAR) = CAST(j.bjxldm AS CHAR)
            WHERE j.jjdbh IN :ids
            """
        ).bindparams(bindparam('ids', expanding=True))
        rows = (db.execute(sql, {'ids': padded_ids + ids})).mappings().all()
        result: dict[str, dict] = {}
        for row in rows:
            key = str(row.get('jjdbh') or '').strip()
            if key:
                result[key] = dict(row)
        return result


    @classmethod
    def get_by_xlbh(cls, db: Session, xlbh: int) -> IntelSuspectWarning | None:
        return (
            db.execute(select(IntelSuspectWarning).where(IntelSuspectWarning.xlbh == xlbh))
        ).scalars().first()

    @classmethod
    def update_handle(
        cls,
        db: Session,
        xlbh: int,
        handle_status: str,
        handle_remark: str | None,
        handle_by: str,
        handle_time: datetime,
    ) -> None:
        db.execute(
            update(IntelSuspectWarning)
            .where(IntelSuspectWarning.xlbh == xlbh)
            .values(
                handle_status=handle_status,
                handle_remark=handle_remark or '',
                handle_by=handle_by or '',
                handle_time=handle_time,
            )
        )

    @classmethod
    def _scope_where(cls, dept_scope_code: str | None = None, dept_scope_name: str | None = None):
        code = (dept_scope_code or '').strip()
        name = (dept_scope_name or '').strip()
        if not code and not name:
            return None
        return sqlalchemy_dept_match(
            IntelSuspectWarning.sdpcsdm,
            IntelSuspectWarning.sdpcs,
            DeptDataScope(unrestricted=False, dept_code=code, dept_name=name),
        )

    @classmethod
    def summary(
        cls,
        db: Session,
        dept_scope_code: str | None = None,
        dept_scope_name: str | None = None,
    ) -> dict:
        scope_cond = cls._scope_where(dept_scope_code, dept_scope_name)
        base_where = [scope_cond] if scope_cond is not None else []

        total_stmt = select(func.count()).select_from(IntelSuspectWarning)
        if base_where:
            total_stmt = total_stmt.where(*base_where)
        total = (db.execute(total_stmt)).scalar() or 0

        pending_conds = [
            (IntelSuspectWarning.handle_status == '0')
            | (IntelSuspectWarning.handle_status == 0)
            | (IntelSuspectWarning.handle_status.is_(None))
        ] + base_where
        pending = (
            db.execute(select(func.count()).select_from(IntelSuspectWarning).where(*pending_conds))
        ).scalar() or 0

        handled_conds = [
            (IntelSuspectWarning.handle_status == '1') | (IntelSuspectWarning.handle_status == 1)
        ] + base_where
        handled = (
            db.execute(select(func.count()).select_from(IntelSuspectWarning).where(*handled_conds))
        ).scalar() or 0

        ignored_conds = [
            (IntelSuspectWarning.handle_status == '2') | (IntelSuspectWarning.handle_status == 2)
        ] + base_where
        ignored = (
            db.execute(select(func.count()).select_from(IntelSuspectWarning).where(*ignored_conds))
        ).scalar() or 0

        label_stmt = select(IntelSuspectWarning.tjwdbq, func.count()).group_by(IntelSuspectWarning.tjwdbq)
        if base_where:
            label_stmt = label_stmt.where(*base_where)
        label_rows = (db.execute(label_stmt.order_by(func.count().desc()))).all()
        labels = [
            {'label': str(name or '未标注'), 'count': int(count or 0)}
            for name, count in label_rows
        ]
        return {
            'total': int(total),
            'pending': int(pending),
            'handled': int(handled),
            'ignored': int(ignored),
            'labels': labels,
        }

    @classmethod
    def list_label_options(cls, db: Session) -> list[str]:
        rows = (
            db.execute(
                select(IntelSuspectWarning.tjwdbq)
                .where(IntelSuspectWarning.tjwdbq.is_not(None))
                .where(IntelSuspectWarning.tjwdbq != '')
                .group_by(IntelSuspectWarning.tjwdbq)
                .order_by(IntelSuspectWarning.tjwdbq)
            )
        ).all()
        return [str(row[0]).strip() for row in rows if row and row[0]]
