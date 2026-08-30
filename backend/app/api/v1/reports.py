from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.core.security import CurrentUser, get_current_user
from app.schemas.report import (
    ReportCreateRequest,
    ReportFolderCreateRequest,
    ReportFolderUpdateRequest,
    ReportGenerateRequest,
    ReportSaveRequest,
    ReportUpdateRequest,
)
from app.services.report_service import ReportService

router = APIRouter()


def get_service(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> ReportService:
    return ReportService(db, current_user)


@router.post("")
def create_report(req: ReportCreateRequest, service: ReportService = Depends(get_service)):
    return ok(service.create(req))


@router.get("")
def list_reports(service: ReportService = Depends(get_service)):
    return ok(service.list())


@router.get("/folders")
def list_folders(service: ReportService = Depends(get_service)):
    return ok(service.list_folders())


@router.post("/folders")
def create_folder(req: ReportFolderCreateRequest, service: ReportService = Depends(get_service)):
    return ok(service.create_folder(req))


@router.put("/folders/{folder_id}")
def update_folder(folder_id: int, req: ReportFolderUpdateRequest, service: ReportService = Depends(get_service)):
    return ok(service.update_folder(folder_id, req))


@router.delete("/folders/{folder_id}")
def delete_folder(folder_id: int, service: ReportService = Depends(get_service)):
    return ok(service.delete_folder(folder_id))


@router.get("/{report_id}")
def get_report(report_id: int, service: ReportService = Depends(get_service)):
    return ok(service.get(report_id))


@router.put("/{report_id}")
def update_report(report_id: int, req: ReportUpdateRequest, service: ReportService = Depends(get_service)):
    return ok(service.update(report_id, req))


@router.delete("/{report_id}")
def delete_report(report_id: int, service: ReportService = Depends(get_service)):
    return ok(service.delete(report_id))


@router.post("/{report_id}/confirm")
def confirm_report(report_id: int, service: ReportService = Depends(get_service)):
    return ok(service.confirm_draft(report_id))


@router.get("/{report_id}/export-html")
def export_report_html(report_id: int, service: ReportService = Depends(get_service)):
    return Response(
        content=service.export_html(report_id),
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data: https:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{report_id}/export-docx")
def export_report_docx(report_id: int, service: ReportService = Depends(get_service)):
    title, content = service.export_docx(report_id)
    filename = quote(f"{title}.docx")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.put("/{report_id}/content")
def save_report(report_id: int, req: ReportSaveRequest, service: ReportService = Depends(get_service)):
    return ok(service.save(report_id, req))


@router.put("/{report_id}/draft")
def save_report_draft(report_id: int, req: ReportSaveRequest, service: ReportService = Depends(get_service)):
    return ok(service.save_draft(report_id, req))


@router.post("/{report_id}/generate-draft")
def generate_draft(report_id: int, req: ReportGenerateRequest, service: ReportService = Depends(get_service)):
    return ok(service.generate_draft(report_id, req))
