from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.repositories.report_repository import ReportRepository, ReportStateConflict
from app.schemas.report import ReportContent, ReportSection


def _content():
    return ReportContent(title="报告", type="html", sections=[ReportSection(id="1", title="正文", content="ok")])


def _repo_with_row(status: str, *, draft=None):
    db = Mock()
    db.scalar.return_value = SimpleNamespace(status=status, draft_json=draft)
    return ReportRepository(db, 7), db


@pytest.mark.parametrize("method,status", [("save_draft", "confirmed"), ("save_content", "draft"), ("confirm_draft", "confirmed")])
def test_state_writes_lock_before_rechecking(method, status):
    repository, db = _repo_with_row(status, draft=_content().model_dump(mode="json"))
    with pytest.raises(ReportStateConflict):
        if method == "confirm_draft":
            repository.confirm_draft(1, lambda value: value)
        else:
            getattr(repository, method)(1, _content())
    statement = db.scalar.call_args.args[0]
    assert statement._for_update_arg is not None
    db.rollback.assert_called_once()


def test_update_rejects_confirmed_to_draft_under_lock():
    repository, db = _repo_with_row("confirmed")
    with pytest.raises(ReportStateConflict):
        repository.update(1, status="draft")
    assert db.scalar.call_args.args[0]._for_update_arg is not None


def test_update_allows_only_confirmed_to_archived_transition():
    repository, db = _repo_with_row("draft")
    with pytest.raises(ReportStateConflict):
        repository.update(1, status="archived")
    db.rollback.assert_called_once()
