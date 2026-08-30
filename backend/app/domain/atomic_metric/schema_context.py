from __future__ import annotations

from typing import Any

# 列清单对齐当前库：
# - 接警单：bjlbdm/bjlxdm/bjxldm + zd_bjl*dm；含 zjjdbh 主单去重
# - 反馈单：ajlbbh/ajlxbh/ajxlbh + zd_fklbdm/zd_fklxdm/zd_fkxldm（与 jjd 不同）
_JJD_COLUMNS = [
    {"column_name": name, "column_type": "varchar(100)", "is_nullable": "YES", "column_comment": ""}
    for name in (
        "jjdbh", "zjjdbh", "bjsj", "fkzj",
        "bjlbdm", "bjlxdm", "bjxldm", "gxdwdm", "jjdwdm", "jjdwmc",
        "insert_time",
    )
]

_FKD_COLUMNS = [
    {"column_name": name, "column_type": "varchar(100)", "is_nullable": "YES", "column_comment": ""}
    for name in (
        "fkdbh", "jjdbh",
        "ajlbbh", "ajlxbh", "ajxlbh",
        "fksj", "bjsj", "fkzj",
        "fkdwdm", "fkdwmc", "txfkdwdm", "txfkdwmc",
        "sdsq", "sdpcs", "sdxq", "jdxz", "jdxzmc", "afsq",
        "cjqk", "zrmj", "zzfkbs",
    )
]


class ComponentSchemaContext:
    def __init__(
        self,
        *,
        data_source_code: str,
        data_source_name: str,
        source_type: str,
        table_name: str,
        table_comment: str,
        schema_name: str | None,
        columns: list[dict[str, str]],
    ) -> None:
        self.data_source_code = data_source_code
        self.data_source_name = data_source_name
        self.source_type = source_type
        self.table_name = table_name
        self.table_comment = table_comment
        self.schema_name = schema_name
        self.columns = columns

    @classmethod
    def resolve(cls, data_source_code: str | None) -> ComponentSchemaContext:
        code = (data_source_code or "fkd_fkd").strip() or "fkd_fkd"
        if code in {"jjd_jjd", "jjd"}:
            return cls(
                data_source_code="jjd_jjd",
                data_source_name="接警单",
                source_type="local",
                table_name="jjd_jjd",
                table_comment="接警单表",
                schema_name=None,
                columns=[dict(item) for item in _JJD_COLUMNS],
            )
        return cls(
            data_source_code="fkd_fkd",
            data_source_name="反馈单",
            source_type="local",
            table_name="fkd_fkd",
            table_comment="反馈单表",
            schema_name=None,
            columns=[dict(item) for item in _FKD_COLUMNS],
        )

    def column_names(self) -> list[str]:
        return [c["column_name"] for c in self.columns]
