from __future__ import annotations

import argparse
import csv
import secrets
import string
import sys
from pathlib import Path

from sqlalchemy import select, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.system import User

ROOT_DEPARTMENT_CODE = "330782000000"
DEFAULT_OUTPUT = Path("storage/station-account-credentials.csv")
PASSWORD_ALPHABET = string.ascii_letters + string.digits + "@#_-"


def build_username(unit_code: str) -> str:
    """使用部门编码中的派出所段生成稳定、易辨认的用户名。"""
    station_segment = unit_code[6:8] if len(unit_code) >= 8 else unit_code
    return f"pcs_{station_segment.lower()}"


def generate_password(length: int = 16) -> str:
    while True:
        password = "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))
        if (
            any(char.islower() for char in password)
            and any(char.isupper() for char in password)
            and any(char.isdigit() for char in password)
            and any(char in "@#_-" for char in password)
        ):
            return password


def load_station_departments(db) -> list[dict[str, str]]:
    table_exists = db.execute(
        text(
            """
            SELECT 1
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'jz_dept'
            LIMIT 1
            """
        )
    ).scalar()
    if not table_exists:
        raise RuntimeError("当前数据库不存在 jz_dept，无法读取派出所部门清单")

    rows = db.execute(
        text(
            """
            SELECT
                dept_code AS unit_code,
                COALESCE(NULLIF(short_dept_name, ''), NULLIF(detail_dept_name, ''), dept_code) AS display_name
            FROM jz_dept
            WHERE dept_code <> :root_code
              AND (short_dept_name LIKE :keyword OR detail_dept_name LIKE :keyword)
              AND COALESCE(del_flag, '0') = '0'
              AND COALESCE(status, '0') = '0'
              AND COALESCE(is_show, '1') = '1'
            ORDER BY dept_code
            """
        ),
        {"root_code": ROOT_DEPARTMENT_CODE, "keyword": "%派出所%"},
    ).mappings().all()
    return [
        {"unit_code": str(row["unit_code"]), "display_name": str(row["display_name"])}
        for row in rows
    ]


def provision_accounts(apply: bool) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    created: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    with SessionLocal() as db:
        departments = load_station_departments(db)
        for department in departments:
            username = build_username(department["unit_code"])
            exists = db.scalar(
                select(User.id).where(
                    (User.username == username) | (User.unit_code == department["unit_code"])
                ).limit(1)
            )
            if exists:
                skipped.append({**department, "username": username})
                continue

            password = generate_password()
            created.append({**department, "username": username, "password": password})
            if apply:
                db.add(
                    User(
                        username=username,
                        password_hash=hash_password(password),
                        display_name=department["display_name"],
                        roles="user",
                        unit_code=department["unit_code"],
                        status="enabled",
                    )
                )
        if apply:
            db.commit()
        else:
            db.rollback()
    return created, skipped


def write_credentials(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["display_name", "unit_code", "username", "password"],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="批量创建市局下属派出所账号")
    parser.add_argument("--apply", action="store_true", help="实际写入数据库；不传时仅预览")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="初始凭据 CSV 输出路径")
    args = parser.parse_args()

    created, skipped = provision_accounts(apply=args.apply)
    if args.apply and created:
        write_credentials(args.output, created)
        print(f"已创建 {len(created)} 个派出所账号，初始凭据已写入：{args.output}")
    elif args.apply:
        print("没有需要创建的新账号")
    else:
        print(f"预览：将创建 {len(created)} 个账号；使用 --apply 确认写入")
    print(f"已存在并跳过：{len(skipped)} 个")


if __name__ == "__main__":
    main()
