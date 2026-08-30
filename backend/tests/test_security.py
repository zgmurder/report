import pytest
from fastapi import HTTPException

from app.core.security import CurrentUser, require_admin


def make_user(*roles: str) -> CurrentUser:
    return CurrentUser(id=1, username="tester", display_name="测试用户", roles=list(roles))


def test_require_admin_rejects_regular_user():
    with pytest.raises(HTTPException) as exc_info:
        require_admin(make_user("user"))

    assert exc_info.value.status_code == 403


def test_require_admin_allows_admin():
    user = make_user("user", "admin")

    assert require_admin(user) is user
