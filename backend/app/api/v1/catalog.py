from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.core.security import CurrentUser, get_current_user
from app.schemas.catalog import (
    DataSourceCreateRequest,
    DataSourceUpdateRequest,
    ReportTemplateCreateRequest,
    ReportTemplateUpdateRequest,
    StatComponentCreateRequest,
    StatComponentUpdateRequest,
)
from app.services.catalog_service import CatalogService

router = APIRouter()


def get_service(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> CatalogService:
    return CatalogService(db, current_user)


@router.get("/templates")
def list_templates(service: CatalogService = Depends(get_service)):
    return ok(service.list_templates())


@router.post("/templates")
def create_template(req: ReportTemplateCreateRequest, service: CatalogService = Depends(get_service)):
    return ok(service.create_template(req))


@router.post("/templates/upload")
async def upload_template(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    description: str = Form(default=""),
    status_value: str = Form(default="enabled", alias="status"),
    service: CatalogService = Depends(get_service),
):
    return ok(await service.upload_template(file, name, description=description, status_value=status_value))


@router.get("/templates/{template_id}/download")
def download_template(template_id: int, service: CatalogService = Depends(get_service)):
    filename, media_type, content = service.download_template(template_id)
    encoded_filename = quote(filename)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@router.get("/templates/{template_id}/content")
def get_template_content(template_id: int, service: CatalogService = Depends(get_service)):
    return ok(service.get_template_content(template_id))


@router.put("/templates/{template_id}")
def update_template(template_id: int, req: ReportTemplateUpdateRequest, service: CatalogService = Depends(get_service)):
    return ok(service.update_template(template_id, req))


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, service: CatalogService = Depends(get_service)):
    return ok(service.delete_template(template_id))


@router.get("/components")
def list_components(service: CatalogService = Depends(get_service)):
    return ok(service.list_components())


@router.post("/components")
def create_component(req: StatComponentCreateRequest, service: CatalogService = Depends(get_service)):
    return ok(service.create_component(req))


@router.put("/components/{component_id}")
def update_component(component_id: int, req: StatComponentUpdateRequest, service: CatalogService = Depends(get_service)):
    return ok(service.update_component(component_id, req))


@router.delete("/components/{component_id}")
def delete_component(component_id: int, service: CatalogService = Depends(get_service)):
    return ok(service.delete_component(component_id))


@router.get("/data-sources")
def list_data_sources(service: CatalogService = Depends(get_service)):
    return ok(service.list_data_sources())


@router.post("/data-sources")
def create_data_source(req: DataSourceCreateRequest, service: CatalogService = Depends(get_service)):
    return ok(service.create_data_source(req))


@router.put("/data-sources/{data_source_id}")
def update_data_source(data_source_id: int, req: DataSourceUpdateRequest, service: CatalogService = Depends(get_service)):
    return ok(service.update_data_source(data_source_id, req))


@router.delete("/data-sources/{data_source_id}")
def delete_data_source(data_source_id: int, service: CatalogService = Depends(get_service)):
    return ok(service.delete_data_source(data_source_id))
