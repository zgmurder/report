import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_weak_defaults():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            app_env="prod",
            jwt_secret_key="please-change-me",
            admin_password="admin123",
            database_url="mysql+pymysql://root:password@127.0.0.1:3306/report?charset=utf8mb4",
        )

    message = str(exc_info.value)
    assert "JWT_SECRET_KEY" in message
    assert "ADMIN_PASSWORD" in message
    assert "DATABASE_URL" in message


def test_production_rejects_enabled_pi_without_sandbox_acknowledgement():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            app_env="prod",
            jwt_secret_key="strong-secret",
            admin_password="strong-password",
            database_url="mysql+pymysql://app:secret@db/report",
            pi_agent_enabled=True,
            pi_agent_sandboxed=False,
        )
    assert "PI_AGENT_SANDBOXED" in str(exc_info.value)


def test_development_keeps_local_defaults():
    settings = Settings(_env_file=None, app_env="dev")

    assert settings.jwt_secret_key == "please-change-me"
