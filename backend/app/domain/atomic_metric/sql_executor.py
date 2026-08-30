from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.domain.atomic_metric.exceptions import ServiceException

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE|CALL)\b"
    r"|\bREPLACE\s+INTO\b",
    re.I,
)
MYSQL_RESERVED_SELECT_ALIASES: dict[str, str] = {
    "repeat": "repeat_count",
    "order": "order_num",
    "group": "group_name",
    "key": "key_value",
    "index": "idx_value",
    "range": "range_value",
    "status": "status_value",
    "rank": "rank_value",
    "year": "year_value",
    "month": "month_value",
    "day": "day_value",
}
_RESERVED_ALIAS_PATTERN = re.compile(
    r"\bAS\s+(" + "|".join(map(re.escape, MYSQL_RESERVED_SELECT_ALIASES.keys())) + r")\b(?!\w)",
    re.I,
)
_SQL_BIND_PARAM_PATTERN = re.compile(r":([a-z_][a-z0-9_]*)", re.I)
_BUILTIN_PARAM_KEYS = ("date_start", "date_end", "dept_code")
_BUILTIN_EMPTY_OK = frozenset({"dept_code"})


class ComponentSqlExecutor:
    @classmethod
    def sanitize_mysql_select_aliases(cls, sql: str) -> str:
        def _replace(match: re.Match[str]) -> str:
            name = match.group(1).lower()
            return f"AS {MYSQL_RESERVED_SELECT_ALIASES.get(name, match.group(1))}"

        return _RESERVED_ALIAS_PATTERN.sub(_replace, sql)

    @classmethod
    def validate_sql(cls, sql: str) -> str:
        cleaned = (sql or "").strip()
        if not cleaned:
            raise ServiceException(message="请填写统计 SQL")
        if ";" in cleaned.rstrip(";"):
            raise ServiceException(message="仅允许单条 SELECT 语句")
        if _FORBIDDEN.search(cleaned):
            raise ServiceException(message="仅允许 SELECT 查询")
        head_sql = cls._strip_leading_sql_comments(cleaned)
        head = head_sql.upper()
        if not (head.startswith("SELECT") or head.startswith("WITH")):
            raise ServiceException(message="SQL 必须以 SELECT 或 WITH 开头")
        return cls.sanitize_mysql_select_aliases(cleaned)

    @classmethod
    def _strip_leading_sql_comments(cls, sql: str) -> str:
        text_sql = sql or ""
        while True:
            stripped = text_sql.lstrip()
            if stripped.startswith("--"):
                newline = stripped.find("\n")
                text_sql = "" if newline < 0 else stripped[newline + 1 :]
                continue
            if stripped.startswith("/*"):
                end = stripped.find("*/")
                if end < 0:
                    return ""
                text_sql = stripped[end + 2 :]
                continue
            return stripped

    @classmethod
    def normalize_param_key(cls, key: str) -> str | None:
        raw = (key or "").strip()
        if not raw:
            return None
        snake = re.sub(r"([A-Z])", r"_\1", raw).lower().lstrip("_")
        if not re.match(r"^[a-z][a-z0-9_]*$", snake):
            return None
        return snake

    @classmethod
    def extract_sql_bind_names(cls, sql: str) -> set[str]:
        names: set[str] = set()
        for match in _SQL_BIND_PARAM_PATTERN.finditer(sql or ""):
            name = match.group(1).lower()
            if name in MYSQL_RESERVED_SELECT_ALIASES:
                continue
            names.add(name)
        return names

    @classmethod
    def build_bind_params(cls, params: dict[str, Any], sql: str | None = None) -> dict[str, Any]:
        src = dict(params or {})
        merged: dict[str, Any] = {}

        def pick_builtin(key: str) -> Any | None:
            camel = "".join(w if i == 0 else w.capitalize() for i, w in enumerate(key.split("_")))
            for candidate in (key, camel):
                if candidate not in src or src[candidate] is None:
                    continue
                if src[candidate] == "" and key not in _BUILTIN_EMPTY_OK:
                    continue
                return src[candidate]
            return None

        for key in _BUILTIN_PARAM_KEYS:
            val = pick_builtin(key)
            if val is not None:
                merged[key] = val

        if "date_start" not in merged:
            merged["date_start"] = datetime.now().strftime("%Y-%m-%d")
        if "date_end" not in merged:
            merged["date_end"] = merged["date_start"]
        if "dept_code" not in merged:
            merged["dept_code"] = ""

        builtin_set = set(_BUILTIN_PARAM_KEYS)
        for raw_key, val in src.items():
            snake = cls.normalize_param_key(raw_key)
            if not snake or snake in builtin_set or val is None:
                continue
            merged[snake] = val

        for name in cls.extract_sql_bind_names(sql or ""):
            if name not in merged:
                merged[name] = ""
        return merged

    @staticmethod
    def sql_literal(value: Any) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        if isinstance(value, datetime):
            value = value.strftime("%Y-%m-%d %H:%M:%S")
        text_value = str(value)
        return "'" + text_value.replace("\\", "\\\\").replace("'", "''") + "'"

    @classmethod
    def format_executable_sql(cls, sql: str, params: dict[str, Any]) -> str:
        validated = cls.validate_sql(sql)
        bind = cls.build_bind_params(params, validated)

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            return cls.sql_literal(bind.get(name))

        return _SQL_BIND_PARAM_PATTERN.sub(replace, validated)

    @classmethod
    def normalize_sql_row(cls, row: dict[str, Any]) -> dict[str, Any]:
        out = dict(row)
        for reserved, safe in MYSQL_RESERVED_SELECT_ALIASES.items():
            if safe in out and reserved not in out:
                out[reserved] = out[safe]
        return out

    @staticmethod
    def serialize_value(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return value

    @classmethod
    def fetch_rows(
        cls,
        db: Session,
        sql: str,
        params: dict[str, Any],
        limit: int = 500,
        data_source_row: Any = None,
    ) -> list[dict[str, Any]]:
        del data_source_row
        validated = cls.validate_sql(sql)
        bind = cls.build_bind_params(params, validated)
        result = db.execute(text(validated), bind)
        keys = list(result.keys())
        rows: list[dict[str, Any]] = []
        for i, row in enumerate(result.fetchall()):
            if i >= limit:
                break
            rows.append(cls.normalize_sql_row({k: cls.serialize_value(row[j]) for j, k in enumerate(keys)}))
        return rows
