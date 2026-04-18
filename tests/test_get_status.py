import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from get_status import fetch_single, main
from smartthings_client import AuthError, NotFoundError, RateLimitError, ServerError, SmartThingsError


# ── fetch_single ─────────────────────────────────────────────────────────────

def test_fetch_single_output_shape(sample_device, sample_status):
    client = MagicMock()
    client.get_device.return_value = sample_device
    client.get_device_status.return_value = sample_status
    result = fetch_single(client, "device-abc")
    assert result["deviceId"] == "device-abc"
    assert result["label"] == "Living Room Light"
    assert "status" in result


def test_fetch_single_uses_components_key(sample_device, sample_status):
    client = MagicMock()
    client.get_device.return_value = sample_device
    client.get_device_status.return_value = sample_status
    result = fetch_single(client, "device-abc")
    assert result["status"] == sample_status["components"]


def test_fetch_single_fallback_when_no_components_key(sample_device):
    raw_status = {"switch": {"switch": {"value": "on"}}}
    client = MagicMock()
    client.get_device.return_value = sample_device
    client.get_device_status.return_value = raw_status
    result = fetch_single(client, "device-abc")
    assert result["status"] == raw_status


# ── main() with --device-id ──────────────────────────────────────────────────

def _mock_client_for_single(sample_device, sample_status):
    client = MagicMock()
    client.get_device.return_value = sample_device
    client.get_device_status.return_value = sample_status
    return client


def test_main_device_id_stdout_is_valid_json(capsys, sample_device, sample_status):
    with patch("get_status.SmartThingsClient", return_value=_mock_client_for_single(sample_device, sample_status)):
        with patch("sys.argv", ["get_status.py", "--device-id", "device-abc"]):
            main()
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["deviceId"] == "device-abc"


def test_main_device_id_calls_fetch_once(sample_device, sample_status, capsys):
    client = _mock_client_for_single(sample_device, sample_status)
    with patch("get_status.SmartThingsClient", return_value=client):
        with patch("sys.argv", ["get_status.py", "--device-id", "device-abc"]):
            main()
    client.get_device.assert_called_once_with("device-abc")
    client.get_device_status.assert_called_once_with("device-abc")


# ── main() with --all ────────────────────────────────────────────────────────

def test_main_all_stdout_is_json_array(capsys, sample_device, sample_status):
    client = MagicMock()
    client.list_devices.return_value = [sample_device]
    client.get_device.return_value = sample_device
    client.get_device_status.return_value = sample_status
    with patch("get_status.SmartThingsClient", return_value=client):
        with patch("sys.argv", ["get_status.py", "--all"]):
            main()
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert isinstance(parsed, list)
    assert len(parsed) == 1


def test_main_all_includes_all_devices(capsys, sample_device, sample_status):
    device2 = {**sample_device, "deviceId": "device-xyz", "label": "Kitchen Light"}
    client = MagicMock()
    client.list_devices.return_value = [sample_device, device2]
    client.get_device.side_effect = [sample_device, device2]
    client.get_device_status.return_value = sample_status
    with patch("get_status.SmartThingsClient", return_value=client):
        with patch("sys.argv", ["get_status.py", "--all"]):
            main()
    out = capsys.readouterr().out
    assert len(json.loads(out)) == 2


def test_main_all_skips_not_found_device(capsys, sample_device, sample_status):
    device2 = {**sample_device, "deviceId": "device-gone", "label": "Ghost Device"}
    client = MagicMock()
    client.list_devices.return_value = [sample_device, device2]
    client.get_device.side_effect = [sample_device, NotFoundError("not found")]
    client.get_device_status.return_value = sample_status
    with patch("get_status.SmartThingsClient", return_value=client):
        with patch("sys.argv", ["get_status.py", "--all"]):
            main()
    out, err = capsys.readouterr()
    assert len(json.loads(out)) == 1
    assert "device-gone" in err


def test_main_all_not_found_warning_on_stderr(capsys, sample_device):
    client = MagicMock()
    client.list_devices.return_value = [sample_device]
    client.get_device.side_effect = NotFoundError("missing")
    with patch("get_status.SmartThingsClient", return_value=client):
        with patch("sys.argv", ["get_status.py", "--all"]):
            main()
    err = capsys.readouterr().err
    assert "Skipping" in err


# ── main() argparse ──────────────────────────────────────────────────────────

def test_main_no_args_exits(capsys):
    with patch("sys.argv", ["get_status.py"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0


def test_main_both_args_exits(capsys):
    with patch("sys.argv", ["get_status.py", "--device-id", "abc", "--all"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0


# ── main() error handling ────────────────────────────────────────────────────

def _client_raising(exc):
    client = MagicMock()
    client.list_devices.side_effect = exc
    client.get_device.side_effect = exc
    return client


def test_main_auth_error_exits_2():
    with patch("get_status.SmartThingsClient", return_value=_client_raising(AuthError("bad"))):
        with patch("sys.argv", ["get_status.py", "--all"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
    assert exc_info.value.code == 2


def test_main_rate_limit_exits_4():
    with patch("get_status.SmartThingsClient", return_value=_client_raising(RateLimitError("rate"))):
        with patch("sys.argv", ["get_status.py", "--all"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
    assert exc_info.value.code == 4


def test_main_server_error_exits_5():
    with patch("get_status.SmartThingsClient", return_value=_client_raising(ServerError("srv"))):
        with patch("sys.argv", ["get_status.py", "--all"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
    assert exc_info.value.code == 5


def test_main_generic_error_exits_1():
    with patch("get_status.SmartThingsClient", return_value=_client_raising(SmartThingsError("x"))):
        with patch("sys.argv", ["get_status.py", "--all"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
    assert exc_info.value.code == 1
