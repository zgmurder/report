"""接警单报警类别树（zd_bjlbdm / zd_bjlxdm / zd_bjxldm）。"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.domain.atomic_metric.exceptions import ServiceException
from app.schemas.warning import FeedbackCategoryNode


class IncidentCategoryService:
    @classmethod
    def tree(cls, db: Session) -> list[FeedbackCategoryNode]:
        try:
            category_rows = cls._fetch_rows(
                db,
                """
                SELECT
                  CAST(CAST(bjlbdm AS SIGNED) AS CHAR) AS code,
                  bjlbmc AS name,
                  bh,
                  pxh
                FROM zd_bjlbdm
                WHERE bjlbdm IS NOT NULL
                ORDER BY COALESCE(pxh, 0), CAST(bh AS UNSIGNED), bh
                """,
            )
            type_rows = cls._fetch_rows(
                db,
                """
                SELECT
                  CAST(CAST(bjlxdm AS SIGNED) AS CHAR) AS code,
                  bjlxmc AS name,
                  bjlb AS parent_codes,
                  pxh
                FROM zd_bjlxdm
                WHERE bjlxdm IS NOT NULL
                ORDER BY COALESCE(pxh, 0), CAST(CAST(bjlxdm AS SIGNED) AS CHAR)
                """,
            )
            subtype_rows = cls._fetch_rows(
                db,
                """
                SELECT
                  CAST(CAST(bjxldm AS SIGNED) AS CHAR) AS code,
                  bjxlmc AS name,
                  bjlx AS parent_code,
                  pxh
                FROM zd_bjxldm
                WHERE bjxldm IS NOT NULL
                ORDER BY COALESCE(pxh, 0), CAST(CAST(bjxldm AS SIGNED) AS CHAR)
                """,
            )
        except SQLAlchemyError as exc:
            raise ServiceException(message='接警报警分类表不存在或不可查询，请先导入 zd_bjlbdm/zd_bjlxdm/zd_bjxldm') from exc

        subtypes_by_type: dict[str, list[dict[str, Any]]] = {}
        for row in subtype_rows:
            parent_code = cls._norm_code(row.get('parent_code'))
            if not parent_code:
                continue
            subtypes_by_type.setdefault(parent_code, []).append(row)

        types_by_category: dict[str, list[dict[str, Any]]] = {}
        for row in type_rows:
            for parent_code in cls._split_parent_codes(row.get('parent_codes')):
                types_by_category.setdefault(parent_code, []).append(row)

        tree: list[FeedbackCategoryNode] = []
        for row in category_rows:
            category_code = cls._norm_code(row.get('code'))
            if not category_code:
                continue
            type_nodes = [
                cls._type_node(type_row, category_code, subtypes_by_type)
                for type_row in types_by_category.get(category_code, [])
            ]
            tree.append(
                FeedbackCategoryNode(
                    code=category_code,
                    name=str(row.get('name') or category_code),
                    level='category',
                    children=type_nodes,
                )
            )
        return tree

    @classmethod
    def _fetch_rows(cls, db: Session, sql: str) -> list[dict[str, Any]]:
        result = db.execute(text(sql))
        keys = list(result.keys())
        return [{key: row[index] for index, key in enumerate(keys)} for row in result.fetchall()]

    @classmethod
    def _split_parent_codes(cls, value: Any) -> list[str]:
        return [cls._norm_code(item) for item in str(value or '').split(',') if cls._norm_code(item)]

    @staticmethod
    def _norm_code(value: Any) -> str:
        text_value = str(value or '').strip()
        if not text_value:
            return ''
        try:
            # DECIMAL / "10.0" → "10"
            as_float = float(text_value)
            if as_float.is_integer():
                return str(int(as_float))
        except (TypeError, ValueError):
            pass
        return text_value

    @classmethod
    def _type_node(
        cls,
        row: dict[str, Any],
        parent_code: str,
        subtypes_by_type: dict[str, list[dict[str, Any]]],
    ) -> FeedbackCategoryNode:
        type_code = cls._norm_code(row.get('code'))
        subtype_nodes = [
            FeedbackCategoryNode(
                code=cls._norm_code(subtype.get('code')),
                name=str(subtype.get('name') or subtype.get('code') or ''),
                parent_code=type_code,
                level='subtype',
            )
            for subtype in subtypes_by_type.get(type_code, [])
            if cls._norm_code(subtype.get('code'))
        ]
        return FeedbackCategoryNode(
            code=type_code,
            name=str(row.get('name') or type_code),
            parent_code=parent_code,
            level='type',
            children=subtype_nodes,
        )
