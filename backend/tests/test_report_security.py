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
    clean = sanitize_report_html('<script>alert(1)</script><p onclick="x()" style="color:red;position:fixed;background:url(javascript:alert(1))">ok<a href="javascript:alert(1)" target="_blank">x</a></p>')
    assert "script" not in clean
    assert "onclick" not in clean
    assert 'style="color:red"' in clean
    assert "position" not in clean
    assert "url(" not in clean
    assert "javascript:" not in clean
    assert "noopener noreferrer" in clean


def test_sanitizer_preserves_export_formatting_css_allowlist():
    clean = sanitize_report_html(
        '<p style="text-align:center;margin-left:1.20cm;line-height:1.50;break-before:page">'
        '<span style="font-family:Microsoft YaHei;font-size:16pt;color:#123456;'
        'background-color:rgb(240, 240, 240);text-decoration:underline">正文</span></p>'
    )
    assert "text-align:center" in clean
    assert "margin-left:1.20cm" in clean
    assert "line-height:1.50" in clean
    assert "break-before:page" in clean
    assert "font-family:Microsoft YaHei" in clean
    assert "font-size:16pt" in clean
    assert "color:#123456" in clean
    assert "background-color:rgb(240, 240, 240)" in clean
    assert "text-decoration:underline" in clean


def test_sanitizer_rejects_css_escape_and_active_value_payloads():
    clean = sanitize_report_html(
        '<span style="color:expression(alert(1));font-family:Arial\\;position:fixed;'
        'width:calc(100%);border:1px solid #000">safe</span>'
    )
    assert "expression" not in clean
    assert "position" not in clean
    assert "calc(" not in clean
    assert "font-family" not in clean
    assert "border:1px solid #000" in clean


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


def test_archived_report_remains_exportable():
    service = ReportService.__new__(ReportService)
    service.repository = Mock()
    service.repository.get.return_value = _detail(status="archived", content=_content())
    service.export_service = ExportService()

    assert "安全正文" in service.export_html(1)


def test_html_and_docx_exports_preserve_sanitized_inline_styles():
    report = _detail(
        status="confirmed",
        content=_content('<p style="text-align:center"><span style="font-size:18pt;color:#123456">样式正文</span></p>'),
    )
    rendered = ExportService().render_report_html(report)
    assert 'style="text-align:center"' in rendered
    assert "font-size:18pt;color:#123456" in rendered

    import io, zipfile
    data = ExportService().render_report_docx(report)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    assert 'w:jc w:val="center"' in xml
    assert 'w:sz w:val="36"' in xml
    assert 'w:color w:val="123456"' in xml


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
