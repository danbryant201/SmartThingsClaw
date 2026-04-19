import json
import time
from unittest.mock import MagicMock, call, patch

import pytest

from setup import _ensure_cli_installed, check_config, main, register_app


# ── check_config ─────────────────────────────────────────────────────────────

def test_check_no_credentials(monkeypatch):
    for key in ["SMARTTHINGS_CLIENT_ID", "SMARTTHINGS_CLIENT_SECRET",
                "SMARTTHINGS_ACCESS_TOKEN", "SMARTTHINGS_REFRESH_TOKEN",
                "SMARTTHINGS_TOKEN_EXPIRES_AT"]:
        monkeypatch.delenv(key, raising=False)
    result = check_config()
    assert result["client_id_set"] is False
    assert result["client_secret_set"] is False
    assert result["next_step"] == "register_app"
    assert result["ready"] is False


def test_check_only_client_id_set(monkeypatch):
    monkeypatch.setenv("SMARTTHINGS_CLIENT_ID", "cid")
    monkeypatch.delenv("SMARTTHINGS_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("SMARTTHINGS_ACCESS_TOKEN", raising=False)
    result = check_config()
    assert result["next_step"] == "register_app"


def test_check_creds_set_no_token(monkeypatch):
    monkeypatch.setenv("SMARTTHINGS_CLIENT_ID", "cid")
    monkeypatch.setenv("SMARTTHINGS_CLIENT_SECRET", "csecret")
    monkeypatch.delenv("SMARTTHINGS_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("SMARTTHINGS_TOKEN_EXPIRES_AT", raising=False)
    result = check_config()
    assert result["next_step"] == "authorize"
    assert result["ready"] is False


def test_check_token_expired(monkeypatch):
    monkeypatch.setenv("SMARTTHINGS_CLIENT_ID", "cid")
    monkeypatch.setenv("SMARTTHINGS_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("SMARTTHINGS_ACCESS_TOKEN", "old-token")
    monkeypatch.setenv("SMARTTHINGS_TOKEN_EXPIRES_AT", str(int(time.time()) - 1))
    result = check_config()
    assert result["token_expired"] is True
    assert result["next_step"] == "authorize"


def test_check_ready(monkeypatch):
    monkeypatch.setenv("SMARTTHINGS_CLIENT_ID", "cid")
    monkeypatch.setenv("SMARTTHINGS_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("SMARTTHINGS_ACCESS_TOKEN", "valid-token")
    monkeypatch.setenv("SMARTTHINGS_TOKEN_EXPIRES_AT", str(int(time.time()) + 3600))
    result = check_config()
    assert result["next_step"] == "ready"
    assert result["ready"] is True
    assert result["token_expired"] is False


def test_check_all_fields_present(monkeypatch):
    monkeypatch.setenv("SMARTTHINGS_CLIENT_ID", "cid")
    monkeypatch.setenv("SMARTTHINGS_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("SMARTTHINGS_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("SMARTTHINGS_REFRESH_TOKEN", "ref")
    monkeypatch.setenv("SMARTTHINGS_TOKEN_EXPIRES_AT", str(int(time.time()) + 3600))
    result = check_config()
    assert result["client_id_set"] is True
    assert result["client_secret_set"] is True
    assert result["access_token_set"] is True
    assert result["refresh_token_set"] is True


# ── main() check subcommand ───────────────────────────────────────────────────

def test_main_check_outputs_json(monkeypatch, capsys):
    for key in ["SMARTTHINGS_CLIENT_ID", "SMARTTHINGS_CLIENT_SECRET",
                "SMARTTHINGS_ACCESS_TOKEN", "SMARTTHINGS_REFRESH_TOKEN",
                "SMARTTHINGS_TOKEN_EXPIRES_AT"]:
        monkeypatch.delenv(key, raising=False)
    with patch("sys.argv", ["setup.py", "check"]):
        main()
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "next_step" in parsed
    assert "ready" in parsed


# ── main() save-creds subcommand ──────────────────────────────────────────────

def test_main_save_creds_writes_file(tmp_path, capsys):
    env_file = tmp_path / ".env"
    with patch("sys.argv", ["setup.py", "save-creds", "my-id", "my-secret"]):
        with patch("setup.save_credentials") as mock_save:
            with patch("setup.ENV_FILE", str(env_file)):
                main()
    mock_save.assert_called_once_with("my-id", "my-secret")


def test_main_save_creds_missing_args(capsys):
    with patch("sys.argv", ["setup.py", "save-creds", "only-one-arg"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0


def test_main_no_subcommand_exits(capsys):
    with patch("sys.argv", ["setup.py"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0


# ── _ensure_cli_installed ──────────────────────────────────────────────────────

def test_ensure_cli_already_installed():
    ok = MagicMock(returncode=0)
    with patch("setup.subprocess.run", return_value=ok) as mock_run:
        _ensure_cli_installed()
    mock_run.assert_called_once_with(["smartthings", "--version"], capture_output=True)


def test_ensure_cli_installs_when_missing():
    missing = MagicMock(returncode=1)
    installed = MagicMock(returncode=0)
    with patch("setup.subprocess.run", side_effect=[missing, installed]) as mock_run:
        _ensure_cli_installed()
    assert mock_run.call_count == 2
    assert mock_run.call_args_list[1] == call(
        ["npm", "install", "-g", "@smartthings/cli"],
        capture_output=True,
        text=True,
    )


def test_ensure_cli_raises_on_npm_failure():
    missing = MagicMock(returncode=1)
    npm_fail = MagicMock(returncode=1, stderr="npm error")
    with patch("setup.subprocess.run", side_effect=[missing, npm_fail]):
        with pytest.raises(RuntimeError, match="Failed to install SmartThings CLI"):
            _ensure_cli_installed()


# ── register_app ──────────────────────────────────────────────────────────────

def _cli_response(client_id="cli-id", client_secret="cli-secret"):
    return json.dumps({"oauthClientId": client_id, "oauthClientSecret": client_secret})


def test_register_app_saves_credentials(tmp_path):
    env_file = tmp_path / ".env"
    cli_ok = MagicMock(returncode=0, stdout=_cli_response())
    with patch("setup._ensure_cli_installed"):
        with patch("setup.subprocess.run", return_value=cli_ok):
            result = register_app("my-pat", env_path=str(env_file))
    assert result["client_id"] == "cli-id"
    assert result["client_secret"] == "cli-secret"
    content = env_file.read_text()
    assert "SMARTTHINGS_CLIENT_ID=cli-id" in content
    assert "SMARTTHINGS_CLIENT_SECRET=cli-secret" in content


def test_register_app_passes_pat_and_json_flag(tmp_path):
    env_file = tmp_path / ".env"
    captured = []

    def capture(*args, **kwargs):
        captured.append(args[0])
        return MagicMock(returncode=0, stdout=_cli_response())

    with patch("setup._ensure_cli_installed"):
        with patch("setup.subprocess.run", side_effect=capture):
            register_app("secret-pat", env_path=str(env_file))

    cmd = captured[0]
    assert "--token" in cmd
    assert "secret-pat" in cmd
    assert "--json" in cmd


def test_register_app_raises_on_cli_error(tmp_path):
    env_file = tmp_path / ".env"
    cli_fail = MagicMock(returncode=1, stderr="some error", stdout="")
    with patch("setup._ensure_cli_installed"):
        with patch("setup.subprocess.run", return_value=cli_fail):
            with pytest.raises(RuntimeError, match="SmartThings CLI error"):
                register_app("pat", env_path=str(env_file))


def test_register_app_raises_on_non_json_output(tmp_path):
    env_file = tmp_path / ".env"
    cli_bad = MagicMock(returncode=0, stdout="not json at all")
    with patch("setup._ensure_cli_installed"):
        with patch("setup.subprocess.run", return_value=cli_bad):
            with pytest.raises(RuntimeError, match="not JSON"):
                register_app("pat", env_path=str(env_file))


def test_register_app_raises_when_credentials_missing(tmp_path):
    env_file = tmp_path / ".env"
    cli_no_creds = MagicMock(returncode=0, stdout=json.dumps({"something": "else"}))
    with patch("setup._ensure_cli_installed"):
        with patch("setup.subprocess.run", return_value=cli_no_creds):
            with pytest.raises(RuntimeError, match="Credentials missing"):
                register_app("pat", env_path=str(env_file))


def test_register_app_uses_custom_name(tmp_path):
    env_file = tmp_path / ".env"
    written_configs = []

    def capture(*args, **kwargs):
        import json as _json
        config_arg = [a for a in args[0] if a.endswith(".json")]
        if config_arg:
            with open(config_arg[0]) as f:
                written_configs.append(_json.load(f))
        return MagicMock(returncode=0, stdout=_cli_response())

    with patch("setup._ensure_cli_installed"):
        with patch("setup.subprocess.run", side_effect=capture):
            register_app("pat", name="MyApp", env_path=str(env_file))

    assert written_configs[0]["displayName"] == "MyApp"


# ── main() register-app subcommand ────────────────────────────────────────────

def test_main_register_app_prints_json(tmp_path, capsys):
    with patch("sys.argv", ["setup.py", "register-app", "--pat", "tok"]):
        with patch("setup.register_app", return_value={"client_id": "cid", "client_secret": "cs"}):
            main()
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["status"] == "ok"
    assert parsed["client_id"] == "cid"


def test_main_register_app_exits_1_on_error(capsys):
    with patch("sys.argv", ["setup.py", "register-app", "--pat", "tok"]):
        with patch("setup.register_app", side_effect=RuntimeError("oops")):
            with pytest.raises(SystemExit) as exc_info:
                main()
    assert exc_info.value.code == 1


def test_main_register_app_requires_pat(capsys):
    with patch("sys.argv", ["setup.py", "register-app"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0
