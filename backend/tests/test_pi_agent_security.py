import os
from pathlib import Path

from app.core.config import Settings
from app.services.pi_agent_service import _minimal_environment, _pi_args


def test_pi_agent_disabled_by_default():
    assert Settings(_env_file=None).pi_agent_enabled is False


def test_pi_command_is_read_only_and_has_no_approve(monkeypatch):
    monkeypatch.setattr("app.services.pi_agent_service._pi_command", lambda: "pi")
    args = _pi_args("hello")
    assert "--approve" not in args
    assert "--no-approve" in args
    assert "--tools" in args
    assert args[args.index("--tools") + 1] == "read,grep,find,ls"


def test_pi_environment_does_not_inherit_application_secrets(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "secret-db")
    monkeypatch.setenv("JWT_SECRET_KEY", "secret-jwt")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret-admin")
    monkeypatch.setenv("LLM_API_KEY", "secret-llm")
    monkeypatch.setenv("PI_OFFLINE", "1")
    env = _minimal_environment(tmp_path)
    assert env.get("PI_OFFLINE") == "1"
    assert not any(name in env for name in ("DATABASE_URL", "JWT_SECRET_KEY", "ADMIN_PASSWORD", "LLM_API_KEY"))
    inherited = {name: os.environ.get(name) for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP")}
    for name in inherited:
        assert Path(env[name]).is_relative_to(tmp_path)
        assert env[name] != inherited[name]
