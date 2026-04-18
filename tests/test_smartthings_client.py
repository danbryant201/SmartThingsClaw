import json
import os
import urllib.error
from unittest.mock import MagicMock, call, patch

import pytest

from conftest import mock_response
from smartthings_client import (
    AuthError,
    NotFoundError,
    RateLimitError,
    ServerError,
    SmartThingsClient,
    SmartThingsError,
)


# ── __init__ ────────────────────────────────────────────────────────────────

def test_init_token_from_arg():
    client = SmartThingsClient("my-token")
    assert client._token == "my-token"


def test_init_token_from_env(monkeypatch):
    monkeypatch.setenv("SMARTTHINGS_TOKEN", "env-token")
    client = SmartThingsClient()
    assert client._token == "env-token"


def test_init_no_token_raises(monkeypatch):
    monkeypatch.delenv("SMARTTHINGS_TOKEN", raising=False)
    with pytest.raises(AuthError):
        SmartThingsClient()


# ── _request ────────────────────────────────────────────────────────────────

def test_request_correct_url(st_client, mock_urlopen):
    mock_urlopen.return_value = mock_response({"ok": True})
    st_client._request("GET", "/devices")
    req = mock_urlopen.call_args[0][0]
    assert req.full_url == "https://api.smartthings.com/v1/devices"


def test_request_query_params(st_client, mock_urlopen):
    mock_urlopen.return_value = mock_response({})
    st_client._request("GET", "/devices", params={"locationId": "loc-1"})
    req = mock_urlopen.call_args[0][0]
    assert "locationId=loc-1" in req.full_url


def test_request_authorization_header(st_client, mock_urlopen):
    mock_urlopen.return_value = mock_response({})
    st_client._request("GET", "/devices")
    req = mock_urlopen.call_args[0][0]
    assert req.get_header("Authorization") == "Bearer test-token"


def test_request_json_body_serialized(st_client, mock_urlopen):
    mock_urlopen.return_value = mock_response({})
    st_client._request("POST", "/devices/abc/commands", body={"commands": []})
    req = mock_urlopen.call_args[0][0]
    assert json.loads(req.data) == {"commands": []}


def test_request_returns_parsed_json(st_client, mock_urlopen):
    mock_urlopen.return_value = mock_response({"deviceId": "abc"})
    result = st_client._request("GET", "/devices/abc")
    assert result == {"deviceId": "abc"}


def _http_error(code: int) -> urllib.error.HTTPError:
    err = urllib.error.HTTPError(url="", code=code, msg="err", hdrs={}, fp=None)
    err.read = lambda: b""
    return err


def test_request_401_raises_auth_error(st_client, mock_urlopen):
    mock_urlopen.side_effect = _http_error(401)
    with pytest.raises(AuthError) as exc_info:
        st_client._request("GET", "/devices")
    assert exc_info.value.status_code == 401


def test_request_404_raises_not_found(st_client, mock_urlopen):
    mock_urlopen.side_effect = _http_error(404)
    with pytest.raises(NotFoundError) as exc_info:
        st_client._request("GET", "/devices/missing")
    assert exc_info.value.status_code == 404


def test_request_429_raises_rate_limit(st_client, mock_urlopen):
    mock_urlopen.side_effect = _http_error(429)
    with pytest.raises(RateLimitError) as exc_info:
        st_client._request("GET", "/devices")
    assert exc_info.value.status_code == 429


def test_request_500_raises_server_error(st_client, mock_urlopen):
    mock_urlopen.side_effect = _http_error(500)
    with pytest.raises(ServerError) as exc_info:
        st_client._request("GET", "/devices")
    assert exc_info.value.status_code == 500


def test_request_503_raises_server_error(st_client, mock_urlopen):
    mock_urlopen.side_effect = _http_error(503)
    with pytest.raises(ServerError):
        st_client._request("GET", "/devices")


def test_request_400_raises_base_error(st_client, mock_urlopen):
    mock_urlopen.side_effect = _http_error(400)
    with pytest.raises(SmartThingsError) as exc_info:
        st_client._request("GET", "/devices")
    assert type(exc_info.value) is SmartThingsError


def test_request_url_error_raises_smartthings_error(st_client, mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError(reason="connection refused")
    with pytest.raises(SmartThingsError, match="Network error"):
        st_client._request("GET", "/devices")


# ── _paginate ───────────────────────────────────────────────────────────────

def test_paginate_single_page(st_client, mock_urlopen):
    page = {"items": [{"id": "a"}, {"id": "b"}], "_links": {}}
    mock_urlopen.return_value = mock_response(page)
    result = st_client._paginate("/devices")
    assert result == [{"id": "a"}, {"id": "b"}]


def test_paginate_follows_next_link(st_client, mock_urlopen):
    page1 = {
        "items": [{"id": "a"}],
        "_links": {"next": {"href": "https://api.smartthings.com/v1/devices?page=2"}},
    }
    page2 = {"items": [{"id": "b"}], "_links": {}}
    mock_urlopen.side_effect = [mock_response(page1), mock_response(page2)]
    result = st_client._paginate("/devices")
    assert result == [{"id": "a"}, {"id": "b"}]
    assert mock_urlopen.call_count == 2


def test_paginate_passes_params_on_first_page_only(st_client, mock_urlopen):
    page1 = {
        "items": [{"id": "a"}],
        "_links": {"next": {"href": "https://api.smartthings.com/v1/devices?page=2"}},
    }
    page2 = {"items": [], "_links": {}}
    mock_urlopen.side_effect = [mock_response(page1), mock_response(page2)]
    st_client._paginate("/devices", params={"locationId": "loc-1"})
    first_req = mock_urlopen.call_args_list[0][0][0]
    second_req = mock_urlopen.call_args_list[1][0][0]
    assert "locationId=loc-1" in first_req.full_url
    assert "locationId" not in second_req.full_url.split("?")[0]


def test_paginate_empty_items(st_client, mock_urlopen):
    mock_urlopen.return_value = mock_response({"items": [], "_links": {}})
    assert st_client._paginate("/devices") == []


# ── High-level methods ───────────────────────────────────────────────────────

def test_list_devices_calls_paginate(st_client):
    with patch.object(st_client, "_paginate", return_value=[]) as mock_pag:
        st_client.list_devices()
        mock_pag.assert_called_once_with("/devices")


def test_get_device_calls_correct_path(st_client):
    with patch.object(st_client, "_request", return_value={}) as mock_req:
        st_client.get_device("abc-123")
        mock_req.assert_called_once_with("GET", "/devices/abc-123")


def test_get_device_status_calls_correct_path(st_client):
    with patch.object(st_client, "_request", return_value={}) as mock_req:
        st_client.get_device_status("abc-123")
        mock_req.assert_called_once_with("GET", "/devices/abc-123/status")
