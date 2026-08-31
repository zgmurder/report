from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from sqlalchemy import UniqueConstraint

from app.core import database
from app.models.intelligence import JqTagResult

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_startup_database_initialization_has_no_drop_statements():
    source = (BACKEND_ROOT / "app/core/database.py").read_text(encoding="utf-8").upper()
    assert "DROP TABLE" not in source
    assert "DROP INDEX" not in source


def test_configured_admin_owner_selection_is_fail_safe(monkeypatch):
    monkeypatch.setattr(database, "get_settings", lambda: SimpleNamespace(admin_username="configured-admin"))
    result = Mock()
    result.scalar.return_value = None
    conn = Mock()
    conn.execute.return_value = result

    assert database._configured_admin_id(conn) is None
    sql, params = conn.execute.call_args.args
    rendered = str(sql)
    assert "username = :username" in rendered
    assert "ORDER BY id" not in rendered
    assert params == {"username": "configured-admin"}


def test_startup_preserves_unowned_statistics_exclusions():
    source = (BACKEND_ROOT / "app/core/database.py").read_text(encoding="utf-8").upper()
    assert "DELETE FROM {DICT_TABLE} WHERE CREATED_BY IS NULL" not in source


def test_jq_tag_result_orm_and_canonical_sql_share_unique_constraint():
    constraints = {
        constraint.name
        for constraint in JqTagResult.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_jq_tag_result_fkdbh_tag_path" in constraints

    canonical_sql = (BACKEND_ROOT / "sql/intelligence/tag_dict_v2.sql").read_text(encoding="utf-8")
    migration_sql = (BACKEND_ROOT / "sql/202603_tag_result_unique.sql").read_text(encoding="utf-8")
    expected = "uq_jq_tag_result_fkdbh_tag_path"
    assert expected in canonical_sql
    assert expected in migration_sql
