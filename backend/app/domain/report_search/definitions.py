from dataclasses import dataclass


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    label: str
    expression: str
    result_type: str = "text"
    description: str = ""
    default: bool = False


DATA_SOURCES = {
    "jjd_jjd": {"key": "jjd_jjd", "name": "接警单"},
    "fkd_fkd": {"key": "fkd_fkd", "name": "反馈单"},
}

SOURCE_CONFIG = {
    "jjd_jjd": {
        "table": "jjd_jjd",
        "time_column": "bjsj",
        "unit_column": "gxdwdm",
        "category_column": "bjlbdm",
        "type_column": "bjlxdm",
        "detail_column": "bjxldm",
    },
    "fkd_fkd": {
        "table": "fkd_fkd",
        "time_column": "fksj",
        "unit_column": "fkdwdm",
        "category_column": "ajlbbh",
        "type_column": "ajlxbh",
        "detail_column": "ajxlbh",
    },
}

DIMENSIONS_BY_SOURCE = {
    "jjd_jjd": {
        "date": MetricDefinition("date", "日期", "DATE(j.`bjsj`)", "text", "按报警日期分组"),
        "jurisdiction_unit": MetricDefinition("jurisdiction_unit", "管辖单位", "COALESCE(NULLIF(j.`gxdwdm`, ''), '未知')", "text", "按管辖单位代码分组"),
        "receiving_unit": MetricDefinition("receiving_unit", "接警单位", "COALESCE(NULLIF(j.`jjdwmc`, ''), j.`jjdwdm`)", "text", "按接警单位分组"),
    },
    "fkd_fkd": {
        "date": MetricDefinition("date", "日期", "DATE(j.`fksj`)", "text", "按反馈日期分组"),
        "jurisdiction_unit": MetricDefinition("jurisdiction_unit", "反馈单位", "COALESCE(NULLIF(j.`fkdwmc`, ''), j.`fkdwdm`)", "text", "按反馈单位分组"),
    },
}

MEASURES_BY_SOURCE = {
    "jjd_jjd": {
        "event_count": MetricDefinition("event_count", "接警总量", "COUNT(*)", "number", "符合条件的接警单数量", True),
        "completed_count": MetricDefinition("completed_count", "反馈终结数", "SUM(CASE WHEN j.`fkzj` = 1 THEN 1 ELSE 0 END)", "number", "已反馈终结的接警数量"),
    },
    "fkd_fkd": {
        "event_count": MetricDefinition("event_count", "反馈单量", "COUNT(*)", "number", "符合条件的反馈单数量", True),
        "completed_count": MetricDefinition("completed_count", "反馈终结数", "SUM(CASE WHEN j.`fkzj` = 1 THEN 1 ELSE 0 END)", "number", "已反馈终结的反馈单数量"),
    },
}


def get_dimensions(source: str) -> dict[str, MetricDefinition]:
    return DIMENSIONS_BY_SOURCE.get(source, {})


def get_measures(source: str) -> dict[str, MetricDefinition]:
    return MEASURES_BY_SOURCE.get(source, {})
