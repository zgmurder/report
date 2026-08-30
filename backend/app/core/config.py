from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "警情智能报告"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_prefix: str = "/api/v1"

    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/report?charset=utf8mb4"
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    jwt_secret_key: str = "please-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    admin_username: str = "admin"
    admin_password: str = "admin123"
    admin_display_name: str = "系统管理员"

    llm_provider: str = "mock"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    # The Pi CLI is not an application sandbox. Keep the endpoint opt-in even
    # after the in-process restrictions below; production should add OS-level isolation.
    pi_agent_enabled: bool = False
    # Deployment acknowledgement only: set this after the Pi process is placed
    # in an external container/VM or a low-privilege OS sandbox. The application
    # itself cannot confine absolute-path reads by the CLI.
    pi_agent_sandboxed: bool = False
    pi_agent_timeout_seconds: int = 300
    pi_agent_max_concurrency: int = 1

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def reject_weak_production_defaults(self):
        if self.app_env.strip().lower() in {"dev", "test"}:
            return self

        weak_values: list[str] = []
        if self.jwt_secret_key == "please-change-me":
            weak_values.append("JWT_SECRET_KEY")
        if self.admin_password == "admin123":
            weak_values.append("ADMIN_PASSWORD")
        if self.database_url == "mysql+pymysql://root:password@127.0.0.1:3306/report?charset=utf8mb4":
            weak_values.append("DATABASE_URL")
        if weak_values:
            names = ", ".join(weak_values)
            raise ValueError(f"非 dev/test 环境禁止使用默认弱配置，请修改: {names}")
        if self.pi_agent_enabled and not self.pi_agent_sandboxed:
            raise ValueError("非 dev/test 环境启用 Pi Agent 必须显式设置 PI_AGENT_SANDBOXED=true")
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
