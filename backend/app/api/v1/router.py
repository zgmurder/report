from fastapi import APIRouter, Depends

from app.api.v1 import (
    atomic_metric,
    auth,
    catalog,
    departments,
    pi_agent,
    police,
    report_search,
    reports,
    tags,
    tags_v2,
    users,
    warnings,
)
from app.core.security import get_current_user

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(
    police.router,
    prefix="/police-events",
    tags=["police-events"],
    dependencies=[Depends(get_current_user)],
)
api_router.include_router(reports.router, prefix="/reports", tags=["reports"], dependencies=[Depends(get_current_user)])
api_router.include_router(pi_agent.router, prefix="/pi-agent", tags=["pi-agent"], dependencies=[Depends(get_current_user)])
api_router.include_router(report_search.router, prefix="/report-search", tags=["report-search"])
api_router.include_router(
    atomic_metric.router,
    prefix="/atomic-metric",
    tags=["atomic-metric"],
    dependencies=[Depends(get_current_user)],
)
api_router.include_router(tags.router, prefix="/tags", tags=["tags"], dependencies=[Depends(get_current_user)])
api_router.include_router(tags_v2.router, prefix="/tags-v2", tags=["tags-v2"], dependencies=[Depends(get_current_user)])
api_router.include_router(warnings.router, prefix="/warnings", tags=["warnings"], dependencies=[Depends(get_current_user)])
api_router.include_router(catalog.router, prefix="/catalog", tags=["catalog"], dependencies=[Depends(get_current_user)])
api_router.include_router(departments.router, prefix="/departments", tags=["departments"], dependencies=[Depends(get_current_user)])
api_router.include_router(users.router, prefix="/users", tags=["users"], dependencies=[Depends(get_current_user)])
