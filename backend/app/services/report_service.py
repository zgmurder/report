from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, is_admin
from app.domain.ai.client import AiClient
from app.domain.report.validator import validate_report_content
from app.repositories.report_repository import ReportRepository, ReportStateConflict
from app.services.export_service import ExportService
from app.schemas.report import (
    AiDraftResponse,
    ReportCreateRequest,
    ReportDetail,
    ReportFolderCreateRequest,
    ReportFolderItem,
    ReportFolderUpdateRequest,
    ReportGenerateRequest,
    ReportItem,
    ReportSaveRequest,
    ReportUpdateRequest,
)


class ReportService:
    def __init__(self, db: Session, current_user: CurrentUser):
        self.repository = ReportRepository(db, current_user.id, is_admin(current_user))
        self.ai_client = AiClient()
        self.export_service = ExportService()
        self.current_user = current_user

    def create(self, req: ReportCreateRequest) -> ReportDetail:
        req.title = self._require_text(req.title, "报告标题不能为空")
        req.report_type = self._require_text(req.report_type, "报告类型不能为空")
        self._validate_folder(req.folder_id)
        return self.repository.create(req)

    def list(self) -> list[ReportItem]:
        return self.repository.list()

    def list_folders(self) -> list[ReportFolderItem]:
        return self.repository.list_folders()

    def create_folder(self, req: ReportFolderCreateRequest) -> ReportFolderItem:
        name = self._require_text(req.name, "目录名称不能为空")
        self._validate_folder(req.parent_id)
        return self.repository.create_folder(name, req.parent_id)

    def update_folder(self, folder_id: int, req: ReportFolderUpdateRequest) -> ReportFolderItem:
        if not self.repository.folder_exists(folder_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件夹不存在")
        parent_id_provided = "parent_id" in req.model_fields_set
        if parent_id_provided:
            if req.parent_id == folder_id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="上级目录不能选择自身")
            self._validate_folder(req.parent_id)
            if req.parent_id is not None and self.repository.folder_has_ancestor(req.parent_id, folder_id):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="上级目录不能是当前目录的子目录")
        name = self._require_text(req.name, "目录名称不能为空") if req.name is not None else None
        folder = self.repository.update_folder(
            folder_id,
            name,
            req.parent_id,
            req.sort_order,
            parent_id_provided=parent_id_provided,
        )
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件夹不存在")
        return folder

    def delete_folder(self, folder_id: int) -> dict[str, bool]:
        deleted = self.repository.delete_folder(folder_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件夹不存在")
        return {"deleted": True}

    def get(self, report_id: int) -> ReportDetail:
        report = self.repository.get(report_id)
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
        return report

    def update(self, report_id: int, req: ReportUpdateRequest) -> ReportDetail:
        if "folder_id" in req.model_fields_set:
            self._validate_folder(req.folder_id)
        title = self._require_text(req.title, "报告标题不能为空") if req.title is not None else None
        try:
            report = self.repository.update(
                report_id,
                title=title,
                folder_id=req.folder_id,
                status=req.status,
                folder_id_provided="folder_id" in req.model_fields_set,
            )
        except ReportStateConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
        return report

    def delete(self, report_id: int) -> dict[str, bool]:
        deleted = self.repository.delete(report_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
        return {"deleted": True}

    def confirm_draft(self, report_id: int) -> ReportDetail:
        try:
            report = self.repository.confirm_draft(report_id, self._validate_content)
        except ReportStateConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在或没有可确认的草稿")
        return report

    def export_html(self, report_id: int) -> str:
        report = self._get_exportable(report_id)
        return self.export_service.render_report_html(report)

    def export_docx(self, report_id: int) -> tuple[str, bytes]:
        report = self._get_exportable(report_id)
        return report.title, self.export_service.render_report_docx(report)

    def save(self, report_id: int, req: ReportSaveRequest) -> ReportDetail:
        content = self._validate_content(req.content_json)
        try:
            report = self.repository.save_content(
                report_id,
                content,
                html_snapshot=req.html_snapshot,
                editor_config=req.editor_config,
            )
        except ReportStateConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
        return report

    def save_draft(self, report_id: int, req: ReportSaveRequest) -> ReportDetail:
        content = self._validate_content(req.content_json)
        try:
            report = self.repository.save_draft(
                report_id,
                content,
                html_snapshot=req.html_snapshot,
                editor_config=req.editor_config,
            )
        except ReportStateConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
        return report

    def generate_draft(self, report_id: int, req: ReportGenerateRequest) -> AiDraftResponse:
        report = self.get(report_id)
        draft = self.ai_client.generate_report_draft(report.title, req.report_type, req.source_query)
        draft = self._validate_content(draft)
        try:
            saved = self.repository.save_draft(report_id, draft)
        except ReportStateConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        if not saved:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
        return AiDraftResponse(
            draft_json=draft,
            explanation="AI 已生成结构化报告草稿，仅保存到 draft_json，需人工确认后才能成为正式内容。",
            warnings=["当前为 mock AI 输出", "请核对统计数据和敏感表述"],
        )

    def _get_exportable(self, report_id: int) -> ReportDetail:
        report = self.get(report_id)
        if report.status != "confirmed" or not report.content_json:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="报告尚未确认，无法导出正式版本")
        report.content_json = self._validate_content(report.content_json)
        return report

    def _validate_folder(self, folder_id: int | None) -> None:
        if folder_id is not None and not self.repository.folder_exists(folder_id):
            # 不区分目录不存在与无权访问，避免泄露其他用户目录的存在性。
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="目录不存在")

    @staticmethod
    def _require_text(value: str, message: str) -> str:
        text = value.strip()
        if not text:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)
        return text

    @staticmethod
    def _validate_content(content):
        try:
            return validate_report_content(content)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
