"""Tests for the command line interface."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import click
import pytest
import yaml
from click.testing import CliRunner

from roborock.cli import (
    ConnectionCache,
    DeviceConnectionManager,
    RoborockContext,
    cli,
    q7_clean_segments,
    q7_vacuum_dock,
    q7_vacuum_pause,
    q7_vacuum_start,
    q7_vacuum_stop,
    session,
    status,
)
from roborock.data import HomeDataDevice, HomeDataProduct, HomeDataSchedule, RoborockCategory, UserData
from roborock.data.b01_q7 import CleanTaskTypeMapping, SCDeviceCleanParam
from roborock.devices.device import RoborockDevice
from roborock.devices.device_manager import DeviceManager
from roborock.devices.traits.b01.q7 import Q7PropertiesApi
from roborock.devices.traits.b01.q7 import create as create_q7_api
from roborock.exceptions import RoborockException
from roborock.roborock_message import RoborockB01Props
from roborock.roborock_typing import RoborockB01Q7Methods, RoborockCommand
from roborock.web_api import RoborockApiClient
from tests.devices.traits.b01.q7.conftest import FakeQ7Channel
from tests.mock_data import USER_DATA, USER_EMAIL


@pytest.fixture(autouse=True)
def isolated_login(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Use temporary cached credentials so commands never load the user's login."""
    login_file = tmp_path / ".roborock"
    monkeypatch.setattr(RoborockContext, "roborock_file", login_file)
    monkeypatch.setattr(RoborockContext, "roborock_cache_file", tmp_path / ".roborock.cache")
    login_file.write_text(
        json.dumps(ConnectionCache(user_data=UserData.from_dict(USER_DATA), email=USER_EMAIL).as_dict()),
        encoding="utf-8",
    )


