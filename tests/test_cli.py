"""Tests for the command line interface."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
import yaml
from click.testing import CliRunner

from roborock.cli import ConnectionCache, DeviceConnectionManager, RoborockContext, cli
from roborock.data import HomeDataProduct, HomeDataSchedule, RoborockCategory, UserData
from roborock.devices.device import RoborockDevice
from roborock.devices.device_manager import DeviceManager
from roborock.exceptions import RoborockException
from roborock.roborock_typing import RoborockCommand
from roborock.web_api import RoborockApiClient
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
