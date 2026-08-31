from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.catalog import router as catalog_router
from app.core.security import CurrentUser, require_admin
from app.schemas.catalog import DataSourceUpdateRequest, StatComponentCreateRequest
from app.services.catalog_service import CatalogService, SECRET_PLACEHOLDER


def _user(*roles: str) -> CurrentUser:
    return CurrentUser(id=7, username="tester", display_name="Tester", roles=list(roles))


def _service(user: CurrentUser) -> CatalogService:
    service = CatalogService.__new__(CatalogService)
    service.current_user = user
    return service


def _route(path: str, method: str):
    return next(route for route in catalog_router.routes if route.path == path and method in route.methods)


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/components", "POST"),
        ("/components/{component_id}", "PUT"),
        ("/components/{component_id}", "DELETE"),
        ("/data-sources", "GET"),
        ("/data-sources", "POST"),
        ("/data-sources/{data_source_id}", "PUT"),
        ("/data-sources/{data_source_id}", "DELETE"),
    ],
)
def test_catalog_mutation_routes_require_admin(path, method):
    route = _route(path, method)
    assert any(dependency.call is require_admin for dependency in route.dependant.dependencies)


def test_catalog_service_rejects_non_admin_even_if_called_directly():
    service = _service(_user("user"))
    service.repository = SimpleNamespace(
        create_component=lambda data: pytest.fail("repository must not be called"),
        list_data_sources=lambda: pytest.fail("repository must not be called"),
    )

    with pytest.raises(HTTPException) as exc:
        service.create_component(StatComponentCreateRequest(name="组件"))
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        service.list_data_sources()
    assert exc.value.status_code == 403


def test_data_source_redaction_is_recursive_and_does_not_mutate_model():
    raw_config = {
        "username": "report",
        "password": "db-password",
        "nested": {"apiToken": "token-value", "port": 3306},
        "replicas": [{"private-key": "key-value", "host": "db-2"}],
    }
    row = SimpleNamespace(
        id=1,
        name="source",
        source_type="mysql",
        address="db:3306",
        description="",
        config_json=raw_config,
        status="enabled",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    item = CatalogService._data_source_item(row)

    assert item.config_json == {
        "username": "report",
        "password": SECRET_PLACEHOLDER,
        "nested": {"apiToken": SECRET_PLACEHOLDER, "port": 3306},
        "replicas": [{"private-key": SECRET_PLACEHOLDER, "host": "db-2"}],
    }
    assert raw_config["password"] == "db-password"


def test_data_source_update_preserves_recursive_secret_placeholders():
    existing = SimpleNamespace(
        config_json={
            "password": "old-password",
            "nested": {"api_token": "old-token", "keep": "old"},
            "replicas": [{"secret": "replica-secret", "host": "old-host"}],
        }
    )
    captured = {}
    updated = SimpleNamespace(
        id=3,
        name="source",
        source_type="mysql",
        address="db:3306",
        description="",
        config_json={},
        status="enabled",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    def update(_data_source_id, data):
        captured.update(data)
        updated.config_json = data["config_json"]
        return updated

    service = _service(_user("ADMIN"))
    service.repository = SimpleNamespace(
        get_data_source=lambda _data_source_id: existing,
        update_data_source=update,
    )
    req = DataSourceUpdateRequest(
        config_json={
            "password": SECRET_PLACEHOLDER,
            "nested": {"api_token": SECRET_PLACEHOLDER, "keep": "new"},
            "replicas": [{"secret": SECRET_PLACEHOLDER, "host": "new-host"}],
        }
    )

    result = service.update_data_source(3, req)

    assert captured["config_json"] == {
        "password": "old-password",
        "nested": {"api_token": "old-token", "keep": "new"},
        "replicas": [{"secret": "replica-secret", "host": "new-host"}],
    }
    assert result.config_json["password"] == SECRET_PLACEHOLDER
    assert result.config_json["nested"]["api_token"] == SECRET_PLACEHOLDER
