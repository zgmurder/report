from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import local_now


class CommunityOrgMapping(Base):
    """社区组织映射（community_org_mappings），供片区/共建委/警务区折叠。"""

    __tablename__ = "community_org_mappings"
    __table_args__ = (
        UniqueConstraint("seed_key", name="uq_community_org_mapping_seed_key"),
        Index("ix_community_org_mapping_code_type", "fasqdm", "org_type"),
        Index("ix_community_org_mapping_name_type", "fasqmc", "org_type"),
        Index("ix_community_org_mapping_station_type", "station_name", "org_type"),
        Index("ix_community_org_mapping_org", "org_type", "org_name"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seed_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    fasqdm: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    fasqmc: Mapped[str] = mapped_column(String(100), nullable=False)
    xzqh: Mapped[str] = mapped_column(String(12), nullable=False, default="")
    gxdwdm: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    mapping_name: Mapped[str] = mapped_column(String(100), nullable=False)
    station_name: Mapped[str] = mapped_column(String(100), nullable=False)
    org_type: Mapped[str] = mapped_column(String(20), nullable=False)
    org_name: Mapped[str] = mapped_column(String(100), nullable=False)
    match_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unmatched")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=local_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=local_now, onupdate=local_now
    )
