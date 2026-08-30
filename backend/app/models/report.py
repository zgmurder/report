from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import local_now


class ReportFolder(Base):
    __tablename__ = "report_folders"
    __table_args__ = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=local_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=local_now, onupdate=local_now)


class ReportDocument(Base):
    __tablename__ = "report_documents"
    __table_args__ = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False, default="monthly")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    folder_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_query: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    editor_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    content_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    draft_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Word 模板转换后的内联样式 HTML 很容易超过 MySQL TEXT 的 64KB 上限。
    html_snapshot: Mapped[str | None] = mapped_column(Text().with_variant(LONGTEXT(), "mysql"), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=local_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=local_now, onupdate=local_now)
