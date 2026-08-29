from html import escape
from io import BytesIO

from bs4 import BeautifulSoup, NavigableString, Tag
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from app.schemas.report import ReportContent, ReportDetail, ReportEditorConfig, ReportSection


class ExportService:
    """报告派生产物导出服务。

    content_json 是权威数据；HTML 只是派生产物，供预览/导出使用。
    """

    def render_report_html(self, report: ReportDetail) -> str:
        content = report.content_json or report.draft_json
        if not content:
            return self._html_document(report.title, "<p class=\"empty\">暂无报告内容。</p>", report.editor_config)
        body = self._render_content(content)
        return self._html_document(content.title or report.title, body, report.editor_config)

    def render_report_docx(self, report: ReportDetail) -> bytes:
        content = report.content_json or report.draft_json
        document = Document()
        self._configure_docx_page(document, report.editor_config)
        styles = document.styles
        styles["Normal"].font.name = "Microsoft YaHei"
        styles["Normal"].font.size = Pt(10.5)

        if report.html_snapshot:
            self._append_html_to_docx(document, report.html_snapshot)
        elif content:
            for section in content.sections:
                if section.type == "html":
                    self._append_html_to_docx(document, section.content or "")
                else:
                    document.add_heading(section.title, level=2)
                    if section.content:
                        document.add_paragraph(section.content)
        else:
            document.add_heading(report.title, level=1)
            document.add_paragraph("暂无报告内容。")

        buffer = BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    def _configure_docx_page(self, document: Document, editor_config: ReportEditorConfig) -> None:
        page = editor_config.page
        section = document.sections[0]
        if page.size and page.size.width and page.size.height:
            width = Cm(page.size.width)
            height = Cm(page.size.height)
            if page.orientation == "landscape":
                width, height = max(width, height), min(width, height)
            else:
                width, height = min(width, height), max(width, height)
            section.page_width = width
            section.page_height = height
        elif page.orientation == "landscape":
            section.page_width, section.page_height = section.page_height, section.page_width
        if page.orientation == "landscape":
            section.orientation = WD_ORIENT.LANDSCAPE
        section.top_margin = Cm(page.margin.top)
        section.bottom_margin = Cm(page.margin.bottom)
        section.left_margin = Cm(page.margin.left)
        section.right_margin = Cm(page.margin.right)

    def _append_html_to_docx(self, document: Document, html: str) -> None:
        soup = BeautifulSoup(html, "html.parser")
        root = soup.body or soup
        for node in root.children:
            if isinstance(node, NavigableString):
                text = str(node).strip()
                if text:
                    document.add_paragraph(text)
                continue
            if not isinstance(node, Tag):
                continue
            self._append_html_node(document, node)

    def _append_html_node(self, document: Document, node: Tag) -> None:
        name = node.name.lower()
        text = node.get_text(" ", strip=True)
        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            paragraph = document.add_heading(text, level=min(int(name[1]), 6))
            if name == "h1":
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            return
        if name in {"ul", "ol"}:
            style = "List Bullet" if name == "ul" else "List Number"
            for item in node.find_all("li", recursive=False):
                document.add_paragraph(item.get_text(" ", strip=True), style=style)
            return
        if name == "table":
            rows = node.find_all("tr")
            column_count = max((len(row.find_all(["th", "td"], recursive=False)) for row in rows), default=0)
            if not rows or not column_count:
                return
            table = document.add_table(rows=len(rows), cols=column_count)
            table.style = "Table Grid"
            for row_index, row in enumerate(rows):
                cells = row.find_all(["th", "td"], recursive=False)
                for column_index, cell in enumerate(cells):
                    table.cell(row_index, column_index).text = cell.get_text(" ", strip=True)
            return
        if name in {"p", "blockquote", "pre"}:
            document.add_paragraph(text)
            return
        for child in node.children:
            if isinstance(child, Tag):
                self._append_html_node(document, child)

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

    def _html_document(self, title: str, body: str, editor_config: ReportEditorConfig | None = None) -> str:
        page = editor_config.page if editor_config else None
        orientation = page.orientation if page else "portrait"
        if page and page.size and page.size.width and page.size.height:
            width, height = page.size.width, page.size.height
            if orientation == "landscape":
                width, height = max(width, height), min(width, height)
            else:
                width, height = min(width, height), max(width, height)
            page_size = f"{width}cm {height}cm"
        else:
            page_size = f"A4 {orientation}"
        margins = page.margin if page else None
        page_margin = (
            f"{margins.top}cm {margins.right}cm {margins.bottom}cm {margins.left}cm"
            if margins
            else "2.54cm"
        )
        main_width = "1180px" if orientation == "landscape" else "920px"
        return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <title>{escape(title)}</title>
  <style>
    @page {{ size: {page_size}; margin: {page_margin}; }}
    body {{ margin: 0; background: #f5f7fb; color: #1f2a3d; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; }}
    main {{ max-width: {main_width}; margin: 32px auto; padding: 48px 64px; background: #fff; border-radius: 18px; box-shadow: 0 18px 50px rgba(34, 75, 130, .12); }}
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
