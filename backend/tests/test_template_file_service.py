import io
import zipfile

import pytest
from fastapi import HTTPException

from app.services.template_file_service import TemplateFileService


def _zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in entries.items():
            archive.writestr(name, value)
    return buffer.getvalue()


def test_validate_docx_accepts_required_entries():
    TemplateFileService._validate_docx(_zip({"[Content_Types].xml": b"x", "word/document.xml": b"x"}))


@pytest.mark.parametrize("content", [b"not-a-zip", _zip({"word/document.xml": b"x"})])
def test_validate_docx_rejects_fake_or_incomplete_files(content):
    with pytest.raises(HTTPException) as exc:
        TemplateFileService._validate_docx(content)
    assert exc.value.status_code == 422


def test_validate_docx_rejects_zip_bomb_size(monkeypatch):
    monkeypatch.setattr("app.services.template_file_service.MAX_ZIP_ENTRY_SIZE", 10)
    content = _zip({"[Content_Types].xml": b"x", "word/document.xml": b"01234567890"})
    with pytest.raises(HTTPException, match="单个解压条目过大"):
        TemplateFileService._validate_docx(content)


def test_read_rejects_path_outside_storage(tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()
    malicious = tmp_path / "outside.docx"
    malicious.write_bytes(_zip({"[Content_Types].xml": b"x", "word/document.xml": b"x"}))
    service = TemplateFileService(storage)
    with pytest.raises(HTTPException, match="超出存储目录"):
        service.read(str(malicious))


def test_delete_rejects_historical_malicious_absolute_path(tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()
    malicious = tmp_path / "outside.docx"
    malicious.write_bytes(b"do-not-delete")
    service = TemplateFileService(storage)
    with pytest.raises(HTTPException, match="超出存储目录"):
        service.delete(str(malicious))
    assert malicious.exists()


def test_read_revalidates_historical_docx(tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()
    invalid = storage / "old.docx"
    invalid.write_bytes(b"not-a-docx")
    with pytest.raises(HTTPException) as exc:
        TemplateFileService(storage).read(str(invalid))
    assert exc.value.status_code == 422
