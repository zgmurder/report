from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.schemas.department import DepartmentCreateRequest, DepartmentUpdateRequest
from app.services.department_service import DepartmentService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> DepartmentService:
    return DepartmentService(db)


@router.get("")
def list_departments(include_disabled: bool = False, service: DepartmentService = Depends(get_service)):
    return ok(service.list(include_disabled=include_disabled))


@router.get("/tree")
def department_tree(include_disabled: bool = False, service: DepartmentService = Depends(get_service)):
    return ok(service.tree(include_disabled=include_disabled))


@router.post("")
def create_department(req: DepartmentCreateRequest, service: DepartmentService = Depends(get_service)):
    return ok(service.create(req))


@router.put("/{department_id}")
def update_department(department_id: int, req: DepartmentUpdateRequest, service: DepartmentService = Depends(get_service)):
    return ok(service.update(department_id, req))


@router.delete("/{department_id}")
def delete_department(department_id: int, service: DepartmentService = Depends(get_service)):
    return ok(service.delete(department_id))
