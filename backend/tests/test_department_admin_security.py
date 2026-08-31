from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.departments import router as department_router
from app.core.security import CurrentUser, require_admin
from app.schemas.department import DepartmentCreateRequest, DepartmentUpdateRequest
from app.services.department_service import DepartmentService


def _user(*roles: str) -> CurrentUser:
    return CurrentUser(id=9, username="tester", display_name="Tester", roles=list(roles))


def _service(user: CurrentUser) -> DepartmentService:
    service = DepartmentService.__new__(DepartmentService)
    service.current_user = user
    return service


def _route(path: str, method: str):
    return next(route for route in department_router.routes if route.path == path and method in route.methods)


@pytest.mark.parametrize(
    ("path", "method"),
    [("", "POST"), ("/{department_id}", "PUT"), ("/{department_id}", "DELETE")],
)
def test_department_mutation_routes_require_admin(path, method):
    route = _route(path, method)
    assert any(dependency.call is require_admin for dependency in route.dependant.dependencies)


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
def test_department_service_rejects_non_admin_before_repository(operation):
    service = _service(_user("user"))
    service.repository = SimpleNamespace(
        create=lambda req: pytest.fail("repository must not be called"),
        update=lambda department_id, req: pytest.fail("repository must not be called"),
        delete=lambda department_id: pytest.fail("repository must not be called"),
    )

    with pytest.raises(HTTPException) as exc:
        if operation == "create":
            service.create(DepartmentCreateRequest(name="新部门", code="330782990000"))
        elif operation == "update":
            service.update(1, DepartmentUpdateRequest(name="新名称"))
        else:
            service.delete(1)

    assert exc.value.status_code == 403


def test_department_service_allows_admin_mutation():
    service = _service(_user("admin"))
    service.repository = SimpleNamespace(delete=lambda department_id: department_id == 1)

    assert service.delete(1) == {"deleted": True}
