from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models.report import ReportDocument, ReportFolder
from app.schemas.report import ReportContent, ReportCreateRequest, ReportDetail, ReportEditorConfig, ReportFolderItem, ReportItem


class ReportStateConflict(ValueError):
    """The requested write is incompatible with the report's locked state."""


class ReportRepository:
    """报告仓库数据库实现，统一按当前用户应用所有权范围。"""

    def __init__(self, db: Session, current_user_id: int, is_admin: bool = False):
        self.db = db
        self.current_user_id = current_user_id
        self.is_admin = is_admin

    def _ownership_filter(self, model: type[ReportDocument] | type[ReportFolder]) -> ColumnElement[bool]:
        # 历史 created_by 为空的数据只对管理员可见；管理员可访问全部数据。
        return model.id.is_not(None) if self.is_admin else model.created_by == self.current_user_id

    def _get_owned_report(self, report_id: int) -> ReportDocument | None:
        return self.db.scalar(
            select(ReportDocument).where(
                ReportDocument.id == report_id,
                self._ownership_filter(ReportDocument),
            )
        )

    def _lock_owned_report(self, report_id: int) -> ReportDocument | None:
        return self.db.scalar(
            select(ReportDocument)
            .where(ReportDocument.id == report_id, self._ownership_filter(ReportDocument))
            .with_for_update()
        )

    def _get_owned_folder(self, folder_id: int) -> ReportFolder | None:
        return self.db.scalar(
            select(ReportFolder).where(
                ReportFolder.id == folder_id,
                self._ownership_filter(ReportFolder),
            )
        )

    def create(self, req: ReportCreateRequest) -> ReportDetail:
        row = ReportDocument(
            title=req.title,
            report_type=req.report_type,
            status="draft",
            folder_id=req.folder_id,
            source_query=req.source_query,
            created_by=self.current_user_id,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_detail(row)

    def list(self) -> list[ReportItem]:
        # 列表页只读取摘要字段。content_json/editor_document 和 html_snapshot 可能很大，
        # 将整行参与 ORDER BY 会让 MySQL 的 filesort 很容易耗尽 sort buffer。
        rows = self.db.execute(
            select(
                ReportDocument.id,
                ReportDocument.title,
                ReportDocument.report_type,
                ReportDocument.status,
                ReportDocument.folder_id,
                ReportDocument.created_at,
                ReportDocument.updated_at,
            )
            .where(self._ownership_filter(ReportDocument))
            .order_by(ReportDocument.updated_at.desc(), ReportDocument.id.desc())
        ).all()
        return [
            ReportItem(
                id=row.id,
                title=row.title,
                report_type=row.report_type,
                status=row.status,
                folder_id=row.folder_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    def folder_exists(self, folder_id: int | None) -> bool:
        if folder_id is None:
            return True
        return self._get_owned_folder(folder_id) is not None

    def folder_has_ancestor(self, folder_id: int, ancestor_id: int) -> bool:
        """在当前用户可访问范围内沿父链查找，兼顾多级环和历史脏数据环。"""
        current_id: int | None = folder_id
        visited: set[int] = set()
        while current_id is not None:
            if current_id == ancestor_id:
                return True
            if current_id in visited:
                return True
            visited.add(current_id)
            row = self._get_owned_folder(current_id)
            if not row:
                return False
            current_id = row.parent_id
        return False

    def list_folders(self) -> list[ReportFolderItem]:
        rows = self.db.scalars(
            select(ReportFolder)
            .where(self._ownership_filter(ReportFolder))
            .order_by(ReportFolder.sort_order.asc(), ReportFolder.id.asc())
        ).all()
        counts = dict(
            self.db.execute(
                select(ReportDocument.folder_id, func.count())
                .where(self._ownership_filter(ReportDocument))
                .group_by(ReportDocument.folder_id)
            ).all()
        )
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

    def create_folder(self, name: str, parent_id: int | None = None) -> ReportFolderItem:
        row = ReportFolder(name=name, parent_id=parent_id, created_by=self.current_user_id)
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

    def update_folder(
        self,
        folder_id: int,
        name: str | None = None,
        parent_id: int | None = None,
        sort_order: int | None = None,
        parent_id_provided: bool = False,
    ) -> ReportFolderItem | None:
        row = self._get_owned_folder(folder_id)
        if not row:
            return None
        if name is not None:
            row.name = name
        if parent_id_provided:
            row.parent_id = parent_id
        if sort_order is not None:
            row.sort_order = sort_order
        self.db.commit()
        self.db.refresh(row)
        count = self.db.scalar(
            select(func.count())
            .select_from(ReportDocument)
            .where(
                ReportDocument.folder_id == row.id,
                self._ownership_filter(ReportDocument),
            )
        ) or 0
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
        row = self._get_owned_folder(folder_id)
        if not row:
            return False
        for child in self.db.scalars(
            select(ReportFolder).where(
                ReportFolder.parent_id == folder_id,
                self._ownership_filter(ReportFolder),
            )
        ).all():
            child.parent_id = None
        for report in self.db.scalars(
            select(ReportDocument).where(
                ReportDocument.folder_id == folder_id,
                self._ownership_filter(ReportDocument),
            )
        ).all():
            report.folder_id = None
        self.db.delete(row)
        self.db.commit()
        return True

    def get(self, report_id: int) -> ReportDetail | None:
        row = self._get_owned_report(report_id)
        return self._to_detail(row) if row else None

    def update(
        self,
        report_id: int,
        title: str | None = None,
        folder_id: int | None = None,
        status: str | None = None,
        folder_id_provided: bool = False,
    ) -> ReportDetail | None:
        row = self._lock_owned_report(report_id)
        if not row:
            return None
        current_status = str(row.status)
        requested_status = status or current_status
        if current_status == "archived" and (title is not None or folder_id_provided or requested_status != current_status):
            self.db.rollback()
            raise ReportStateConflict("已归档报告为只读，暂不支持恢复或修改")
        allowed = requested_status == current_status or (current_status == "confirmed" and requested_status == "archived")
        if not allowed:
            self.db.rollback()
            raise ReportStateConflict("不支持该报告状态转换；仅允许正式报告归档，暂不支持恢复或降级")
        if title is not None:
            row.title = title
        if folder_id_provided:
            row.folder_id = folder_id
        row.status = requested_status
        self.db.commit()
        self.db.refresh(row)
        return self._to_detail(row)

    def delete(self, report_id: int) -> bool:
        row = self._get_owned_report(report_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def confirm_draft(
        self,
        report_id: int,
        validate: Callable[[ReportContent], ReportContent],
    ) -> ReportDetail | None:
        row = self._lock_owned_report(report_id)
        if not row:
            return None
        if row.status != "draft":
            self.db.rollback()
            raise ReportStateConflict("只有草稿状态的报告可以确认")
        if not row.draft_json:
            self.db.rollback()
            raise ReportStateConflict("报告没有可确认的草稿")
        # Lock, parse, revalidate/sanitize and promote in one database transaction.
        try:
            content = validate(ReportContent.model_validate(row.draft_json))
        except Exception:
            self.db.rollback()
            raise
        row.title = content.title or row.title
        row.report_type = content.type or row.report_type
        row.content_json = content.model_dump(mode="json")
        row.draft_json = None
        row.status = "confirmed"
        self.db.commit()
        self.db.refresh(row)
        return self._to_detail(row)

    def save_content(
        self,
        report_id: int,
        content: ReportContent,
        html_snapshot: str | None = None,
        editor_config: ReportEditorConfig | None = None,
    ) -> ReportDetail | None:
        row = self._lock_owned_report(report_id)
        if not row:
            return None
        if row.status != "confirmed":
            self.db.rollback()
            raise ReportStateConflict("只有已确认报告可以保存正式内容")
        row.title = content.title or row.title
        row.report_type = content.type or row.report_type
        row.content_json = content.model_dump(mode="json")
        # Remove historical stale drafts so a confirmed report can never expose
        # or later persist a confirmed+draft combination through this path.
        row.draft_json = None
        row.html_snapshot = html_snapshot
        if editor_config is not None:
            row.editor_config = editor_config.model_dump(mode="json")
        # Formal saves do not perform a state transition; only confirm_draft does.
        self.db.commit()
        self.db.refresh(row)
        return self._to_detail(row)

    def save_draft(
        self,
        report_id: int,
        draft: ReportContent,
        html_snapshot: str | None = None,
        editor_config: ReportEditorConfig | None = None,
    ) -> ReportDetail | None:
        row = self._lock_owned_report(report_id)
        if not row:
            return None
        if row.status != "draft":
            self.db.rollback()
            raise ReportStateConflict("只有草稿状态的报告可以保存草稿；正式报告请保存正文")
        row.draft_json = draft.model_dump(mode="json")
        row.html_snapshot = html_snapshot
        if editor_config is not None:
            row.editor_config = editor_config.model_dump(mode="json")
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
        legacy_editor_config = {}
        if not row.editor_config and isinstance(row.content_json, dict):
            params = row.content_json.get("params")
            if isinstance(params, dict) and isinstance(params.get("editor"), dict):
                legacy_editor_config = params["editor"]
        return ReportDetail(
            **item.model_dump(),
            source_query=row.source_query or {},
            editor_config=ReportEditorConfig.model_validate(row.editor_config or legacy_editor_config),
            content_json=ReportContent.model_validate(row.content_json) if row.content_json else None,
            # Historical confirmed+draft rows must render authoritative content.
            draft_json=(
                ReportContent.model_validate(row.draft_json)
                if row.status == "draft" and row.draft_json
                else None
            ),
            html_snapshot=row.html_snapshot,
        )
