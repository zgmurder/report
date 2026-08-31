from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.security import CurrentUser
from app.services.catalog_service import CatalogService
from app.services.template_file_service import TemplateFileService


def _admin() -> CurrentUser:
    return CurrentUser(id=1, username="admin", display_name="Admin", roles=["admin"])


def _service(repository, files) -> CatalogService:
    service = CatalogService.__new__(CatalogService)
    service.current_user = _admin()
    service.repository = repository
    service.template_files = files
    return service


def test_template_file_recycle_can_restore_after_database_failure(tmp_path):
    storage = tmp_path / "templates"
    storage.mkdir()
    original = storage / "template.docx"
    original.write_bytes(b"content")
    files = TemplateFileService(storage)

    receipt = files.recycle(str(original))
    assert receipt is not None
    assert not original.exists()
    assert receipt[1].exists()

    files.restore_recycled(receipt)
    assert original.read_bytes() == b"content"
    assert not receipt[1].exists()


def test_delete_template_restores_file_when_repository_delete_fails(tmp_path):
    storage = tmp_path / "templates"
    storage.mkdir()
    original = storage / "template.docx"
    original.write_bytes(b"content")
    row = SimpleNamespace(id=2, file_path=str(original))

    class Repository:
        def get_template(self, template_id, user_id):
            return row

        def delete_template(self, template_id, user_id):
            raise RuntimeError("database commit failed")

    service = _service(Repository(), TemplateFileService(storage))

    with pytest.raises(RuntimeError, match="database commit failed"):
        service.delete_template(2)

    assert original.read_bytes() == b"content"
    assert not list((storage / ".recycle").glob("*"))


def test_delete_template_commits_then_purges_recycled_file(tmp_path):
    storage = tmp_path / "templates"
    storage.mkdir()
    original = storage / "template.docx"
    original.write_bytes(b"content")
    row = SimpleNamespace(id=2, file_path=str(original))

    class Repository:
        def get_template(self, template_id, user_id):
            return row

        def delete_template(self, template_id, user_id):
            return row

    service = _service(Repository(), TemplateFileService(storage))

    assert service.delete_template(2) == {"deleted": True}
    assert not original.exists()
    assert not list((storage / ".recycle").glob("*"))
