from fastapi import APIRouter, Depends

from app.api.v1 import auth, catalog, departments, police, report_search, reports, users
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
api_router.include_router(report_search.router, prefix="/report-search", tags=["report-search"])
api_router.include_router(catalog.router, prefix="/catalog", tags=["catalog"], dependencies=[Depends(get_current_user)])
api_router.include_router(departments.router, prefix="/departments", tags=["departments"], dependencies=[Depends(get_current_user)])
api_router.include_router(users.router, prefix="/users", tags=["users"], dependencies=[Depends(get_current_user)])
