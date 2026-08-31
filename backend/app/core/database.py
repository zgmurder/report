from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


def _configured_admin_id(conn) -> int | None:
    """Resolve legacy-row ownership only to the explicitly configured admin."""
    username = get_settings().admin_username.strip()
    if not username:
        return None
    return conn.execute(
        text("SELECT id FROM sys_users WHERE username = :username AND status = 'enabled' LIMIT 1"),
        {"username": username},
    ).scalar()


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(
    settings.database_url,
    connect_args={"charset": "utf8mb4", "use_unicode": True, "init_command": "SET time_zone = '+08:00'"},
    pool_pre_ping=True,
    pool_recycle=1800,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    # Import models before create_all so SQLAlchemy registers metadata.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "mysql":
        with engine.begin() as conn:
            for table_name in ("report_documents", "report_folders", "report_templates", "stat_components", "data_source_configs", "departments", "sys_users", "statistics_dictionary_exclusions", "community_org_mappings"):
                conn.execute(text(f"ALTER TABLE {table_name} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            community_columns = {
                "source_row": "INT NOT NULL DEFAULT 0",
                "xzqh": "VARCHAR(12) NOT NULL DEFAULT ''",
                "mapping_name": "VARCHAR(100) NOT NULL DEFAULT ''",
                "match_status": "VARCHAR(20) NOT NULL DEFAULT 'unmatched'",
            }
            for column_name, definition in community_columns.items():
                has_column = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'community_org_mappings' "
                        "AND COLUMN_NAME = :column_name"
                    ),
                    {"column_name": column_name},
                ).scalar()
                if not has_column:
                    conn.execute(
                        text(
                            f"ALTER TABLE community_org_mappings "
                            f"ADD COLUMN {column_name} {definition}"
                        )
                    )

            template_columns = {
                "original_filename": "VARCHAR(255) NULL",
                "file_path": "VARCHAR(500) NULL",
                "file_size": "INT NULL",
                "mime_type": "VARCHAR(150) NULL",
                "created_by": "INT NULL",
            }
            for column_name, definition in template_columns.items():
                has_column = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'report_templates' AND COLUMN_NAME = :column_name"
                    ),
                    {"column_name": column_name},
                ).scalar()
                if not has_column:
                    conn.execute(text(f"ALTER TABLE report_templates ADD COLUMN {column_name} {definition}"))
            # 历史模板只归属到显式配置的管理员；无法确认时保留无主状态。
            default_template_owner = _configured_admin_id(conn)
            if default_template_owner:
                conn.execute(
                    text("UPDATE report_templates SET created_by = :user_id WHERE created_by IS NULL"),
                    {"user_id": default_template_owner},
                )
            has_folder_id = conn.execute(
                text(
                    "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'report_documents' AND COLUMN_NAME = 'folder_id'"
                )
            ).scalar()
            if not has_folder_id:
                conn.execute(text("ALTER TABLE report_documents ADD COLUMN folder_id INT NULL AFTER report_type"))
            has_editor_config = conn.execute(
                text(
                    "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'report_documents' AND COLUMN_NAME = 'editor_config'"
                )
            ).scalar()
            if not has_editor_config:
                conn.execute(text("ALTER TABLE report_documents ADD COLUMN editor_config JSON NULL AFTER source_query"))
            html_snapshot_type = conn.execute(
                text(
                    "SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'report_documents' AND COLUMN_NAME = 'html_snapshot'"
                )
            ).scalar()
            if html_snapshot_type and html_snapshot_type.lower() != "longtext":
                conn.execute(text("ALTER TABLE report_documents MODIFY COLUMN html_snapshot LONGTEXT NULL"))

            # 统计字典排除项：从全局改为按账号隔离
            dict_table = "statistics_dictionary_exclusions"
            has_dict_table = conn.execute(
                text(
                    "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name"
                ),
                {"table_name": dict_table},
            ).scalar()
            if has_dict_table:
                default_owner = _configured_admin_id(conn)
                if default_owner:
                    conn.execute(
                        text(
                            f"UPDATE {dict_table} SET created_by = :user_id "
                            "WHERE created_by IS NULL"
                        ),
                        {"user_id": default_owner},
                    )
                # 找不到显式配置的管理员时保留无主历史数据，避免启动迁移误删。
                created_by_nullable = conn.execute(
                    text(
                        "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name "
                        "AND COLUMN_NAME = 'created_by'"
                    ),
                    {"table_name": dict_table},
                ).scalar()
                if default_owner and created_by_nullable and str(created_by_nullable).upper() == "YES":
                    remaining_unowned = conn.execute(
                        text(f"SELECT COUNT(*) FROM {dict_table} WHERE created_by IS NULL")
                    ).scalar()
                    if not remaining_unowned:
                        conn.execute(
                            text(f"ALTER TABLE {dict_table} MODIFY COLUMN created_by INT NOT NULL")
                        )
                new_uq = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name "
                        "AND INDEX_NAME = 'uq_statistics_dictionary_exclusion_user'"
                    ),
                    {"table_name": dict_table},
                ).scalar()
                if not new_uq:
                    conn.execute(
                        text(
                            f"ALTER TABLE {dict_table} "
                            "ADD UNIQUE INDEX uq_statistics_dictionary_exclusion_user "
                            "(created_by, source, level, code)"
                        )
                    )

    from app.repositories.user_repository import UserRepository

    with SessionLocal() as db:
        UserRepository(db).ensure_seed_data()
        # 社区组织映射直接使用 community_org_mappings 表，不再从 Excel 灌库


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
