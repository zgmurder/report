from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


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
            for table_name in ("report_documents", "report_folders", "report_templates", "stat_components", "data_source_configs", "departments", "sys_users", "statistics_dictionary_exclusions"):
                conn.execute(text(f"ALTER TABLE {table_name} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            template_columns = {
                "original_filename": "VARCHAR(255) NULL",
                "file_path": "VARCHAR(500) NULL",
                "file_size": "INT NULL",
                "mime_type": "VARCHAR(150) NULL",
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

    from app.repositories.user_repository import UserRepository

    with SessionLocal() as db:
        UserRepository(db).ensure_seed_data()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
