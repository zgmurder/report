from app.schemas.report import ReportContent


def validate_report_content(content: ReportContent) -> ReportContent:
    """校验报告结构化内容。

    Pydantic 已完成基础结构校验；这里保留业务校验入口，例如章节白名单、数据源权限、敏感词等。
    """
    section_ids = [section.id for section in content.sections]
    if len(section_ids) != len(set(section_ids)):
        raise ValueError("报告章节 id 不能重复")
    return content
