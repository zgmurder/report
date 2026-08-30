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
        "deduplicate_column": "jjdbh",
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

def _comparison_measures(event_label: str) -> dict[str, MetricDefinition]:
    return {
        "event_count": MetricDefinition("event_count", event_label, "COUNT(*)", "number", "当前查询时间范围内的警情数量", True),
        "year_on_year_rate": MetricDefinition("year_on_year_rate", "同比", "", "number", "相较去年同期的增减比例"),
        "period_on_period_rate": MetricDefinition("period_on_period_rate", "环比", "", "number", "相较上一等长周期的增减比例"),
        "proportion": MetricDefinition("proportion", "占比", "", "number", "所选分类数量占同层级全部警情数量的比例"),
        "year_on_year_change": MetricDefinition("year_on_year_change", "同比数", "", "number", "当前数量减去年同期数量"),
        "period_on_period_change": MetricDefinition("period_on_period_change", "环比数", "", "number", "当前数量减上一等长周期数量"),
    }


MEASURES_BY_SOURCE = {
    "jjd_jjd": _comparison_measures("接警总量"),
    "fkd_fkd": _comparison_measures("反馈单量"),
}


def get_dimensions(source: str) -> dict[str, MetricDefinition]:
    return DIMENSIONS_BY_SOURCE.get(source, {})


def get_measures(source: str) -> dict[str, MetricDefinition]:
    return MEASURES_BY_SOURCE.get(source, {})
