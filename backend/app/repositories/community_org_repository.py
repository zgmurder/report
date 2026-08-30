from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.community_org import CommunityOrgMapping


class CommunityOrgRepository:
    """社区组织映射：直接读 community_org_mappings，不再从 Excel 灌库。"""

    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[dict[str, Any]]:
        rows = self.db.scalars(
            select(CommunityOrgMapping).order_by(CommunityOrgMapping.source_row.asc())
        ).all()
        return [
            {
                "fasqdm": row.fasqdm,
                "fasqmc": row.fasqmc,
                "aliases": self._aliases(row),
                "station_name": row.station_name,
                "gxdwdm": row.gxdwdm,
                "org_type": row.org_type,
                "org_name": row.org_name,
            }
            for row in rows
        ]

    def count(self) -> int:
        return len(self.db.scalars(select(CommunityOrgMapping.id)).all())

    @staticmethod
    def _aliases(row: CommunityOrgMapping) -> list[str]:
        aliases: list[str] = []
        for value in (row.fasqmc, row.mapping_name):
            value = str(value or "").strip()
            if value and value not in aliases:
                aliases.append(value)
        return aliases
