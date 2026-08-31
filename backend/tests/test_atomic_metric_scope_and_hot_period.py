from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.atomic_metric import _apply_dept_scope
from app.core.security import CurrentUser
from app.schemas.atomic_metric import AtomicMetricQueryRequest
from app.services.atomic_metric_service import AtomicMetricService


def _user(*, roles=None, unit_code=None):
    return CurrentUser(
        id=1,
        username="tester",
        display_name="Tester",
        roles=roles or ["user"],
        unit_code=unit_code,
    )


def test_atomic_metric_dept_scope_overrides_body_and_nested_params():
    body = AtomicMetricQueryRequest(
        dept_code="OTHER",
        params={"dept_code": "OTHER", "deptCode": "OTHER", "date_start": "2026-01-01"},
    )

    scoped = _apply_dept_scope(body, _user(unit_code="330782010000"))

    assert scoped.dept_code == "330782010000"
    assert scoped.params["dept_code"] == "330782010000"
    assert scoped.params["deptCode"] == "330782010000"
    assert scoped.params["date_start"] == "2026-01-01"


def test_atomic_metric_dept_scope_fails_closed_without_user_department():
    with pytest.raises(HTTPException) as exc:
        _apply_dept_scope(AtomicMetricQueryRequest(), _user(unit_code=None))

    assert exc.value.status_code == 403


def test_atomic_metric_city_scope_can_override_department():
    body = AtomicMetricQueryRequest(dept_code="330782020000", params={"deptCode": "330782030000"})

    assert _apply_dept_scope(body, _user(unit_code="330782000000")) is body


def test_atomic_metric_admin_can_override_department():
    body = AtomicMetricQueryRequest(dept_code="330782020000", params={"deptCode": "330782030000"})

    assert _apply_dept_scope(body, _user(roles=["admin"], unit_code=None)) is body


def test_hot_period_reuses_classification_values_and_only_queries_requested_comparison():
    fetch_calls = []

    def fake_fetch_rows(db, sql, bind, **kwargs):
        fetch_calls.append((sql, dict(bind)))
        if "slot_start" in sql:
            return [{"slot_start": 8, "slot_end": 10, "total": 3}]
        return [{"total": 5}]

    body = AtomicMetricQueryRequest(
        data_source="fkd_fkd",
        dept_code="330782010000",
        date_start="2026-06-01",
        date_end="2026-06-07",
        category_code="CAT-1",
        include_hot_period=True,
        include_mom=True,
    )

    with (
        patch("app.services.atomic_metric_service.ComponentSqlExecutor.fetch_rows", side_effect=fake_fetch_rows),
        patch("app.services.atomic_metric_service.DataSourceDao.get_by_code", return_value=None),
    ):
        result = AtomicMetricService.query(Mock(), body)

    hot_calls = [(sql, bind) for sql, bind in fetch_calls if "slot_start" in sql]
    assert len(hot_calls) == 2  # current + mom; no unnecessary yoy query
    assert all(bind["ajlb"] == "CAT-1" for _, bind in hot_calls)
    assert all(bind["dept_code"] == "330782010000" for _, bind in hot_calls)
    assert result.hot_periods


def test_hot_period_yoy_sort_queries_yoy_only_and_avoids_top_n_sql_limit():
    fetch_calls = []

    def fake_fetch_rows(db, sql, bind, **kwargs):
        fetch_calls.append((sql, dict(bind)))
        if "slot_start" in sql:
            return [{"slot_start": 8, "slot_end": 10, "total": 3}]
        return [{"total": 5}]

    body = AtomicMetricQueryRequest(
        data_source="fkd_fkd",
        dept_code="330782010000",
        date_start="2026-06-01",
        date_end="2026-06-07",
        include_hot_period=True,
        rank_sort_by="yoy",
        yoy_trend_top_n=3,
    )

    with (
        patch("app.services.atomic_metric_service.ComponentSqlExecutor.fetch_rows", side_effect=fake_fetch_rows),
        patch("app.services.atomic_metric_service.DataSourceDao.get_by_code", return_value=None),
    ):
        AtomicMetricService.query(Mock(), body)

    hot_calls = [(sql, bind) for sql, bind in fetch_calls if "slot_start" in sql]
    assert len(hot_calls) == 2  # current + yoy; no unnecessary mom query
    assert all("LIMIT 500" in sql for sql, _ in hot_calls)
