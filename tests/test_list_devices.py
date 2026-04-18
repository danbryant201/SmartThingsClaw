import json
from unittest.mock import MagicMock, patch

import pytest

from list_devices import normalise_device, main
from smartthings_client import AuthError, RateLimitError, ServerError, SmartThingsError


# ── normalise_device ─────────────────────────────────────────────────────────

def test_normalise_full_device(sample_device):
    result = normalise_device(sample_device)
    assert result["deviceId"] == "device-abc"
    assert result["label"] == "Living Room Light"
    assert result["name"] == "LIFX Color Bulb"
    assert result["type"] == "LAN"
    assert result["roomId"] == "room-xyz"
    assert result["components"] == [{"id": "main", "capabilities": ["switch", "switchLevel"]}]


def test_normalise_missing_room_id():
    device = {"deviceId": "x", "components": []}
    assert normalise_device(device)["roomId"] == ""


def test_normalise_missing_label_and_name():
    device = {"deviceId": "x", "components": []}
    result = normalise_device(device)
    assert result["label"] == ""
    assert result["name"] == ""


def test_normalise_multiple_components():
    device = {
        "deviceId": "x",
        "components": [
            {"id": "main", "capabilities": [{"id": "switch", "version": 1}]},
            {"id": "outlet2", "capabilities": [{"id": "switch", "version": 1}, {"id": "powerMeter", "version": 1}]},
        ],
    }
    result = normalise_device(device)
    assert len(result["components"]) == 2
    assert result["components"][0] == {"id": "main", "capabilities": ["switch"]}
    assert result["components"][1] == {"id": "outlet2", "capabilities": ["switch", "powerMeter"]}


def test_normalise_capability_ids_extracted():
    device = {
        "deviceId": "x",
        "components": [
            {"id": "main", "capabilities": [{"id": "lock", "version": 1}, {"id": "battery", "version": 2}]},
        ],
    }
    caps = normalise_device(device)["components"][0]["capabilities"]
    assert caps == ["lock", "battery"]


def test_normalise_empty_components():
    device = {"deviceId": "x", "components": []}
    assert normalise_device(device)["components"] == []


def test_normalise_component_no_capabilities():
    device = {"deviceId": "x", "components": [{"id": "main", "capabilities": []}]}
    assert normalise_device(device)["components"] == [{"id": "main", "capabilities": []}]


# ── main() ───────────────────────────────────────────────────────────────────

def _mock_client(devices=None):
    client = MagicMock()
    client.list_devices.return_value = devices or []
    return client


def test_main_success_stdout(capsys, sample_device):
    with patch("list_devices.SmartThingsClient", return_value=_mock_client([sample_device])):
        main()
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert isinstance(parsed, list)
    assert parsed[0]["deviceId"] == "device-abc"


def test_main_success_no_exit(sample_device):
    with patch("list_devices.SmartThingsClient", return_value=_mock_client([sample_device])):
        main()  # should not raise SystemExit


def test_main_auth_error_exits_2(capsys):
    client = MagicMock()
    client.list_devices.side_effect = AuthError("bad token")
    with patch("list_devices.SmartThingsClient", return_value=client):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 2


def test_main_rate_limit_exits_4():
    client = MagicMock()
    client.list_devices.side_effect = RateLimitError("rate limited")
    with patch("list_devices.SmartThingsClient", return_value=client):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 4


def test_main_server_error_exits_5():
    client = MagicMock()
    client.list_devices.side_effect = ServerError("server error")
    with patch("list_devices.SmartThingsClient", return_value=client):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 5


def test_main_generic_smartthings_error_exits_1():
    client = MagicMock()
    client.list_devices.side_effect = SmartThingsError("unknown")
    with patch("list_devices.SmartThingsClient", return_value=client):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1


def test_main_unexpected_exception_exits_1():
    client = MagicMock()
    client.list_devices.side_effect = RuntimeError("unexpected")
    with patch("list_devices.SmartThingsClient", return_value=client):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code == 1