@pytest.fixture
def mock_api(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Replace the cloud client, including all asynchronous network operations."""
    factory = Mock(return_value=Mock(spec=RoborockApiClient))
    monkeypatch.setattr("roborock.cli.RoborockApiClient", factory)
    return factory


@pytest.fixture
def job_data() -> dict[str, Any]:
    """A schedule including model-specific cleaning settings."""
    return {
        "id": 3878757,
        "cron": "05 10 * * ?",
        "repeated": True,
        "enabled": False,
        "param": {"mapId": 0, "rooms": [1, 2], "custom_key": {"id": 7, "value": None}},
    }


def test_update_job(mock_api: Mock, tmp_path: Path, job_data: dict[str, Any]) -> None:
    """The CLI parses JSON into a schedule and calls the API using cached credentials."""
    job_file = tmp_path / "job.json"
    job_file.write_text(json.dumps(job_data), encoding="utf-8")

    result = CliRunner().invoke(cli, ["update-job", "--device_id", "123456", "--job-file", str(job_file)])

    assert result.exit_code == 0, result.output
    assert result.output == "Updated job 3878757 for device 123456\n"
    mock_api.assert_called_once_with(USER_EMAIL)
    mock_api.return_value.update_job.assert_awaited_once_with(
        UserData.from_dict(USER_DATA), "123456", HomeDataSchedule(**job_data)
    )


def test_update_job_invalid_json(mock_api: Mock, tmp_path: Path) -> None:
    """A JSON parsing failure is reported without calling the cloud API."""
    job_file = tmp_path / "job.json"
    job_file.write_text("[", encoding="utf-8")

    result = CliRunner().invoke(cli, ["update-job", "--device_id", "123456", "--job-file", str(job_file)])

    assert result.exit_code == 1
    assert "Error: Expecting value" in result.output
    mock_api.assert_not_called()


def test_update_job_api_error(mock_api: Mock, tmp_path: Path, job_data: dict[str, Any]) -> None:
    """A cloud rejection is reported with an unsuccessful command exit."""
    mock_api.return_value.update_job.side_effect = RoborockException("Job not found")
    job_file = tmp_path / "job.json"
    job_file.write_text(json.dumps(job_data), encoding="utf-8")

    result = CliRunner().invoke(cli, ["update-job", "--device_id", "123456", "--job-file", str(job_file)])

    assert result.exit_code == 1
    assert result.output == "Error: Job not found\n"
    mock_api.return_value.update_job.assert_awaited_once()


@pytest.mark.parametrize(
    ("model", "expected_nickname"),
    [
        ("roborock.vacuum.a294", "Unknown"),
        ("roborock.vacuum.unrecognized", "Unknown"),
        ("roborock.vacuum.a87", "PEARLPLUS"),
        ("roborock.vacuum.a101", "PEARLS"),
    ],
)
def test_get_device_info_product_nickname(monkeypatch: pytest.MonkeyPatch, model: str, expected_nickname: str) -> None:
    """Device info exports unknown families and retains mapped family names."""
    product = HomeDataProduct(id="test-product", name="Test vacuum", model=model, category=RoborockCategory.VACUUM)
    init_status = {
        "new_feature_info": 2247397454282751,
        "new_feature_info_str": "0000009021D0B410C0C47EFDA82934C952BA8F507EDEFFFE",
        "feature_info": list(range(111, 126)),
    }
    device = Mock(spec=RoborockDevice)
    device.name = "Test vacuum"
    device.duid = "test-device"
    device.product = product
    device.device_info = Mock(pv="1.0")
    device.v1_properties = Mock()
    send_command = AsyncMock(return_value=[init_status])
    device.v1_properties.command.send = send_command
    device_manager = AsyncMock(spec=DeviceManager)
    device_manager.get_devices.return_value = [device]
    connection_manager = AsyncMock(spec=DeviceConnectionManager)
    connection_manager.ensure_device_manager.return_value = device_manager
    monkeypatch.setattr(RoborockContext, "get_device_manager", AsyncMock(return_value=connection_manager))

    result = CliRunner().invoke(cli, ["get-device-info"])

    assert result.exit_code == 0, result.output
    device_info = yaml.safe_load(result.output.split("--- Device Information (copy to your YAML file) ---\n\n")[1])
    assert device_info == {
        model: {
            "protocol_version": "1.0",
            "product_nickname": expected_nickname,
            **init_status,
            "product": product.as_dict(),
        }
    }
    send_command.assert_awaited_once_with(RoborockCommand.APP_GET_INIT_STATUS)


@pytest.fixture
def q7_fake_channel() -> FakeQ7Channel:
    """A plaintext mock for the Q7 RPC and map channels."""
    return FakeQ7Channel()


@pytest.fixture
def q7_api(q7_fake_channel: FakeQ7Channel) -> Q7PropertiesApi:
    """A Q7 API for the Q7 TF+ (roborock.vacuum.sc05) from the issue report."""
    product = HomeDataProduct(
        id="product-id-q7",
        name="Roborock Q7",
        model="roborock.vacuum.sc05",
        category=RoborockCategory.VACUUM,
    )
    device = HomeDataDevice(
        duid="abc123",
        name="Q7",
        local_key="key123key123key1",
        product_id="product-id-q7",
        sn="testsn012345",
    )
    return create_q7_api(product, device, q7_fake_channel, q7_fake_channel)


def _mock_device(monkeypatch: pytest.MonkeyPatch, q7_api: Q7PropertiesApi | None) -> SimpleNamespace:
    """Route RoborockContext.get_device_manager to a device with the given Q7 API."""
    device = SimpleNamespace(v1_properties=None, b01_q10_properties=None, b01_q7_properties=q7_api)
    connection_manager = AsyncMock()
    connection_manager.get_device.return_value = device
    monkeypatch.setattr(RoborockContext, "get_device_manager", AsyncMock(return_value=connection_manager))
    return device


def _invoke_session_command(command: click.Command, device_id: str = "abc123", **kwargs: Any) -> None:
    """Invoke a session command callback directly with a fresh context.

    The command is wrapped by ``click.pass_context``, so the context must be
    pushed onto the click stack and the device id passed as a keyword: the
    decorator injects the active context as the first argument itself.
    """
    ctx = click.Context(command, obj=RoborockContext())
    with ctx:
        assert command.callback is not None
        command.callback(device_id=device_id, **kwargs)


def test_q7_session_commands_registered() -> None:
    """The Q7 vacuum commands are available in the session shell."""
    assert {
        "q7-vacuum-start",
        "q7-vacuum-pause",
        "q7-vacuum-stop",
        "q7-vacuum-dock",
        "q7-clean-segments",
    } <= set(session.commands)


@pytest.mark.parametrize(
    ("command", "method", "params", "message"),
    [
        (
            q7_vacuum_start,
            RoborockB01Q7Methods.SET_ROOM_CLEAN,
            {"clean_type": CleanTaskTypeMapping.ALL.code, "ctrl_value": SCDeviceCleanParam.START.code, "room_ids": []},
            "Starting vacuum cleaning...",
        ),
        (
            q7_vacuum_pause,
            RoborockB01Q7Methods.SET_ROOM_CLEAN,
            {"clean_type": CleanTaskTypeMapping.ALL.code, "ctrl_value": SCDeviceCleanParam.PAUSE.code, "room_ids": []},
            "Pausing vacuum cleaning...",
        ),
        (
            q7_vacuum_stop,
            RoborockB01Q7Methods.SET_ROOM_CLEAN,
            {"clean_type": CleanTaskTypeMapping.ALL.code, "ctrl_value": SCDeviceCleanParam.STOP.code, "room_ids": []},
            "Stopping vacuum cleaning...",
        ),
        (
            q7_vacuum_dock,
            RoborockB01Q7Methods.START_RECHARGE,
            {},
            "Returning vacuum to dock...",
        ),
    ],
)
def test_q7_vacuum_commands(
    monkeypatch: pytest.MonkeyPatch,
    q7_api: Q7PropertiesApi,
    q7_fake_channel: FakeQ7Channel,
    capsys: pytest.CaptureFixture[str],
    command: click.Command,
    method: RoborockB01Q7Methods,
    params: dict[str, Any],
    message: str,
) -> None:
    """Each Q7 vacuum command sends the matching B01 Q7 command to the device."""
    _mock_device(monkeypatch, q7_api)

    _invoke_session_command(command)

    assert q7_fake_channel.published_commands == [(method, params)]
    assert message in capsys.readouterr().out


def test_q7_vacuum_command_without_q7_support(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A device without a Q7 API reports the Q7 protocol as unsupported and sends nothing."""
    _mock_device(monkeypatch, None)

    _invoke_session_command(q7_vacuum_start)

    assert "Device does not support B01 Q7 protocol. Is it a Q7?" in capsys.readouterr().out


def test_q7_clean_segments(
    monkeypatch: pytest.MonkeyPatch,
    q7_api: Q7PropertiesApi,
    q7_fake_channel: FakeQ7Channel,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Segment cleaning on a Q7 sends a room clean for the given room ids."""
    _mock_device(monkeypatch, q7_api)

    _invoke_session_command(q7_clean_segments, segments="10,11")

    assert q7_fake_channel.published_commands == [
        (
            RoborockB01Q7Methods.SET_ROOM_CLEAN,
            {
                "clean_type": CleanTaskTypeMapping.ROOM.code,
                "ctrl_value": SCDeviceCleanParam.START.code,
                "room_ids": [10, 11],
            },
        )
    ]
    assert "Starting room clean of segments [10, 11]..." in capsys.readouterr().out


@pytest.mark.parametrize(
    ("segments", "message"),
    [
        ("9,x", "--segments must be comma-separated integers, e.g. 9,2"),
        ("", "No segment ids provided"),
    ],
)
def test_q7_clean_segments_invalid_input(
    monkeypatch: pytest.MonkeyPatch,
    q7_api: Q7PropertiesApi,
    q7_fake_channel: FakeQ7Channel,
    capsys: pytest.CaptureFixture[str],
    segments: str,
    message: str,
) -> None:
    """Bad segment input is rejected before anything is sent to the device."""
    _mock_device(monkeypatch, q7_api)

    _invoke_session_command(q7_clean_segments, segments=segments)

    assert q7_fake_channel.published_commands == []
    assert message in capsys.readouterr().out


def test_q7_status(
    monkeypatch: pytest.MonkeyPatch,
    q7_api: Q7PropertiesApi,
    q7_fake_channel: FakeQ7Channel,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Status on a Q7 queries the device properties and prints them as JSON."""
    q7_fake_channel.response_queue.append({"status": 1, "quantity": 87})
    _mock_device(monkeypatch, q7_api)

    _invoke_session_command(status)

    command, params = q7_fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.GET_PROP
    assert RoborockB01Props.STATUS in params["property"]
    assert RoborockB01Props.QUANTITY in params["property"]
    data = json.loads(capsys.readouterr().out)
    assert data["quantity"] == 87


def test_status_without_supported_device(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Status on a device with no supported protocol reports the feature as unsupported."""
    _mock_device(monkeypatch, None)

    _invoke_session_command(status)

    assert "Feature not supported by device" in capsys.readouterr().out


def test_q7_raw_command(
    monkeypatch: pytest.MonkeyPatch,
    q7_api: Q7PropertiesApi,
    q7_fake_channel: FakeQ7Channel,
) -> None:
    """The raw command sends a named B01 Q7 method and prints the device reply."""
    q7_fake_channel.response_queue.append({"result": "ok"})
    _mock_device(monkeypatch, q7_api)

    result = CliRunner().invoke(cli, ["command", "--device_id", "abc123", "--cmd", "service.find_device"])

    assert result.exit_code == 0, result.output
    assert q7_fake_channel.published_commands == [(RoborockB01Q7Methods.FIND_DEVICE, {})]
    assert '"result": "ok"' in result.output


def test_q7_raw_command_explicit_empty_list_params(
    monkeypatch: pytest.MonkeyPatch,
    q7_api: Q7PropertiesApi,
    q7_fake_channel: FakeQ7Channel,
) -> None:
    """An explicit --params '[]' still sends an empty list, not the {} default."""
    q7_fake_channel.response_queue.append({"result": "ok"})
    _mock_device(monkeypatch, q7_api)

    result = CliRunner().invoke(
        cli, ["command", "--device_id", "abc123", "--cmd", "service.find_device", "--params", "[]"]
    )

    assert result.exit_code == 0, result.output
    assert q7_fake_channel.published_commands == [(RoborockB01Q7Methods.FIND_DEVICE, [])]


def test_q7_raw_command_explicit_params(
    monkeypatch: pytest.MonkeyPatch,
    q7_api: Q7PropertiesApi,
    q7_fake_channel: FakeQ7Channel,
) -> None:
    """An explicit --params value is parsed as JSON and sent as-is."""
    q7_fake_channel.response_queue.append({"result": "ok"})
    _mock_device(monkeypatch, q7_api)

    result = CliRunner().invoke(
        cli, ["command", "--device_id", "abc123", "--cmd", "service.find_device", "--params", '{"mode": 1}']
    )

    assert result.exit_code == 0, result.output
    assert q7_fake_channel.published_commands == [(RoborockB01Q7Methods.FIND_DEVICE, {"mode": 1})]


def test_q7_clean_segments_help_does_not_reference_rooms() -> None:
    """The Q7 segment help does not point at the rooms command, which has no Q7 branch."""
    segments_option = next(p for p in q7_clean_segments.params if p.name == "segments")
    assert "`rooms`" not in (segments_option.help or "")
    assert "`rooms`" not in (q7_clean_segments.callback.__doc__ or "")


def test_q7_raw_command_invalid(
    monkeypatch: pytest.MonkeyPatch,
    q7_api: Q7PropertiesApi,
    q7_fake_channel: FakeQ7Channel,
) -> None:
    """An unknown method name is rejected before anything is sent to the device."""
    _mock_device(monkeypatch, q7_api)

    result = CliRunner().invoke(cli, ["command", "--device_id", "abc123", "--cmd", "service.nope"])

    assert result.exit_code == 0, result.output
    assert "Invalid command service.nope for B01_Q7 device" in result.output
    assert q7_fake_channel.published_commands == []
