from unittest.mock import Mock

from app.domain.warning.dept_data_scope import DeptDataScope
from app.repositories.tag_v2_repository import TagV2Repository


def test_scoped_alarm_query_contains_department_filter():
    db = Mock()
    result = Mock()
    result.mappings.return_value.first.return_value = None
    db.execute.return_value = result
    repository = TagV2Repository(db)

    repository.get_scoped_alarm("FK-1", DeptDataScope(False, dept_code="330782010000", dept_name="稠城派出所"), full=True)

    statement, params = db.execute.call_args.args
    sql = str(statement)
    assert "f.`fkdwdm`" in sql
    assert "f.`fkdwmc`" in sql
    assert params["fkdbh"] == "FK-1"
    assert params["scope_code8"] == "33078201"


def test_unscoped_alarm_query_for_admin_has_no_scope_params():
    db = Mock()
    result = Mock()
    result.mappings.return_value.first.return_value = None
    db.execute.return_value = result
    TagV2Repository(db).get_scoped_alarm("FK-1", DeptDataScope(True), full=False)
    _, params = db.execute.call_args.args
    assert params == {"fkdbh": "FK-1"}


def test_scoped_alarm_uses_first_eight_digits_and_can_lock():
    db = Mock()
    result = Mock()
    result.mappings.return_value.first.return_value = None
    db.execute.return_value = result
    TagV2Repository(db).get_scoped_alarm(
        "FK-1",
        DeptDataScope(False, dept_code="330782010000", dept_name="稠城派出所"),
        full=False,
        for_update=True,
    )
    statement, params = db.execute.call_args.args
    sql = str(statement)
    assert "LEFT(TRIM(COALESCE(f.`fkdwdm`, '')), 8)" in sql
    assert "FOR UPDATE" in sql
    assert params["scope_code8"] == "33078201"
