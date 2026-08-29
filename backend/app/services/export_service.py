from html import escape

from app.schemas.report import ReportContent, ReportDetail, ReportSection


class ExportService:
    """报告派生产物导出服务。

    content_json 是权威数据；HTML 只是派生产物，供预览/导出使用。
    """

    def render_report_html(self, report: ReportDetail) -> str:
        content = report.content_json or report.draft_json
        if not content:
            return self._html_document(report.title, "<p class=\"empty\">暂无报告内容。</p>")
        body = self._render_content(content)
        return self._html_document(content.title or report.title, body)

    def _render_content(self, content: ReportContent) -> str:
        sections = "".join(self._render_section(section) for section in content.sections)
        return f"<h1>{escape(content.title)}</h1>{sections}"

    def _render_section(self, section: ReportSection) -> str:
        content = section.content or ""
        if section.type == "html":
            section_body = content
        else:
            section_body = f"<p>{escape(content)}</p>" if content else ""
        source = ""
        if section.source:
            source = f"<p class=\"source\">来源：{escape(', '.join(section.source))}</p>"
        ai_badge = "<span class=\"badge\">AI 草稿</span>" if section.ai_generated else ""
        return f"<section><h2>{escape(section.title)}{ai_badge}</h2>{section_body}{source}</section>"

    def _html_document(self, title: str, body: str) -> str:
        return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <title>{escape(title)}</title>
  <style>
    body {{ margin: 0; background: #f5f7fb; color: #1f2a3d; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; }}
    main {{ max-width: 920px; margin: 32px auto; padding: 48px 64px; background: #fff; border-radius: 18px; box-shadow: 0 18px 50px rgba(34, 75, 130, .12); }}
    h1 {{ margin: 0 0 28px; text-align: center; font-size: 28px; }}
    h2 {{ margin: 28px 0 12px; font-size: 20px; color: #123b78; }}
    p {{ line-height: 1.9; font-size: 16px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
    th, td {{ border: 1px solid #d8e2ef; padding: 9px 11px; text-align: left; }}
    th {{ background: #eef5ff; }}
    .badge {{ margin-left: 8px; font-size: 12px; color: #2878ff; background: #eaf3ff; border-radius: 999px; padding: 2px 8px; }}
    .source, .empty {{ color: #7b8aa3; font-size: 13px; }}
  </style>
</head>
<body><main>{body}</main></body>
</html>"""
