from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.response import ok
from app.core.security import CurrentUser, get_current_user, is_admin
from app.domain.atomic_metric.exceptions import ServiceException
from app.domain.warning.dept_data_scope import resolve_dept_data_scope
from app.schemas.atomic_metric import AtomicMetricQueryRequest
from app.services.atomic_metric_service import AtomicMetricService

router = APIRouter()


def _apply_dept_scope(
    body: AtomicMetricQueryRequest,
    current_user: CurrentUser,
    db: Session | None = None,
) -> AtomicMetricQueryRequest:
    """按统一数据范围解析结果覆盖非全局账号的请求部门。"""
    scope = resolve_dept_data_scope(current_user, db)
    if scope.unrestricted:
        return body

    dept_code = scope.dept_code.strip()
    if not dept_code:
        raise HTTPException(status_code=403, detail="当前账号没有有效数据范围，无法查询警情指标")

    params = dict(body.params or {})
    params["dept_code"] = dept_code
    params["deptCode"] = dept_code
    return body.model_copy(update={"dept_code": dept_code, "params": params})


@router.post("/query")
def query_atomic_metric(
    body: AtomicMetricQueryRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    body = _apply_dept_scope(body, current_user, db)
    try:
        result = AtomicMetricService.query(db, body)
    except ServiceException as exc:
        raise HTTPException(status_code=exc.code if 400 <= exc.code < 600 else 400, detail=exc.message) from exc
    if get_settings().app_env.strip().lower() not in {"dev", "test"} and not is_admin(current_user):
        result = result.model_copy(update={"executed_sql": None})
    return ok(result)
