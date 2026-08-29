from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import CurrentUser
from app.domain.ai.client import AiClient
from app.domain.report.validator import validate_report_content
from app.repositories.report_repository import ReportRepository
from app.schemas.report import (
    AiDraftResponse,
    ReportCreateRequest,
    ReportDetail,
    ReportFolderCreateRequest,
    ReportFolderItem,
    ReportGenerateRequest,
    ReportItem,
    ReportSaveRequest,
)


class ReportService:
    def __init__(self, db: Session, current_user: CurrentUser):
        self.repository = ReportRepository(db)
        self.ai_client = AiClient()
        self.current_user = current_user

    def create(self, req: ReportCreateRequest) -> ReportDetail:
        return self.repository.create(req, created_by=self.current_user.id)

    def list(self) -> list[ReportItem]:
        return self.repository.list()

    def list_folders(self) -> list[ReportFolderItem]:
        return self.repository.list_folders()

    def create_folder(self, req: ReportFolderCreateRequest) -> ReportFolderItem:
        return self.repository.create_folder(req.name, req.parent_id, created_by=self.current_user.id)

    def get(self, report_id: int) -> ReportDetail:
        report = self.repository.get(report_id)
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
        return report

    def save(self, report_id: int, req: ReportSaveRequest) -> ReportDetail:
        content = self._validate_content(req.content_json)
        report = self.repository.save_content(report_id, content, html_snapshot=req.html_snapshot)
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
        return report

    def generate_draft(self, report_id: int, req: ReportGenerateRequest) -> AiDraftResponse:
        report = self.get(report_id)
        draft = self.ai_client.generate_report_draft(report.title, req.report_type, req.source_query)
        draft = self._validate_content(draft)
        self.repository.save_draft(report_id, draft)
        return AiDraftResponse(
            draft_json=draft,
            explanation="AI 已生成结构化报告草稿，仅保存到 draft_json，需人工确认后才能成为正式内容。",
            warnings=["当前为 mock AI 输出", "请核对统计数据和敏感表述"],
        )

    @staticmethod
    def _validate_content(content):
        try:
            return validate_report_content(content)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
