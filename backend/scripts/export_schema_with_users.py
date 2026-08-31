"""Export all MySQL table structures and only sys_users account rows."""

from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import create_engine, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "sql" / "export" / "report_schema_with_users.sql"
USER_TABLE = "sys_users"
_BINARY_TYPES = {"binary", "varbinary", "blob", "tinyblob", "mediumblob", "longblob", "bit"}


def quote_identifier(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def sql_literal(value: Any, *, binary: bool = False) -> str:
    if value is None:
        return "NULL"
    if binary:
        return "X'" + bytes(value).hex().upper() + "'"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, datetime):
        value = value.strftime("%Y-%m-%d %H:%M:%S.%f").rstrip("0").rstrip(".")
    elif isinstance(value, (date, time)):
        value = value.isoformat()

    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace("'", "''")
        .replace("\0", "\\0")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\x1a", "\\Z")
    )
    return f"'{escaped}'"


def export() -> tuple[int, int, int]:
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    with engine.connect() as connection:
        database_name = connection.execute(text("SELECT DATABASE()")).scalar_one()
        tables = [
            row[0]
            for row in connection.execute(
                text(
                    "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_TYPE='BASE TABLE' "
                    "ORDER BY TABLE_NAME"
                )
            )
        ]
        if USER_TABLE not in tables:
            raise RuntimeError(f"Required user table not found: {USER_TABLE}")

        lines = [
            "-- 警情智能报告系统数据库导出",
            "-- 内容：全部基础表结构；仅 sys_users 表包含账户数据",
            "-- 不包含其他业务表数据、视图、存储过程、触发器和事件",
            "-- 账户密码保持数据库中的哈希值，不包含数据库连接凭据",
            "",
            "SET NAMES utf8mb4;",
            "SET FOREIGN_KEY_CHECKS = 0;",
            "SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';",
            "",
            f"CREATE DATABASE IF NOT EXISTS {quote_identifier(database_name)} "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
            f"USE {quote_identifier(database_name)};",
            "",
        ]

        for table in tables:
            create_sql = connection.execute(text(f"SHOW CREATE TABLE {quote_identifier(table)}")).one()[1]
            lines.extend(
                [
                    "-- ----------------------------",
                    f"-- Table structure for {table}",
                    "-- ----------------------------",
                    f"DROP TABLE IF EXISTS {quote_identifier(table)};",
                    f"{create_sql};",
                    "",
                ]
            )

        columns = connection.execute(
            text(
                "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=:table "
                "ORDER BY ORDINAL_POSITION"
            ),
            {"table": USER_TABLE},
        ).all()
        user_rows = connection.execute(text(f"SELECT * FROM {quote_identifier(USER_TABLE)} ORDER BY id")).all()
        if user_rows:
            column_names = [column[0] for column in columns]
            row_values = []
            for row in user_rows:
                values = [
                    sql_literal(value, binary=str(columns[index][1]).lower() in _BINARY_TYPES)
                    for index, value in enumerate(row)
                ]
                row_values.append("(" + ", ".join(values) + ")")

            lines.extend(
                [
                    "-- ----------------------------",
                    "-- Account data for sys_users only",
                    "-- Password values remain hashed exactly as stored in the database",
                    "-- ----------------------------",
                    f"LOCK TABLES {quote_identifier(USER_TABLE)} WRITE;",
                    f"INSERT INTO {quote_identifier(USER_TABLE)} "
                    f"({', '.join(quote_identifier(name) for name in column_names)}) VALUES\n  "
                    + ",\n  ".join(row_values)
                    + ";",
                    "UNLOCK TABLES;",
                    "",
                ]
            )

        lines.extend(["SET FOREIGN_KEY_CHECKS = 1;", ""])
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        return len(tables), len(user_rows), OUTPUT_PATH.stat().st_size


if __name__ == "__main__":
    table_count, user_count, output_size = export()
    print(f"Exported {table_count} tables and {user_count} user rows to {OUTPUT_PATH} ({output_size} bytes)")
