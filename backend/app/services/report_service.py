from fastapi import HTTPException, status

from app.domain.ai.client import AiClient
from app.domain.report.validator import validate_report_content
from app.repositories.report_repository import ReportRepository
from app.schemas.report import (
    AiDraftResponse,
    ReportCreateRequest,
    ReportDetail,
    ReportGenerateRequest,
    ReportItem,
    ReportSaveRequest,
)


class ReportService:
    def __init__(self):
        self.repository = ReportRepository()
        self.ai_client = AiClient()

    def create(self, req: ReportCreateRequest) -> ReportDetail:
        return self.repository.create(req)

    def list(self) -> list[ReportItem]:
        return self.repository.list()

    def get(self, report_id: int) -> ReportDetail:
        report = self.repository.get(report_id)
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
        return report

    def save(self, report_id: int, req: ReportSaveRequest) -> ReportDetail:
        content = validate_report_content(req.content_json)
        report = self.repository.save_content(report_id, content)
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在")
        return report

    def generate_draft(self, report_id: int, req: ReportGenerateRequest) -> AiDraftResponse:
        report = self.get(report_id)
        draft = self.ai_client.generate_report_draft(report.title, req.report_type, req.source_query)
        draft = validate_report_content(draft)
        self.repository.save_draft(report_id, draft)
        return AiDraftResponse(
            draft_json=draft,
            explanation="AI 已生成结构化报告草稿，仅保存到 draft_json，需人工确认后才能成为正式内容。",
            warnings=["当前为 mock AI 输出", "请核对统计数据和敏感表述"],
        )
