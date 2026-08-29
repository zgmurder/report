from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.services.catalog_service import CatalogService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> CatalogService:
    return CatalogService(db)


@router.get("/templates")
def list_templates(service: CatalogService = Depends(get_service)):
    return ok(service.list_templates())


@router.get("/components")
def list_components(service: CatalogService = Depends(get_service)):
    return ok(service.list_components())


@router.get("/data-sources")
def list_data_sources(service: CatalogService = Depends(get_service)):
    return ok(service.list_data_sources())
