from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.schemas.police import PoliceEventQuery
from app.services.police_service import PoliceService

router = APIRouter()


@router.post("/search")
def search_events(query: PoliceEventQuery, db: Session = Depends(get_db)):
    return ok(PoliceService(db).list_events(query))


@router.post("/overview")
def overview(query: PoliceEventQuery, db: Session = Depends(get_db)):
    return ok(PoliceService(db).overview(query))
