"""重复涉警预警 DAO（jq-total-cf）。"""

from sqlalchemy import Integer, String, cast, case, func, or_, select
from sqlalchemy.orm import Session

from app.models.intelligence import IntelRepeatWarning
from app.schemas.warning import IntelligenceRepeatWarningQueryModel
from app.domain.warning.dept_data_scope import DeptDataScope, sqlalchemy_dept_match
from app.utils.page_util import PageUtil


class RepeatWarningDao:
    @classmethod
    def _org_condition(cls, org_code: str | None, org_name: str | None):
        code = (org_code or '').strip()
        name = (org_name or '').strip()
        parts = []
        if code:
            code_str = cast(IntelRepeatWarning.pcsdm, String)
            left6 = code[:6] if len(code) >= 6 else code
            left8 = code[:8] if len(code) >= 8 else code
            parts.append(func.left(code_str, 6) == left6)
            parts.append(func.left(code_str, 8) == left8)
        if name:
            parts.append(IntelRepeatWarning.pcsmc == name)
        if not parts:
            return None
        return or_(*parts)

    @classmethod
    def _bjcs_num_expr(cls):
        """bjcs 存 varchar，按数值比较。"""
        return cast(func.nullif(func.trim(func.coalesce(IntelRepeatWarning.bjcs, '')), ''), Integer)

    @classmethod
    def _person_key_expr(cls):
        """按身份证分组；无身份证时回退姓名+电话。"""
        rysfz = func.trim(func.coalesce(IntelRepeatWarning.rysfz, ''))
        ryxm = func.trim(func.coalesce(IntelRepeatWarning.ryxm, ''))
        dhhm = func.trim(func.coalesce(IntelRepeatWarning.dhhm, ''))
        return case(
            (rysfz != '', func.concat('sfz:', rysfz)),
            else_=func.concat('nm:', ryxm, '|', dhhm),
        )

    @classmethod
    def _build_filters(cls, query: IntelligenceRepeatWarningQueryModel):
        conditions = []
        keyword = (query.keyword or '').strip()
        if keyword:
            like = f'%{keyword}%'
            conditions.append(
                or_(
                    IntelRepeatWarning.ryxm.like(like),
                    IntelRepeatWarning.rysfz.like(like),
                    IntelRepeatWarning.dhhm.like(like),
                    IntelRepeatWarning.pcsmc.like(like),
                    cast(IntelRepeatWarning.jjdbh, String).like(like),
                )
            )
        if (query.ryxm or '').strip():
            conditions.append(IntelRepeatWarning.ryxm.like(f'%{query.ryxm.strip()}%'))
        if (query.rysfz or '').strip():
            conditions.append(IntelRepeatWarning.rysfz.like(f'%{query.rysfz.strip()}%'))
        if (query.dhhm or '').strip():
            conditions.append(IntelRepeatWarning.dhhm.like(f'%{query.dhhm.strip()}%'))
        if (query.pcsmc or '').strip():
            conditions.append(IntelRepeatWarning.pcsmc.like(f'%{query.pcsmc.strip()}%'))
        org_code = (query.org_code or query.pcsdm or '').strip()
        org_name = (query.org_name or '').strip()
        if org_code or org_name:
            org_cond = cls._org_condition(org_code or None, org_name or None)
            if org_cond is not None:
                conditions.append(org_cond)
        begin = (query.begin_bjsj or query.begin_rq or '').strip()
        end = (query.end_bjsj or query.end_rq or '').strip()
        time_col = func.coalesce(IntelRepeatWarning.bjsj, IntelRepeatWarning.tjsj)
        if begin:
            conditions.append(time_col >= begin)
        if end:
            conditions.append(time_col <= end)
        scope_code = (query.dept_scope_code or '').strip()
        scope_name = (query.dept_scope_name or '').strip()
        if scope_code or scope_name:
            scope_cond = sqlalchemy_dept_match(
                IntelRepeatWarning.pcsdm,
                IntelRepeatWarning.pcsmc,
                DeptDataScope(unrestricted=False, dept_code=scope_code, dept_name=scope_name),
            )
            if scope_cond is not None:
                conditions.append(scope_cond)
        return conditions

    @classmethod
    def list_page(cls, db: Session, query: IntelligenceRepeatWarningQueryModel):
        stmt = select(IntelRepeatWarning)
        for condition in cls._build_filters(query):
            stmt = stmt.where(condition)
        stmt = stmt.order_by(IntelRepeatWarning.bjsj.desc(), IntelRepeatWarning.xlbh.desc())
        return PageUtil.paginate(db, stmt, query.page_num, query.page_size, is_page=True)

    @classmethod
    def list_summary_page(cls, db: Session, query: IntelligenceRepeatWarningQueryModel):
        """按人员聚合：MAX(bjcs 数值) + MIN(xlbh)。"""
        person_key = cls._person_key_expr().label('person_key')
        bjcs_num = cls._bjcs_num_expr()
        stmt = select(
            person_key,
            func.max(IntelRepeatWarning.ryxm).label('ryxm'),
            func.max(IntelRepeatWarning.rysfz).label('rysfz'),
            func.max(IntelRepeatWarning.dhhm).label('dhhm'),
            func.max(IntelRepeatWarning.pcsdm).label('pcsdm'),
            func.max(IntelRepeatWarning.pcsmc).label('pcsmc'),
            func.max(bjcs_num).label('bjcs'),
            func.min(IntelRepeatWarning.xlbh).label('xlbh'),
            func.max(IntelRepeatWarning.tjsj).label('tjsj'),
            func.max(IntelRepeatWarning.bjsj).label('bjsj'),
            func.count().label('detail_count'),
        )
        for condition in cls._build_filters(query):
            stmt = stmt.where(condition)
        stmt = stmt.group_by(person_key).order_by(
            func.max(bjcs_num).desc(),
            func.min(IntelRepeatWarning.xlbh).desc(),
        )
        return PageUtil.paginate(db, stmt, query.page_num, query.page_size, is_page=True)

    @classmethod
    def list_person_details(
        cls,
        db: Session,
        rysfz: str | None,
        ryxm: str | None = None,
        dhhm: str | None = None,
        page_num: int = 1,
        page_size: int = 50,
        dept_scope_code: str | None = None,
        dept_scope_name: str | None = None,
    ):
        stmt = select(IntelRepeatWarning)
        sfz = (rysfz or '').strip()
        if sfz:
            stmt = stmt.where(func.trim(func.coalesce(IntelRepeatWarning.rysfz, '')) == sfz)
        else:
            name = (ryxm or '').strip()
            phone = (dhhm or '').strip()
            stmt = stmt.where(func.trim(func.coalesce(IntelRepeatWarning.ryxm, '')) == name)
            stmt = stmt.where(func.trim(func.coalesce(IntelRepeatWarning.dhhm, '')) == phone)
        scope_code = (dept_scope_code or '').strip()
        scope_name = (dept_scope_name or '').strip()
        if scope_code or scope_name:
            scope_cond = sqlalchemy_dept_match(
                IntelRepeatWarning.pcsdm,
                IntelRepeatWarning.pcsmc,
                DeptDataScope(unrestricted=False, dept_code=scope_code, dept_name=scope_name),
            )
            if scope_cond is not None:
                stmt = stmt.where(scope_cond)
        stmt = stmt.order_by(IntelRepeatWarning.bjsj.desc(), IntelRepeatWarning.xlbh.desc())
        return PageUtil.paginate(db, stmt, page_num, page_size, is_page=True)

    @classmethod
    def get_by_xlbh(cls, db: Session, xlbh: int) -> IntelRepeatWarning | None:
        return (
            db.execute(select(IntelRepeatWarning).where(IntelRepeatWarning.xlbh == xlbh))
        ).scalars().first()

    @classmethod
    def summary(
        cls,
        db: Session,
        dept_scope_code: str | None = None,
        dept_scope_name: str | None = None,
    ) -> dict:
        scope_code = (dept_scope_code or '').strip()
        scope_name = (dept_scope_name or '').strip()
        scope_cond = None
        if scope_code or scope_name:
            scope_cond = sqlalchemy_dept_match(
                IntelRepeatWarning.pcsdm,
                IntelRepeatWarning.pcsmc,
                DeptDataScope(unrestricted=False, dept_code=scope_code, dept_name=scope_name),
            )
        total_stmt = select(func.count()).select_from(IntelRepeatWarning)
        person_stmt = select(func.count(func.distinct(cls._person_key_expr())))
        if scope_cond is not None:
            total_stmt = total_stmt.where(scope_cond)
            person_stmt = person_stmt.where(scope_cond)
        total_rows = (db.execute(total_stmt)).scalar() or 0
        person_total = (db.execute(person_stmt)).scalar() or 0
        return {
            'total': int(person_total),
            'pending': int(person_total),
            'handled': 0,
            'ignored': 0,
            'labels': [{'label': '明细行', 'count': int(total_rows)}],
        }
