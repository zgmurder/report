from datetime import datetime
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.core.security import CurrentUser
from app.domain.report.sanitizer import sanitize_report_html
from app.schemas.report import ReportContent, ReportDetail, ReportEditorConfig, ReportSection, ReportSaveRequest
from app.services.export_service import ExportService
from app.services.report_service import ReportService


def _content(html: str = "<p>安全正文</p>") -> ReportContent:
    return ReportContent(title="测试报告", type="html", sections=[ReportSection(id="s1", title="正文", type="html", content=html)])


def _detail(*, status: str = "draft", content=None, draft=None, snapshot=None) -> ReportDetail:
    return ReportDetail(
        id=1, title="测试报告", report_type="html", status=status, folder_id=None,
        created_at=datetime.now(), updated_at=datetime.now(), source_query={},
        editor_config=ReportEditorConfig(), content_json=content, draft_json=draft, html_snapshot=snapshot,
    )


def test_sanitizer_removes_active_content_and_dangerous_attributes():
    clean = sanitize_report_html('<script>alert(1)</script><p onclick="x()" style="color:red">ok<a href="javascript:alert(1)" target="_blank">x</a></p>')
    assert "script" not in clean
    assert "onclick" not in clean
    assert "style=" not in clean
    assert "javascript:" not in clean
    assert "noopener noreferrer" in clean


def test_sanitizer_removes_nested_dangerous_subtrees_without_crashing():
    clean = sanitize_report_html(
        "<div><form><style>x{}</style><script>alert(1)</script><input></form><p>safe</p></div>"
    )
    assert clean == "<div><p>safe</p></div>"


def test_draft_save_does_not_promote_content():
    service = ReportService.__new__(ReportService)
    service.repository = Mock()
    service.repository.get.return_value = _detail(status="draft", draft=_content())
    service.repository.save_draft.return_value = _detail(status="draft", draft=_content())
    request = ReportSaveRequest(content_json=_content('<p onclick="bad()">ok</p>'))

    result = service.save_draft(1, request)

    assert result.status == "draft"
    saved = service.repository.save_draft.call_args.args[1]
    assert "onclick" not in (saved.sections[0].content or "")
    service.repository.save_content.assert_not_called()


def test_formal_save_maps_locked_state_conflict():
    from app.repositories.report_repository import ReportStateConflict

    service = ReportService.__new__(ReportService)
    service.repository = Mock()
    service.repository.save_content.side_effect = ReportStateConflict("只有已确认报告可以保存正式内容")
    with pytest.raises(HTTPException) as exc:
        service.save(1, ReportSaveRequest(content_json=_content()))
    assert exc.value.status_code == 409
    service.repository.get.assert_not_called()


def test_export_rejects_draft_and_export_service_never_falls_back_to_draft():
    service = ReportService.__new__(ReportService)
    service.repository = Mock()
    service.repository.get.return_value = _detail(status="draft", draft=_content())
    service.export_service = ExportService()
    with pytest.raises(HTTPException) as exc:
        service.export_html(1)
    assert exc.value.status_code == 409
    rendered = ExportService().render_report_html(_detail(status="draft", draft=_content()))
    assert "暂无报告内容" in rendered


def test_docx_uses_structured_content_not_html_snapshot():
    report = _detail(status="confirmed", content=_content("<p>权威正文</p>"), snapshot="<p>陈旧快照</p>")
    data = ExportService().render_report_docx(report)
    assert data.startswith(b"PK")
    # The generated DOCX package must contain structured content and not the cache.
    import io, zipfile
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    assert "权威正文" in xml
    assert "陈旧快照" not in xml
