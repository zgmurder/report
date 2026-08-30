from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.core.security import CurrentUser, get_current_user
from app.domain.atomic_metric.exceptions import ServiceException
from app.schemas.atomic_metric import AtomicMetricQueryRequest
from app.services.atomic_metric_service import AtomicMetricService

router = APIRouter()


@router.post("/query")
def query_atomic_metric(
    body: AtomicMetricQueryRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.dept_code and current_user.unit_code:
        body = body.model_copy(update={"dept_code": current_user.unit_code})
    try:
        result = AtomicMetricService.query(db, body)
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc
    return ok(result)
