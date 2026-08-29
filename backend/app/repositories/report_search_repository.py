from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.time import local_now
from app.domain.report_search.definitions import SOURCE_CONFIG, get_dimensions, get_measures
from app.schemas.report_search import ReportSearchQuery


class ReportSearchRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_disabled_codes(self, source: str) -> dict[str, list[str]]:
        rows = self.db.execute(
            text(
                """
                SELECT level, code
                FROM statistics_dictionary_exclusions
                WHERE source = :source
                ORDER BY level, code
                """
            ),
            {"source": source},
        ).mappings().all()
        result = {"category": [], "type": [], "detail": []}
        for row in rows:
            if row["level"] in result:
                result[row["level"]].append(str(row["code"]))
        return result

    def replace_disabled_codes(self, source: str, disabled: dict[str, list[str]], user_id: int) -> None:
        self.db.execute(
            text("DELETE FROM statistics_dictionary_exclusions WHERE source = :source"),
            {"source": source},
        )
        values = [
            {"source": source, "level": level, "code": code, "created_by": user_id, "created_at": local_now()}
            for level, codes in disabled.items()
            for code in sorted(set(codes))
        ]
        if values:
            self.db.execute(
                text(
                    """
                    INSERT INTO statistics_dictionary_exclusions (source, level, code, created_by, created_at)
                    VALUES (:source, :level, :code, :created_by, :created_at)
                    """
                ),
                values,
            )
        self.db.commit()

    def is_classification_enabled(self, source: str, level: str, code: str) -> bool:
        count = self.db.execute(
            text(
                """
                SELECT COUNT(*) FROM statistics_dictionary_exclusions
                WHERE source = :source AND level = :level AND code = :code
                """
            ),
            {"source": source, "level": level, "code": code},
        ).scalar()
        return not bool(count)

    def list_all_classifications(self, source: str, level: str) -> list[dict]:
        if source == "jjd_jjd":
            statements = {
                "category": "SELECT CAST(bjlbdm AS CHAR) code, bjlbmc name FROM zd_bjlbdm WHERE bjlbdm IS NOT NULL AND bjlbmc IS NOT NULL ORDER BY COALESCE(pxh,999999), bjlbdm",
                "type": "SELECT CAST(bjlxdm AS CHAR) code, bjlxmc name FROM zd_bjlxdm WHERE bjlxdm IS NOT NULL AND bjlxmc IS NOT NULL ORDER BY COALESCE(pxh,999999), bjlxdm",
                "detail": "SELECT CAST(bjxldm AS CHAR) code, bjxlmc name FROM zd_bjxldm WHERE bjxlmc IS NOT NULL ORDER BY COALESCE(pxh,999999), bjxldm",
            }
        elif source == "fkd_fkd":
            statements = {
                "category": "SELECT code, name FROM zd_fklbdm WHERE code <> '' AND name IS NOT NULL ORDER BY CAST(code AS UNSIGNED), code",
                "type": "SELECT code, name FROM zd_fklxdm WHERE code <> '' AND name IS NOT NULL ORDER BY COALESCE(pxh,999999), code",
                "detail": "SELECT code, name FROM zd_fkxldm WHERE code <> '' AND name IS NOT NULL ORDER BY COALESCE(pxh,999999), code",
            }
        else:
            return []
        sql = statements.get(level)
        return [dict(row) for row in self.db.execute(text(sql)).mappings().all()] if sql else []

    def list_classifications(self, source: str, level: str, parent_code: str | None = None) -> list[dict]:
        if source == "jjd_jjd":
            if level == "category":
                sql = """
                    SELECT CAST(bjlbdm AS CHAR) AS code, bjlbmc AS name
                    FROM zd_bjlbdm
                    WHERE bjlbdm IS NOT NULL AND bjlbmc IS NOT NULL
                    ORDER BY COALESCE(pxh, 999999), bjlbdm
                """
                params = {}
            elif level == "type":
                sql = """
                    SELECT CAST(bjlxdm AS CHAR) AS code, bjlxmc AS name
                    FROM zd_bjlxdm
                    WHERE bjlxdm IS NOT NULL AND bjlxmc IS NOT NULL
                    ORDER BY COALESCE(pxh, 999999), bjlxdm
                """
                params = {}
            elif level == "detail":
                sql = """
                    SELECT CAST(bjxldm AS CHAR) AS code, bjxlmc AS name
                    FROM zd_bjxldm
                    WHERE bjxlmc IS NOT NULL
                    ORDER BY COALESCE(pxh, 999999), bjxldm
                """
                params = {}
            else:
                return []
        elif source == "fkd_fkd":
            if level == "category":
                sql = """
                    SELECT code, name FROM zd_fklbdm
                    WHERE code <> '' AND name IS NOT NULL
                    ORDER BY CAST(code AS UNSIGNED), code
                """
                params = {}
            elif level == "type":
                sql = """
                    SELECT code, name FROM zd_fklxdm
                    WHERE code <> '' AND name IS NOT NULL
                    ORDER BY COALESCE(pxh, 999999), code
                """
                params = {}
            elif level == "detail":
                sql = """
                    SELECT code, name FROM zd_fkxldm
                    WHERE code <> '' AND name IS NOT NULL
                    ORDER BY COALESCE(pxh, 999999), code
                """
                params = {}
            else:
                return []
        else:
            return []
        rows = [dict(row) for row in self.db.execute(text(sql), params).mappings().all()]
        disabled = set(self.get_disabled_codes(source).get(level, []))
        return [row for row in rows if str(row["code"]) not in disabled]

    def get_department_name(self, unit_code: str | None) -> str:
        if not unit_code:
            return "未配置部门"
        name = self.db.execute(
            text(
                """
                SELECT COALESCE(NULLIF(short_dept_name, ''), NULLIF(detail_dept_name, ''), dept_code)
                FROM jz_dept
                WHERE dept_code = :unit_code
                LIMIT 1
                """
            ),
            {"unit_code": unit_code},
        ).scalar()
        return str(name or unit_code)

    def execute(self, query: ReportSearchQuery, unit_code: str | None) -> list[dict]:
        if not query.dimensions and any((query.category_codes, query.type_codes, query.detail_codes)):
            return self._execute_independent_classification_counts(query, unit_code)

        source = SOURCE_CONFIG[query.source]
        dimensions = [get_dimensions(query.source)[key] for key in query.dimensions]
        measures = [get_measures(query.source)[key] for key in query.measures]
        selections = [f"{item.expression} AS `{item.key}`" for item in dimensions + measures]
        group_by = [item.expression for item in dimensions]
        conditions = [
            f"j.`{source['time_column']}` >= :start_time",
            f"j.`{source['time_column']}` < :end_time",
        ]
        params: dict = {
            "start_time": query.start_time,
            "end_time": query.end_time,
            "limit": query.limit + 1,
        }

        disabled = self.get_disabled_codes(query.source)
        for level, column in (
            ("category", source["category_column"]),
            ("type", source["type_column"]),
            ("detail", source["detail_column"]),
        ):
            if disabled[level]:
                conditions.append(
                    "NOT EXISTS ("
                    "SELECT 1 FROM statistics_dictionary_exclusions AS e "
                    f"WHERE e.source = :exclusion_source AND e.level = '{level}' "
                    f"AND e.code = CAST(j.`{column}` AS CHAR)"
                    ")"
                )
                params["exclusion_source"] = query.source

        for level, column, codes in (
            ("category", source["category_column"], query.category_codes),
            ("type", source["type_column"], query.type_codes),
            ("detail", source["detail_column"], query.detail_codes),
        ):
            if codes:
                placeholders = []
                for index, code in enumerate(dict.fromkeys(codes)):
                    param_name = f"{level}_code_{index}"
                    placeholders.append(f":{param_name}")
                    params[param_name] = code
                conditions.append(f"CAST(j.`{column}` AS CHAR) IN ({', '.join(placeholders)})")

        if unit_code:
            if unit_code == "330782000000":
                conditions.append(f"j.`{source['unit_column']}` LIKE :unit_prefix")
                params["unit_prefix"] = "33078%"
            else:
                conditions.append(f"j.`{source['unit_column']}` = :unit_code")
                params["unit_code"] = unit_code

        sql = [
            f"SELECT {', '.join(selections)}",
            f"FROM `{source['table']}` AS j",
            f"WHERE {' AND '.join(conditions)}",
        ]
        if group_by:
            sql.append(f"GROUP BY {', '.join(group_by)}")
        sql.append(f"ORDER BY `{measures[0].key}` DESC")
        sql.append("LIMIT :limit")
        return [dict(row) for row in self.db.execute(text("\n".join(sql)), params).mappings().all()]

    def _execute_independent_classification_counts(self, query: ReportSearchQuery, unit_code: str | None) -> list[dict]:
        source = SOURCE_CONFIG[query.source]
        disabled = self.get_disabled_codes(query.source)
        level_labels = {"category": "类别", "type": "类型", "detail": "细类"}
        selected = (
            ("category", source["category_column"], query.category_codes),
            ("type", source["type_column"], query.type_codes),
            ("detail", source["detail_column"], query.detail_codes),
        )
        statements: list[str] = []
        params: dict = {"start_time": query.start_time, "end_time": query.end_time}

        for level, column, raw_codes in selected:
            codes = list(dict.fromkeys(raw_codes))
            if not codes:
                continue
            placeholders = []
            for index, code in enumerate(codes):
                param_name = f"independent_{level}_{index}"
                placeholders.append(f":{param_name}")
                params[param_name] = code
            conditions = [
                f"j.`{source['time_column']}` >= :start_time",
                f"j.`{source['time_column']}` < :end_time",
                f"CAST(j.`{column}` AS CHAR) IN ({', '.join(placeholders)})",
            ]
            if disabled[level]:
                exclusion_source = f"exclusion_source_{level}"
                params[exclusion_source] = query.source
                conditions.append(
                    "NOT EXISTS ("
                    "SELECT 1 FROM statistics_dictionary_exclusions AS e "
                    f"WHERE e.source = :{exclusion_source} AND e.level = '{level}' "
                    f"AND e.code = CAST(j.`{column}` AS CHAR)"
                    ")"
                )
            if unit_code == "330782000000":
                unit_param = f"unit_prefix_{level}"
                params[unit_param] = "33078%"
                conditions.append(f"j.`{source['unit_column']}` LIKE :{unit_param}")
            elif unit_code:
                unit_param = f"unit_code_{level}"
                params[unit_param] = unit_code
                conditions.append(f"j.`{source['unit_column']}` = :{unit_param}")
            statements.append(
                "\n".join(
                    [
                        f"SELECT '{level_labels[level]}' AS classification_level,",
                        f"       CAST(j.`{column}` AS CHAR) AS classification_code,",
                        "       COUNT(*) AS event_count",
                        f"FROM `{source['table']}` AS j",
                        f"WHERE {' AND '.join(conditions)}",
                        f"GROUP BY CAST(j.`{column}` AS CHAR)",
                    ]
                )
            )

        params["limit"] = query.limit + 1
        sql = "\nUNION ALL\n".join(statements) + "\nORDER BY classification_level, event_count DESC\nLIMIT :limit"
        return [dict(row) for row in self.db.execute(text(sql), params).mappings().all()]
