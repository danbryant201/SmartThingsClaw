import base64
import json
import time
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from auth import (
    AUTH_URL,
    DEFAULT_SCOPES,
    REDIRECT_URI,
    build_auth_url,
    exchange_code,
    refresh_access_token,
    run_refresh,
    save_tokens,
)
from conftest import mock_response


# ── build_auth_url ───────────────────────────────────────────────────────────

def test_build_auth_url_contains_client_id():
    url = build_auth_url("my-client-id")
    assert "client_id=my-client-id" in url


def test_build_auth_url_base_is_auth_url():
    url = build_auth_url("cid")
    assert url.startswith(AUTH_URL)


def test_build_auth_url_includes_redirect_uri():
    url = build_auth_url("cid")
    import urllib.parse
    assert urllib.parse.quote(REDIRECT_URI, safe="") in url or "redirect_uri=" in url


def test_build_auth_url_response_type_code():
    url = build_auth_url("cid")
    assert "response_type=code" in url


def test_build_auth_url_custom_scopes():
    url = build_auth_url("cid", scopes="r:devices:*")
    assert "r%3Adevices%3A" in url or "r:devices:" in url


# ── exchange_code ────────────────────────────────────────────────────────────

def _token_response(extra=None):
    data = {
        "access_token": "new-access",
        "refresh_token": "new-refresh",
        "expires_in": 86400,
        "scope": "r:devices:*",
    }
    if extra:
        data.update(extra)
    return data


def test_exchange_code_returns_tokens():
    with patch("auth.urllib.request.urlopen", return_value=mock_response(_token_response())):
        tokens = exchange_code("cid", "csecret", "auth-code")
    assert tokens["access_token"] == "new-access"
    assert tokens["refresh_token"] == "new-refresh"


def test_exchange_code_sets_expires_at():
    before = int(time.time())
    with patch("auth.urllib.request.urlopen", return_value=mock_response(_token_response())):
        tokens = exchange_code("cid", "csecret", "auth-code")
    assert tokens["expires_at"] >= before + 86400


def test_exchange_code_uses_basic_auth():
    captured = []

    def capture(req):
        captured.append(req)
        return mock_response(_token_response())

    with patch("auth.urllib.request.urlopen", side_effect=capture):
        exchange_code("cid", "csecret", "auth-code")

    auth_header = captured[0].get_header("Authorization")
    expected = "Basic " + base64.b64encode(b"cid:csecret").decode()
    assert auth_header == expected


def test_exchange_code_sends_correct_grant_type():
    captured = []

    def capture(req):
        captured.append(req)
        return mock_response(_token_response())

    with patch("auth.urllib.request.urlopen", side_effect=capture):
        exchange_code("cid", "csecret", "auth-code")

    body = captured[0].data.decode()
    assert "grant_type=authorization_code" in body
    assert "code=auth-code" in body


# ── refresh_access_token ─────────────────────────────────────────────────────

def test_refresh_returns_new_tokens():
    with patch("auth.urllib.request.urlopen", return_value=mock_response(_token_response())):
        tokens = refresh_access_token("cid", "csecret", "old-refresh")
    assert tokens["access_token"] == "new-access"


def test_refresh_sets_expires_at():
    before = int(time.time())
    with patch("auth.urllib.request.urlopen", return_value=mock_response(_token_response())):
        tokens = refresh_access_token("cid", "csecret", "old-refresh")
    assert tokens["expires_at"] >= before + 86400


def test_refresh_uses_basic_auth():
    captured = []

    def capture(req):
        captured.append(req)
        return mock_response(_token_response())

    with patch("auth.urllib.request.urlopen", side_effect=capture):
        refresh_access_token("cid", "csecret", "old-refresh")

    auth_header = captured[0].get_header("Authorization")
    expected = "Basic " + base64.b64encode(b"cid:csecret").decode()
    assert auth_header == expected


def test_refresh_sends_correct_grant_type():
    captured = []

    def capture(req):
        captured.append(req)
        return mock_response(_token_response())

    with patch("auth.urllib.request.urlopen", side_effect=capture):
        refresh_access_token("cid", "csecret", "old-refresh")

    body = captured[0].data.decode()
    assert "grant_type=refresh_token" in body
    assert "refresh_token=old-refresh" in body


