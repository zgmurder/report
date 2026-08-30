"""警情主类连续三天上升预警 DAO（jq-total-day）。"""

from sqlalchemy import Numeric, String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models.intelligence import IntelDayRiseWarning
from app.schemas.warning import IntelligenceDayRiseWarningQueryModel
from app.domain.warning.dept_data_scope import DeptDataScope, sqlalchemy_dept_match
from app.utils.page_util import PageUtil


class DayRiseWarningDao:
    @classmethod
    def _as_hb_number(cls, column):
        """环比字段为字符串（含 %），转数值；空串视为 NULL，避免误当成 0。"""
        cleaned = func.nullif(
            func.trim(func.replace(func.replace(cast(column, String), '%', ''), ',', '')),
            '',
        )
        return cast(cleaned, Numeric)

    @classmethod
    def _strict_rise_conditions(cls):
        """连续三天须严格递增：数量递增且三日环比均 > 0（持平不计）。"""
        qr_hb = cls._as_hb_number(IntelDayRiseWarning.qr_jqhb)
        zr_hb = cls._as_hb_number(IntelDayRiseWarning.zr_jqhb)
        dr_hb = cls._as_hb_number(IntelDayRiseWarning.drjqhb)
        return [
            IntelDayRiseWarning.jjzs.is_not(None),
            IntelDayRiseWarning.zr_pcsjjzs.is_not(None),
            IntelDayRiseWarning.qr_pcsjjzs.is_not(None),
            IntelDayRiseWarning.q3r_pcsjjzs.is_not(None),
            IntelDayRiseWarning.jjzs > IntelDayRiseWarning.zr_pcsjjzs,
            IntelDayRiseWarning.zr_pcsjjzs > IntelDayRiseWarning.qr_pcsjjzs,
            IntelDayRiseWarning.qr_pcsjjzs > IntelDayRiseWarning.q3r_pcsjjzs,
            dr_hb > 0,
            zr_hb > 0,
            qr_hb > 0,
        ]

    @classmethod
    def _org_condition(cls, org_code: str | None, org_name: str | None):
        code = (org_code or '').strip()
        name = (org_name or '').strip()
        parts = []
        if code:
            code_str = cast(IntelDayRiseWarning.sdpcsdm, String)
            left6 = code[:6] if len(code) >= 6 else code
            left8 = code[:8] if len(code) >= 8 else code
            parts.append(func.left(code_str, 6) == left6)
            parts.append(func.left(code_str, 8) == left8)
        if name:
            parts.append(IntelDayRiseWarning.sdpcs == name)
        if not parts:
            return None
        return or_(*parts)

    @classmethod
    def _build_filters(cls, query: IntelligenceDayRiseWarningQueryModel):
        conditions = list(cls._strict_rise_conditions())
        keyword = (query.keyword or '').strip()
        if keyword:
            like = f'%{keyword}%'
            conditions.append(
                or_(
                    IntelDayRiseWarning.sdpcs.like(like),
                    IntelDayRiseWarning.ajlb.like(like),
                    cast(IntelDayRiseWarning.sdpcsdm, String).like(like),
                )
            )
        if (query.sdpcs or '').strip():
            conditions.append(IntelDayRiseWarning.sdpcs.like(f'%{query.sdpcs.strip()}%'))
        ajlb_parts = [part.strip() for part in str(query.ajlb or '').split(',') if part.strip()]
        if ajlb_parts:
            conditions.append(
                or_(*[IntelDayRiseWarning.ajlb.like(f'%{part}%') for part in ajlb_parts])
            )
        if (query.sdpcsdm or '').strip() and not (query.org_code or '').strip():
            conditions.append(cast(IntelDayRiseWarning.sdpcsdm, String) == str(query.sdpcsdm).strip())
        org_cond = cls._org_condition(query.org_code or query.sdpcsdm, query.org_name)
        if org_cond is not None:
            conditions.append(org_cond)
        if (query.begin_rq or '').strip():
            conditions.append(IntelDayRiseWarning.rq >= query.begin_rq.strip())
        if (query.end_rq or '').strip():
            conditions.append(IntelDayRiseWarning.rq <= query.end_rq.strip())
        scope_code = (query.dept_scope_code or '').strip()
        scope_name = (query.dept_scope_name or '').strip()
        if scope_code or scope_name:
            scope_cond = sqlalchemy_dept_match(
                IntelDayRiseWarning.sdpcsdm,
                IntelDayRiseWarning.sdpcs,
                DeptDataScope(unrestricted=False, dept_code=scope_code, dept_name=scope_name),
            )
            if scope_cond is not None:
                conditions.append(scope_cond)
        return conditions

    @classmethod
    def list_page(cls, db: Session, query: IntelligenceDayRiseWarningQueryModel):
        stmt = select(IntelDayRiseWarning)
        for condition in cls._build_filters(query):
            stmt = stmt.where(condition)
        stmt = stmt.order_by(
            IntelDayRiseWarning.rq.desc(),
            IntelDayRiseWarning.jjzs.desc(),
            IntelDayRiseWarning.xlbh.desc(),
        )
        return PageUtil.paginate(db, stmt, query.page_num, query.page_size, is_page=True)

    @classmethod
    def get_by_xlbh(cls, db: Session, xlbh: int) -> IntelDayRiseWarning | None:
        stmt = select(IntelDayRiseWarning).where(IntelDayRiseWarning.xlbh == xlbh)
        for condition in cls._strict_rise_conditions():
            stmt = stmt.where(condition)
        return (db.execute(stmt)).scalars().first()

    @classmethod
    def summary(
        cls,
        db: Session,
        dept_scope_code: str | None = None,
        dept_scope_name: str | None = None,
    ) -> dict:
        base_conds = list(cls._strict_rise_conditions())
        scope_code = (dept_scope_code or '').strip()
        scope_name = (dept_scope_name or '').strip()
        if scope_code or scope_name:
            scope_cond = sqlalchemy_dept_match(
                IntelDayRiseWarning.sdpcsdm,
                IntelDayRiseWarning.sdpcs,
                DeptDataScope(unrestricted=False, dept_code=scope_code, dept_name=scope_name),
            )
            if scope_cond is not None:
                base_conds.append(scope_cond)
        base = select(IntelDayRiseWarning).where(*base_conds)
        total = (db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
        category_rows = (
            db.execute(
                select(IntelDayRiseWarning.ajlb, func.count())
                .where(*base_conds)
                .group_by(IntelDayRiseWarning.ajlb)
                .order_by(func.count().desc())
            )
        ).all()
        labels = [
            {'label': str(name or '未分类'), 'count': int(count or 0)}
            for name, count in category_rows
        ]
        return {
            'total': int(total),
            'pending': int(total),
            'handled': 0,
            'ignored': 0,
            'labels': labels,
        }
