"""派出所 mx_pcs_* 阈值预警 DAO。"""

from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.schemas.warning import IntelligencePcsMxWarningQueryModel
from app.domain.warning.dept_data_scope import DeptDataScope, sqlalchemy_dept_match
from app.utils.page_util import PageUtil


class MxPcsWarningDao:
    @classmethod
    def _org_condition(cls, entity: Any, org_code: str | None, org_name: str | None):
        code = (org_code or '').strip()
        name = (org_name or '').strip()
        parts = []
        if code:
            code_str = cast(entity.sdpcsdm, String)
            left6 = code[:6] if len(code) >= 6 else code
            left8 = code[:8] if len(code) >= 8 else code
            parts.append(func.left(code_str, 6) == left6)
            parts.append(func.left(code_str, 8) == left8)
        if name:
            parts.append(entity.sdpcs == name)
        if not parts:
            return None
        return or_(*parts)

    @classmethod
    def _build_filters(
        cls,
        entity: Any,
        query: IntelligencePcsMxWarningQueryModel,
        *,
        date_column,
    ):
        conditions = []
        keyword = (query.keyword or '').strip()
        if keyword:
            like = f'%{keyword}%'
            conditions.append(
                or_(
                    entity.sdpcs.like(like),
                    entity.ajlb.like(like),
                    cast(entity.sdpcsdm, String).like(like),
                )
            )
        if (query.sdpcs or '').strip():
            conditions.append(entity.sdpcs.like(f'%{query.sdpcs.strip()}%'))
        ajlb_parts = [part.strip() for part in str(query.ajlb or '').split(',') if part.strip()]
        if ajlb_parts:
            conditions.append(or_(*[entity.ajlb.like(f'%{part}%') for part in ajlb_parts]))
        if (query.sdpcsdm or '').strip() and not (query.org_code or '').strip():
            conditions.append(cast(entity.sdpcsdm, String) == str(query.sdpcsdm).strip())
        org_cond = cls._org_condition(entity, query.org_code or query.sdpcsdm, query.org_name)
        if org_cond is not None:
            conditions.append(org_cond)
        if (query.begin_rq or '').strip():
            conditions.append(date_column >= query.begin_rq.strip())
        if (query.end_rq or '').strip():
            conditions.append(date_column <= query.end_rq.strip())
        scope_code = (query.dept_scope_code or '').strip()
        scope_name = (query.dept_scope_name or '').strip()
        if scope_code or scope_name:
            scope_cond = sqlalchemy_dept_match(
                entity.sdpcsdm,
                entity.sdpcs,
                DeptDataScope(unrestricted=False, dept_code=scope_code, dept_name=scope_name),
            )
            if scope_cond is not None:
                conditions.append(scope_cond)
        return conditions

    @classmethod
    def list_page(
        cls,
        db: Session,
        entity: Any,
        query: IntelligencePcsMxWarningQueryModel,
        *,
        date_column,
        order_columns: list,
    ):
        stmt = select(entity)
        for condition in cls._build_filters(entity, query, date_column=date_column):
            stmt = stmt.where(condition)
        stmt = stmt.order_by(*[col.desc() for col in order_columns], entity.xlbh.desc())
        return PageUtil.paginate(db, stmt, query.page_num, query.page_size, is_page=True)

    @classmethod
    def get_by_xlbh(cls, db: Session, entity: Any, xlbh: int):
        stmt = select(entity).where(entity.xlbh == xlbh)
        return (db.execute(stmt)).scalars().first()

    @classmethod
    def summary(
        cls,
        db: Session,
        entity: Any,
        *,
        dept_scope_code: str | None = None,
        dept_scope_name: str | None = None,
    ) -> dict:
        base_conds = []
        scope_code = (dept_scope_code or '').strip()
        scope_name = (dept_scope_name or '').strip()
        if scope_code or scope_name:
            scope_cond = sqlalchemy_dept_match(
                entity.sdpcsdm,
                entity.sdpcs,
                DeptDataScope(unrestricted=False, dept_code=scope_code, dept_name=scope_name),
            )
            if scope_cond is not None:
                base_conds.append(scope_cond)
        base = select(entity)
        if base_conds:
            base = base.where(*base_conds)
        total = (db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
        category_stmt = select(entity.ajlb, func.count())
        if base_conds:
            category_stmt = category_stmt.where(*base_conds)
        category_rows = (
            db.execute(category_stmt.group_by(entity.ajlb).order_by(func.count().desc()))
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
