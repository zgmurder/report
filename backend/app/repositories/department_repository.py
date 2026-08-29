from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.system import Department
from app.schemas.department import DepartmentCreateRequest, DepartmentTreeItem, DepartmentUpdateRequest


ROOT_DEPARTMENT_SEED = {"name": "义乌市公安局", "code": "330782000000", "parent_id": None, "sort_order": 1}
CHILD_DEPARTMENT_SEEDS = [
    {"name": "稠城派出所", "code": "330782010000", "sort_order": 10},
    {"name": "北苑派出所", "code": "330782020000", "sort_order": 20},
    {"name": "江东派出所", "code": "330782030000", "sort_order": 30},
    {"name": "稠江派出所", "code": "330782040000", "sort_order": 40},
]


class DepartmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def ensure_seed_data(self) -> None:
        exists = self.db.scalar(select(Department.id).limit(1))
        if exists:
            return
        root = Department(**ROOT_DEPARTMENT_SEED, status="enabled")
        self.db.add(root)
        self.db.flush()
        self.db.add_all([Department(**item, parent_id=root.id, status="enabled") for item in CHILD_DEPARTMENT_SEEDS])
        self.db.commit()

    def list(self, include_disabled: bool = False) -> list:
        external_rows = self._list_jz_dept_root_and_police_stations(include_disabled=include_disabled)
        if external_rows:
            return external_rows

        self.ensure_seed_data()
        stmt = select(Department)
        if not include_disabled:
            stmt = stmt.where(Department.status == "enabled")
        stmt = stmt.order_by(Department.sort_order.asc(), Department.id.asc())
        return list(self.db.scalars(stmt).all())

    def tree(self, include_disabled: bool = False) -> list[DepartmentTreeItem]:
        external_rows = self._list_jz_dept_root_and_police_stations(include_disabled=include_disabled)
        if external_rows:
            return self._build_tree(external_rows)

        rows = self.list(include_disabled=include_disabled)
        return self._build_tree(rows)

    def _list_jz_dept_root_and_police_stations(self, include_disabled: bool = False) -> list:
        if not self._table_exists("jz_dept"):
            return []

        conditions = [
            "(dept_code = :root_dept_code OR short_dept_name LIKE :keyword OR detail_dept_name LIKE :keyword)",
        ]
        params = {"root_dept_code": "330782000000", "keyword": "%派出所%"}
        if not include_disabled:
            conditions.extend([
                "COALESCE(del_flag, '0') = '0'",
                "COALESCE(status, '0') = '0'",
                "COALESCE(is_show, '1') = '1'",
            ])
        rows = self.db.execute(
            text(
                f"""
                SELECT
                    dept_code,
                    parent_dept_code,
                    COALESCE(NULLIF(short_dept_name, ''), NULLIF(detail_dept_name, ''), dept_code) AS name,
                    COALESCE(sort, 0) AS sort_order,
                    COALESCE(status, '0') AS status,
                    create_time,
                    update_time
                FROM jz_dept
                WHERE {' AND '.join(conditions)}
                ORDER BY COALESCE(sort, 9999), dept_code
                """
            ),
            params,
        ).mappings().all()
        now = datetime.now()
        return [
            SimpleNamespace(
                id=self._dept_id(row["dept_code"], index),
                name=row["name"],
                code=row["dept_code"],
                parent_id=self._dept_id(row["parent_dept_code"], None),
                parent_code=row["parent_dept_code"],
                sort_order=int(row["sort_order"] or 0),
                status="enabled" if row["status"] == "0" else "disabled",
                created_at=row["create_time"] or now,
                updated_at=row["update_time"] or row["create_time"] or now,
            )
            for index, row in enumerate(rows, start=1)
        ]

    @staticmethod
    def _dept_id(code: str | None, fallback: int | None) -> int | None:
        if code and code.isdigit():
            return int(code)
        return fallback

    def _table_exists(self, table_name: str) -> bool:
        return bool(
            self.db.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name
                    LIMIT 1
                    """
                ),
                {"table_name": table_name},
            ).scalar()
        )

    def _build_tree(self, rows: list) -> list[DepartmentTreeItem]:
        nodes = {row.id: self._to_tree_item(row) for row in rows}
        roots: list[DepartmentTreeItem] = []
        for row in rows:
            node = nodes[row.id]
            parent = nodes.get(row.parent_id) if row.parent_id else None
            if parent:
                parent.children.append(node)
            else:
                roots.append(node)
        return roots

    def get(self, department_id: int) -> Department | None:
        return self.db.get(Department, department_id)

    def create(self, req: DepartmentCreateRequest) -> Department:
        row = Department(**req.model_dump())
        self.db.add(row)
        self._commit_or_raise_duplicate()
        self.db.refresh(row)
        return row

    def update(self, department_id: int, req: DepartmentUpdateRequest) -> Department | None:
        row = self.db.get(Department, department_id)
        if not row:
            return None
        for key, value in req.model_dump(exclude_unset=True).items():
            setattr(row, key, value)
        self._commit_or_raise_duplicate()
        self.db.refresh(row)
        return row

    def delete(self, department_id: int) -> bool:
        row = self.db.get(Department, department_id)
        if not row:
            return False
        row.status = "disabled"
        self.db.commit()
        return True

    def _commit_or_raise_duplicate(self) -> None:
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("部门编码已存在") from exc

    def _to_tree_item(self, row: Department) -> DepartmentTreeItem:
        return DepartmentTreeItem(
            id=row.id,
            name=row.name,
            code=row.code,
            parent_id=row.parent_id,
            sort_order=row.sort_order,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
            children=[],
        )
