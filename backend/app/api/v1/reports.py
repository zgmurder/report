from fastapi import APIRouter

from app.core.response import ok
from app.schemas.report import ReportCreateRequest, ReportGenerateRequest, ReportSaveRequest
from app.services.report_service import ReportService

router = APIRouter()


def get_service() -> ReportService:
    return ReportService()


@router.post("")
def create_report(req: ReportCreateRequest):
    return ok(get_service().create(req))


@router.get("")
def list_reports():
    return ok(get_service().list())


@router.get("/{report_id}")
def get_report(report_id: int):
    return ok(get_service().get(report_id))


@router.put("/{report_id}/content")
def save_report(report_id: int, req: ReportSaveRequest):
    return ok(get_service().save(report_id, req))


@router.post("/{report_id}/generate-draft")
def generate_draft(report_id: int, req: ReportGenerateRequest):
    return ok(get_service().generate_draft(report_id, req))
