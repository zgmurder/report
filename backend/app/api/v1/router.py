from fastapi import APIRouter

from app.api.v1 import auth, police, reports

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(police.router, prefix="/police-events", tags=["police-events"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
