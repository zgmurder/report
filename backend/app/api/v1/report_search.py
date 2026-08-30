from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.core.security import CurrentUser, get_current_user
from app.repositories.report_search_repository import ReportSearchRepository
from app.schemas.report_search import ReportSearchBatchRequest, ReportSearchQuery, StatisticsDictionaryConfigUpdate
from app.services.report_search_service import ReportSearchService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> ReportSearchService:
    return ReportSearchService(ReportSearchRepository(db))


@router.get("/options")
def search_options(
    current_user: CurrentUser = Depends(get_current_user),
    service: ReportSearchService = Depends(get_service),
):
    return ok(service.options(current_user))


@router.get("/dictionary-config")
def dictionary_config(
    current_user: CurrentUser = Depends(get_current_user),
    service: ReportSearchService = Depends(get_service),
):
    return ok(service.dictionary_config(current_user))


@router.put("/dictionary-config")
def update_dictionary_config(
    request: StatisticsDictionaryConfigUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ReportSearchService = Depends(get_service),
):
    return ok(service.update_dictionary_config(request, current_user))


@router.get("/classifications")
def search_classifications(
    source: str = Query(default="jjd_jjd"),
    level: str = Query(default="category"),
    parent_code: str | None = Query(default=None),
    service: ReportSearchService = Depends(get_service),
):
    return ok(service.classifications(source, level, parent_code))


@router.get("/metrics")
def search_metrics(
    source: str = Query(default="jjd_jjd"),
    service: ReportSearchService = Depends(get_service),
):
    return ok(service.metrics(source))


@router.post("/batch-query")
def execute_batch_search(
    request: ReportSearchBatchRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: ReportSearchService = Depends(get_service),
):
    return ok(service.batch_query(request, current_user))


@router.post("/query")
def execute_search(
    request: ReportSearchQuery,
    current_user: CurrentUser = Depends(get_current_user),
    service: ReportSearchService = Depends(get_service),
):
    return ok(service.query(request, current_user))