# ── save_tokens ──────────────────────────────────────────────────────────────

def test_save_tokens_creates_file(tmp_path):
    env_file = tmp_path / ".env"
    tokens = {"access_token": "acc", "refresh_token": "ref", "expires_at": 9999}
    save_tokens(tokens, env_path=str(env_file))
    content = env_file.read_text()
    assert "SMARTTHINGS_ACCESS_TOKEN=acc" in content
    assert "SMARTTHINGS_REFRESH_TOKEN=ref" in content
    assert "SMARTTHINGS_TOKEN_EXPIRES_AT=9999" in content


def test_save_tokens_updates_existing_keys(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("SMARTTHINGS_ACCESS_TOKEN=old\nOTHER_VAR=keep\n")
    save_tokens({"access_token": "new", "refresh_token": "ref", "expires_at": 1}, env_path=str(env_file))
    content = env_file.read_text()
    assert "SMARTTHINGS_ACCESS_TOKEN=new" in content
    assert "SMARTTHINGS_ACCESS_TOKEN=old" not in content
    assert "OTHER_VAR=keep" in content


def test_save_tokens_appends_missing_keys(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("SOME_OTHER=value\n")
    save_tokens({"access_token": "acc", "refresh_token": "ref", "expires_at": 1}, env_path=str(env_file))
    content = env_file.read_text()
    assert "SMARTTHINGS_ACCESS_TOKEN=acc" in content
    assert "SOME_OTHER=value" in content


def test_save_tokens_preserves_unrelated_lines(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SMARTTHINGS_CLIENT_ID=my-id\nSMARTTHINGS_CLIENT_SECRET=my-secret\n"
    )
    save_tokens({"access_token": "a", "refresh_token": "r", "expires_at": 1}, env_path=str(env_file))
    content = env_file.read_text()
    assert "SMARTTHINGS_CLIENT_ID=my-id" in content
    assert "SMARTTHINGS_CLIENT_SECRET=my-secret" in content


# ── run_refresh ──────────────────────────────────────────────────────────────

def test_run_refresh_exits_1_without_client_id(monkeypatch):
    monkeypatch.delenv("SMARTTHINGS_CLIENT_ID", raising=False)
    monkeypatch.delenv("SMARTTHINGS_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("SMARTTHINGS_REFRESH_TOKEN", "tok")
    with pytest.raises(SystemExit) as exc_info:
        run_refresh()
    assert exc_info.value.code == 1


def test_run_refresh_exits_1_without_refresh_token(monkeypatch):
    monkeypatch.setenv("SMARTTHINGS_CLIENT_ID", "cid")
    monkeypatch.setenv("SMARTTHINGS_CLIENT_SECRET", "csecret")
    monkeypatch.delenv("SMARTTHINGS_REFRESH_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        run_refresh()
    assert exc_info.value.code == 1


def test_run_refresh_exits_2_on_401(monkeypatch, tmp_path):
    monkeypatch.setenv("SMARTTHINGS_CLIENT_ID", "cid")
    monkeypatch.setenv("SMARTTHINGS_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("SMARTTHINGS_REFRESH_TOKEN", "expired")
    err = urllib.error.HTTPError(url="", code=401, msg="Unauthorized", hdrs={}, fp=None)
    err.read = lambda: b""
    with patch("auth.urllib.request.urlopen", side_effect=err):
        with pytest.raises(SystemExit) as exc_info:
            run_refresh()
    assert exc_info.value.code == 2


def test_run_refresh_saves_tokens_on_success(monkeypatch, tmp_path):
    monkeypatch.setenv("SMARTTHINGS_CLIENT_ID", "cid")
    monkeypatch.setenv("SMARTTHINGS_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("SMARTTHINGS_REFRESH_TOKEN", "valid-refresh")
    env_file = tmp_path / ".env"
    with patch("auth.urllib.request.urlopen", return_value=mock_response(_token_response())):
        with patch("auth.save_tokens") as mock_save:
            run_refresh()
    mock_save.assert_called_once()
    saved = mock_save.call_args[0][0]
    assert saved["access_token"] == "new-access"
