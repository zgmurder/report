from unittest.mock import Mock

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import CurrentUser
from app.domain.atomic_metric.exceptions import ServiceException
from app.schemas.tag_v2 import IntelligenceTagV2VerifyModel
from app.services.tag_v2_service import TagV2Service


def test_verify_rolls_back_unique_conflict_as_409(monkeypatch):
    db = Mock()
    alarm = {"fkdbh": "FK-1", "jqqh": None, "bjsj": None}
    repository = Mock()
    repository.get_scoped_alarm.return_value = alarm
    monkeypatch.setattr("app.services.tag_v2_service.TagV2Repository", lambda _db: repository)
    empty_result = Mock()
    empty_result.scalars.return_value.all.return_value = []
    db.execute.return_value = empty_result
    db.flush.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    body = IntelligenceTagV2VerifyModel(fkdbh="FK-1", tag_paths=[])
    user = CurrentUser(id=1, username="user", display_name="用户", roles=["user"])

    with pytest.raises(ServiceException) as exc:
        TagV2Service.verify_alarm(db, body, user)

    assert exc.value.code == 409
    db.rollback.assert_called_once()
    repository.get_scoped_alarm.assert_called_once()
    assert repository.get_scoped_alarm.call_args.kwargs["for_update"] is True
