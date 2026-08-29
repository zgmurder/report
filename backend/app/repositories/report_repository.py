from __future__ import annotations

from app.models.report import ReportDocument, ReportFolder
from app.schemas.report import ReportContent, ReportCreateRequest, ReportDetail, ReportFolderItem, ReportItem
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class ReportRepository:
    """报告仓库数据库实现。"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, req: ReportCreateRequest, created_by: int | None = None) -> ReportDetail:
        row = ReportDocument(
            title=req.title,
            report_type=req.report_type,
            status="draft",
            folder_id=req.folder_id,
            source_query=req.source_query,
            created_by=created_by,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_detail(row)

    def list(self) -> list[ReportItem]:
        rows = self.db.scalars(select(ReportDocument).order_by(ReportDocument.updated_at.desc(), ReportDocument.id.desc())).all()
        return [self._to_item(row) for row in rows]

    def list_folders(self) -> list[ReportFolderItem]:
        rows = self.db.scalars(select(ReportFolder).order_by(ReportFolder.sort_order.asc(), ReportFolder.id.asc())).all()
        counts = dict(self.db.execute(select(ReportDocument.folder_id, func.count()).group_by(ReportDocument.folder_id)).all())
        return [
            ReportFolderItem(
                id=row.id,
                name=row.name,
                parent_id=row.parent_id,
                sort_order=row.sort_order,
                report_count=counts.get(row.id, 0),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    def create_folder(self, name: str, parent_id: int | None = None, created_by: int | None = None) -> ReportFolderItem:
        row = ReportFolder(name=name, parent_id=parent_id, created_by=created_by)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return ReportFolderItem(
            id=row.id,
            name=row.name,
            parent_id=row.parent_id,
            sort_order=row.sort_order,
            report_count=0,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def update_folder(self, folder_id: int, name: str | None = None, parent_id: int | None = None, sort_order: int | None = None) -> ReportFolderItem | None:
        row = self.db.get(ReportFolder, folder_id)
        if not row:
            return None
        if name is not None:
            row.name = name
        if parent_id is not None:
            row.parent_id = parent_id
        if sort_order is not None:
            row.sort_order = sort_order
        self.db.commit()
        self.db.refresh(row)
        count = self.db.scalar(select(func.count()).select_from(ReportDocument).where(ReportDocument.folder_id == row.id)) or 0
        return ReportFolderItem(
            id=row.id,
            name=row.name,
            parent_id=row.parent_id,
            sort_order=row.sort_order,
            report_count=count,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def delete_folder(self, folder_id: int) -> bool:
        row = self.db.get(ReportFolder, folder_id)
        if not row:
            return False
        for report in self.db.scalars(select(ReportDocument).where(ReportDocument.folder_id == folder_id)).all():
            report.folder_id = None
        self.db.delete(row)
        self.db.commit()
        return True

    def get(self, report_id: int) -> ReportDetail | None:
        row = self.db.get(ReportDocument, report_id)
        return self._to_detail(row) if row else None

    def update(self, report_id: int, title: str | None = None, folder_id: int | None = None, status: str | None = None, folder_id_provided: bool = False) -> ReportDetail | None:
        row = self.db.get(ReportDocument, report_id)
        if not row:
            return None
        if title is not None:
            row.title = title
        if folder_id_provided:
            row.folder_id = folder_id
        if status is not None:
            row.status = status
        self.db.commit()
        self.db.refresh(row)
        return self._to_detail(row)

    def delete(self, report_id: int) -> bool:
        row = self.db.get(ReportDocument, report_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def save_content(self, report_id: int, content: ReportContent, html_snapshot: str | None = None) -> ReportDetail | None:
        row = self.db.get(ReportDocument, report_id)
        if not row:
            return None
        row.title = content.title or row.title
        row.report_type = content.type or row.report_type
        row.content_json = content.model_dump(mode="json")
        row.html_snapshot = html_snapshot
        row.status = "confirmed"
        self.db.commit()
        self.db.refresh(row)
        return self._to_detail(row)

    def save_draft(self, report_id: int, draft: ReportContent) -> ReportDetail | None:
        row = self.db.get(ReportDocument, report_id)
        if not row:
            return None
        row.draft_json = draft.model_dump(mode="json")
        self.db.commit()
        self.db.refresh(row)
        return self._to_detail(row)

    def _to_item(self, row: ReportDocument) -> ReportItem:
        return ReportItem(
            id=row.id,
            title=row.title,
            report_type=row.report_type,
            status=row.status,
            folder_id=row.folder_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _to_detail(self, row: ReportDocument) -> ReportDetail:
        item = self._to_item(row)
        return ReportDetail(
            **item.model_dump(),
            source_query=row.source_query or {},
            content_json=ReportContent.model_validate(row.content_json) if row.content_json else None,
            draft_json=ReportContent.model_validate(row.draft_json) if row.draft_json else None,
            html_snapshot=row.html_snapshot,
        )
