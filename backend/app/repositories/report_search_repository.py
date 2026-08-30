from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.dialects import mysql
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

    def execute_jurisdiction_yoy_summary(
        self, query: ReportSearchQuery, unit_code: str, scope_level: str
    ) -> tuple[list[dict], str]:
        periods = self._comparison_periods(query.start_time, query.end_time, ["year_on_year_rate"])
        params: dict = {
            "current_start": periods["current_start"],
            "current_end": periods["current_end"],
            "year_start": periods["year_start"],
            "year_end": periods["year_end"],
            "scan_start": periods["scan_start"],
            "limit": query.limit + 1,
        }
        conditions = [
            "j.`fksj` >= :scan_start",
            "j.`fksj` < :current_end",
        ]
        self._append_classification_conditions(conditions, params, query, SOURCE_CONFIG["fkd_fkd"])

        if scope_level == "police_station":
            group_expression = "CAST(j.`sdpcs` AS CHAR)"
            name_expression = "COALESCE(NULLIF(d.short_dept_name, ''), NULLIF(d.detail_dept_name, ''), CAST(j.`sdpcs` AS CHAR))"
            joins = "LEFT JOIN jz_dept AS d ON CONVERT(d.dept_code USING utf8mb4) COLLATE utf8mb4_unicode_ci = CAST(j.`sdpcs` AS CHAR) COLLATE utf8mb4_unicode_ci"
            conditions.extend([
                "j.`sdpcs` LIKE '330782%'",
                "COALESCE(NULLIF(d.short_dept_name, ''), NULLIF(d.detail_dept_name, '')) LIKE '%派出所%'",
            ])
        else:
            group_expression = "CAST(j.`sdsq` AS CHAR)"
            name_expression = "COALESCE(NULLIF(c.fasqmc, ''), CAST(j.`sdsq` AS CHAR))"
            joins = "LEFT JOIN zd_fasqdm AS c ON CAST(c.fasqdm AS CHAR) COLLATE utf8mb4_unicode_ci = CAST(j.`sdsq` AS CHAR) COLLATE utf8mb4_unicode_ci"
            conditions.extend([
                "CAST(j.`sdpcs` AS CHAR) = :scope_unit_code",
                "j.`sdsq` IS NOT NULL",
                "TRIM(CAST(j.`sdsq` AS CHAR)) <> ''",
            ])
            params["scope_unit_code"] = unit_code

        selections = [
            f"{group_expression} AS scope_code",
            f"{name_expression} AS scope_name",
            f"{self._period_count_expression(SOURCE_CONFIG['fkd_fkd'], ':current_start', ':current_end')} AS event_count",
            f"{self._period_count_expression(SOURCE_CONFIG['fkd_fkd'], ':year_start', ':year_end')} AS year_base_count",
        ]
        sql = "\n".join([
            f"SELECT {', '.join(selections)}",
            "FROM `fkd_fkd` AS j",
            joins,
            f"WHERE {' AND '.join(conditions)}",
            f"GROUP BY {group_expression}, {name_expression}",
            "ORDER BY event_count DESC",
            "LIMIT :limit",
        ])
        statement = text(sql)
        executed_sql = self._render_sql(statement, params)
        return [dict(row) for row in self.db.execute(statement, params).mappings().all()], executed_sql

    def execute(self, query: ReportSearchQuery, unit_code: str | None) -> tuple[list[dict], str]:
        if not query.dimensions:
            if any((query.category_codes, query.type_codes, query.detail_codes)):
                return self._execute_independent_classification_counts(query, unit_code)
            return self._execute_total_comparison(query, unit_code)

        source = SOURCE_CONFIG[query.source]
        dimensions = [get_dimensions(query.source)[key] for key in query.dimensions]
        selections = [f"{item.expression} AS `{item.key}`" for item in dimensions]
        selections.append(f"{self._count_expression(source)} AS `event_count`")
        conditions = [
            f"j.`{source['time_column']}` >= :start_time",
            f"j.`{source['time_column']}` < :end_time",
        ]
        params: dict = {"start_time": query.start_time, "end_time": query.end_time, "limit": query.limit + 1}
        self._append_unit_condition(conditions, params, source, unit_code)
        sql = [
            f"SELECT {', '.join(selections)}",
            f"FROM `{source['table']}` AS j",
            f"WHERE {' AND '.join(conditions)}",
            f"GROUP BY {', '.join(item.expression for item in dimensions)}",
            "ORDER BY `event_count` DESC",
            "LIMIT :limit",
        ]
        statement = text("\n".join(sql))
        executed_sql = self._render_sql(statement, params)
        return [dict(row) for row in self.db.execute(statement, params).mappings().all()], executed_sql

    def _execute_total_comparison(self, query: ReportSearchQuery, unit_code: str | None) -> tuple[list[dict], str]:
        source = SOURCE_CONFIG[query.source]
        periods = self._comparison_periods(query.start_time, query.end_time, query.measures)
        params: dict = {"current_start": periods["current_start"], "current_end": periods["current_end"], "scan_start": periods["scan_start"]}
        conditions = [
            f"j.`{source['time_column']}` >= :scan_start",
            f"j.`{source['time_column']}` < :current_end",
        ]
        self._append_unit_condition(conditions, params, source, unit_code)
        selections = [
            f"{self._period_count_expression(source, ':current_start', ':current_end')} AS event_count"
        ]
        if any(key in query.measures for key in ("year_on_year_rate", "year_on_year_change")):
            params.update(year_start=periods["year_start"], year_end=periods["year_end"])
            selections.append(
                f"{self._period_count_expression(source, ':year_start', ':year_end')} AS year_base_count"
            )
        if any(key in query.measures for key in ("period_on_period_rate", "period_on_period_change")):
            params.update(period_start=periods["period_start"], period_end=periods["period_end"])
            selections.append(
                f"{self._period_count_expression(source, ':period_start', ':period_end')} AS period_base_count"
            )
        sql = "\n".join(
            [
                f"SELECT {', '.join(selections)}",
                f"FROM `{source['table']}` AS j",
                f"WHERE {' AND '.join(conditions)}",
            ]
        )
        statement = text(sql)
        executed_sql = self._render_sql(statement, params)
        return [dict(row) for row in self.db.execute(statement, params).mappings().all()], executed_sql

    def _execute_independent_classification_counts(self, query: ReportSearchQuery, unit_code: str | None) -> tuple[list[dict], str]:
        source = SOURCE_CONFIG[query.source]
        periods = self._comparison_periods(query.start_time, query.end_time, query.measures)
        level_labels = {"category": "类别", "type": "类型", "detail": "细类"}
        selected = (
            ("category", source["category_column"], query.category_codes),
            ("type", source["type_column"], query.type_codes),
            ("detail", source["detail_column"], query.detail_codes),
        )
        statements: list[str] = []
        params: dict = {"current_start": periods["current_start"], "current_end": periods["current_end"], "scan_start": periods["scan_start"]}
        if any(key in query.measures for key in ("year_on_year_rate", "year_on_year_change")):
            params.update(year_start=periods["year_start"], year_end=periods["year_end"])
        if any(key in query.measures for key in ("period_on_period_rate", "period_on_period_change")):
            params.update(period_start=periods["period_start"], period_end=periods["period_end"])

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
                f"j.`{source['time_column']}` >= :scan_start",
                f"j.`{source['time_column']}` < :current_end",
                f"CAST(j.`{column}` AS CHAR) IN ({', '.join(placeholders)})",
            ]
            self._append_unit_condition(conditions, params, source, unit_code, level)
            selections = [
                f"SELECT '{level_labels[level]}' AS classification_level",
                f"CAST(j.`{column}` AS CHAR) AS classification_code",
                f"{self._period_count_expression(source, ':current_start', ':current_end')} AS event_count",
            ]
            if any(key in query.measures for key in ("year_on_year_rate", "year_on_year_change")):
                selections.append(
                    f"{self._period_count_expression(source, ':year_start', ':year_end')} AS year_base_count"
                )
            if any(key in query.measures for key in ("period_on_period_rate", "period_on_period_change")):
                selections.append(
                    f"{self._period_count_expression(source, ':period_start', ':period_end')} AS period_base_count"
                )
            if "proportion" in query.measures:
                denominator_conditions = [
                    f"d.`{source['time_column']}` >= :current_start",
                    f"d.`{source['time_column']}` < :current_end",
                ]
                self._append_unit_condition(denominator_conditions, params, source, unit_code, f"denominator_{level}", alias="d")
                selections.append(
                    f"(SELECT {self._count_expression(source, alias='d')} FROM `{source['table']}` AS d WHERE {' AND '.join(denominator_conditions)}) AS proportion_base_count"
                )
            statements.append(
                "\n".join(
                    [
                        ",\n       ".join(selections),
                        f"FROM `{source['table']}` AS j",
                        f"WHERE {' AND '.join(conditions)}",
                        f"GROUP BY CAST(j.`{column}` AS CHAR)",
                    ]
                )
            )

        params["limit"] = query.limit + 1
        sql = "\nUNION ALL\n".join(statements) + "\nORDER BY classification_level, event_count DESC\nLIMIT :limit"
        statement = text(sql)
        executed_sql = self._render_sql(statement, params)
        return [dict(row) for row in self.db.execute(statement, params).mappings().all()], executed_sql

    @staticmethod
    def _append_classification_conditions(
        conditions: list[str], params: dict, query: ReportSearchQuery, source: dict, alias: str = "j"
    ) -> None:
        selected = (
            ("category", source["category_column"], query.category_codes),
            ("type", source["type_column"], query.type_codes),
            ("detail", source["detail_column"], query.detail_codes),
        )
        for level, column, raw_codes in selected:
            codes = list(dict.fromkeys(raw_codes))
            if not codes:
                continue
            placeholders = []
            for index, code in enumerate(codes):
                name = f"summary_{level}_{index}"
                params[name] = code
                placeholders.append(f":{name}")
            conditions.append(f"CAST({alias}.`{column}` AS CHAR) IN ({', '.join(placeholders)})")

    @staticmethod
    def _count_expression(source: dict, alias: str = "j") -> str:
        deduplicate_column = source.get("deduplicate_column")
        if deduplicate_column:
            return f"COUNT(DISTINCT {alias}.`{deduplicate_column}`)"
        return "COUNT(*)"

    @staticmethod
    def _period_count_expression(source: dict, start_param: str, end_param: str, alias: str = "j") -> str:
        condition = (
            f"{alias}.`{source['time_column']}` >= {start_param} "
            f"AND {alias}.`{source['time_column']}` < {end_param}"
        )
        deduplicate_column = source.get("deduplicate_column")
        if deduplicate_column:
            return f"COUNT(DISTINCT CASE WHEN {condition} THEN {alias}.`{deduplicate_column}` END)"
        return f"SUM(CASE WHEN {condition} THEN 1 ELSE 0 END)"

    @staticmethod
    def _comparison_periods(start_time: datetime, end_time: datetime, measures: list[str]) -> dict:
        duration = end_time - start_time
        period_end = start_time
        period_start = period_end - duration
        year_start = ReportSearchRepository._shift_year(start_time)
        year_end = ReportSearchRepository._shift_year(end_time)
        scan_starts = [start_time]
        if any(key in measures for key in ("year_on_year_rate", "year_on_year_change")):
            scan_starts.append(year_start)
        if any(key in measures for key in ("period_on_period_rate", "period_on_period_change")):
            scan_starts.append(period_start)
        return {
            "current_start": start_time,
            "current_end": end_time,
            "year_start": year_start,
            "year_end": year_end,
            "period_start": period_start,
            "period_end": period_end,
            "scan_start": min(scan_starts),
        }

    @staticmethod
    def _shift_year(value: datetime) -> datetime:
        try:
            return value.replace(year=value.year - 1)
        except ValueError:
            return value.replace(year=value.year - 1, day=28)

    @staticmethod
    def _append_unit_condition(
        conditions: list[str], params: dict, source: dict, unit_code: str | None, suffix: str = "", alias: str = "j"
    ) -> None:
        if not unit_code:
            return
        param_suffix = f"_{suffix}" if suffix else ""
        if unit_code == "330782000000":
            name = f"unit_prefix{param_suffix}"
            params[name] = "33078%"
            conditions.append(f"{alias}.`{source['unit_column']}` LIKE :{name}")
        else:
            name = f"unit_code{param_suffix}"
            params[name] = unit_code
            conditions.append(f"{alias}.`{source['unit_column']}` = :{name}")

    @staticmethod
    def _render_sql(statement, params: dict) -> str:
        bound = statement.bindparams(**params)
        return str(bound.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))
