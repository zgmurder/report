from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.warning.dept_data_scope import DeptDataScope, dept_scope_sql

FKD_TABLE = "fkd_fkd"
TAG_RESULT_TABLE = "jq_tag_result"


class TagV2Repository:
    """Scoped data access used by alarm detail and manual verification."""

    def __init__(self, db: Session):
        self.db = db

    def get_scoped_alarm(
        self,
        fkdbh: str,
        scope: DeptDataScope,
        *,
        full: bool,
        for_update: bool = False,
    ) -> dict[str, Any] | None:
        scope_sql, params = self._scope_sql(scope)
        params["fkdbh"] = fkdbh
        columns = "f.`fkdbh`, f.`bjsj`, f.`fkdwmc`, f.`fkdwdm`"
        if full:
            columns += ", f.`jjdbh`, f.`zrmj`, f.`cjqk`"
        sql = f"""
            SELECT {columns},
              (SELECT r.`jqqh` FROM `{TAG_RESULT_TABLE}` r WHERE r.`fkdbh` COLLATE utf8mb4_unicode_ci = f.`fkdbh` COLLATE utf8mb4_unicode_ci ORDER BY r.`id` DESC LIMIT 1) AS jqqh,
              (SELECT r.`czyj` FROM `{TAG_RESULT_TABLE}` r WHERE r.`fkdbh` COLLATE utf8mb4_unicode_ci = f.`fkdbh` COLLATE utf8mb4_unicode_ci ORDER BY r.`id` DESC LIMIT 1) AS czyj,
              (SELECT r.`cjqk` FROM `{TAG_RESULT_TABLE}` r WHERE r.`fkdbh` COLLATE utf8mb4_unicode_ci = f.`fkdbh` COLLATE utf8mb4_unicode_ci ORDER BY r.`id` DESC LIMIT 1) AS result_cjqk
            FROM `{FKD_TABLE}` f
            WHERE f.`fkdbh` = :fkdbh {scope_sql}
            LIMIT 1 {"FOR UPDATE" if for_update else ""}
        """
        row = self.db.execute(text(sql), params).mappings().first()
        return dict(row) if row else None

    @staticmethod
    def _scope_sql(scope: DeptDataScope) -> tuple[str, dict[str, Any]]:
        return dept_scope_sql(
            scope,
            code_column="f.`fkdwdm`",
            name_column="f.`fkdwmc`",
        )
