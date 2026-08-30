from app.domain.report.sanitizer import sanitize_report_html
from app.schemas.report import ReportContent


def validate_report_content(content: ReportContent) -> ReportContent:
    """Validate and sanitize the structured report authority before persistence/export."""
    section_ids = [section.id for section in content.sections]
    if len(section_ids) != len(set(section_ids)):
        raise ValueError("报告章节 id 不能重复")
    clean = content.model_copy(deep=True)
    for section in clean.sections:
        if section.type == "html" and section.content:
            section.content = sanitize_report_html(section.content)
    return clean
