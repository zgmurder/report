from fastapi import APIRouter, Depends
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


@router.put("/{report_id}/content")
def save_report(report_id: int, req: ReportSaveRequest, service: ReportService = Depends(get_service)):
    return ok(service.save(report_id, req))


@router.post("/{report_id}/generate-draft")
def generate_draft(report_id: int, req: ReportGenerateRequest, service: ReportService = Depends(get_service)):
    return ok(service.generate_draft(report_id, req))
