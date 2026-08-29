from datetime import datetime
from typing import Any

from app.schemas.report import ReportContent, ReportCreateRequest, ReportDetail, ReportItem


class ReportRepository:
    """报告仓库占位实现。

    第一阶段使用进程内存便于跑通接口；正式实现必须替换为数据库权威存储。
    """

    _items: dict[int, dict[str, Any]] = {}
    _next_id: int = 1

    def create(self, req: ReportCreateRequest) -> ReportDetail:
        now = datetime.now()
        report_id = ReportRepository._next_id
        ReportRepository._next_id += 1
        item = {
            "id": report_id,
            "title": req.title,
            "report_type": req.report_type,
            "status": "draft",
            "source_query": req.source_query,
            "content_json": None,
            "draft_json": None,
            "created_at": now,
            "updated_at": now,
        }
        ReportRepository._items[report_id] = item
        return ReportDetail(**item)

    def list(self) -> list[ReportItem]:
        return [ReportItem(**item) for item in sorted(ReportRepository._items.values(), key=lambda x: x["id"], reverse=True)]

    def get(self, report_id: int) -> ReportDetail | None:
        item = ReportRepository._items.get(report_id)
        return ReportDetail(**item) if item else None

    def save_content(self, report_id: int, content: ReportContent) -> ReportDetail | None:
        item = ReportRepository._items.get(report_id)
        if not item:
            return None
        item["content_json"] = content.model_dump()
        item["status"] = "confirmed"
        item["updated_at"] = datetime.now()
        return ReportDetail(**item)

    def save_draft(self, report_id: int, draft: ReportContent) -> ReportDetail | None:
        item = ReportRepository._items.get(report_id)
        if not item:
            return None
        item["draft_json"] = draft.model_dump()
        item["updated_at"] = datetime.now()
        return ReportDetail(**item)
