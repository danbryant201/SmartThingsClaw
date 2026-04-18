import json
import os
from unittest.mock import MagicMock, patch

import pytest

from smartthings_client import SmartThingsClient


def mock_response(data: dict | list) -> MagicMock:
    body = json.dumps(data).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


@pytest.fixture
def fake_token(monkeypatch):
    monkeypatch.setenv("SMARTTHINGS_ACCESS_TOKEN", "test-access-token")


@pytest.fixture
def fake_oauth_env(monkeypatch):
    monkeypatch.setenv("SMARTTHINGS_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("SMARTTHINGS_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("SMARTTHINGS_ACCESS_TOKEN", "test-access-token")
    monkeypatch.setenv("SMARTTHINGS_REFRESH_TOKEN", "test-refresh-token")
    monkeypatch.setenv("SMARTTHINGS_TOKEN_EXPIRES_AT", "9999999999")


@pytest.fixture
def mock_urlopen():
    with patch("smartthings_client.urllib.request.urlopen") as m:
        yield m


@pytest.fixture
def st_client():
    return SmartThingsClient("test-access-token")


@pytest.fixture
def sample_device():
    return {
        "deviceId": "device-abc",
        "label": "Living Room Light",
        "name": "LIFX Color Bulb",
        "type": "LAN",
        "roomId": "room-xyz",
        "components": [
            {
                "id": "main",
                "capabilities": [
                    {"id": "switch", "version": 1},
                    {"id": "switchLevel", "version": 1},
                ],
            }
        ],
    }


@pytest.fixture
def sample_status():
    return {
        "components": {
            "main": {
                "switch": {"switch": {"value": "on", "timestamp": "2026-04-18T00:00:00Z"}},
                "switchLevel": {"level": {"value": 75, "unit": "%", "timestamp": "2026-04-18T00:00:00Z"}},
            }
        }
    }
