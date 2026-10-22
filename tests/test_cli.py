"""Tests for the command line interface."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from roborock.cli import ConnectionCache, RoborockContext, cli
from roborock.data import HomeDataSchedule, UserData
from roborock.exceptions import RoborockException
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
    """A full schedule including model-specific cleaning settings."""
    return {
        "id": 3878757,
        "cron": "05 10 * * ?",
        "repeated": True,
        "enabled": False,
        "param": {"mapId": 0, "rooms": [1, 2], "custom_key": {"id": 7, "value": None}},
    }


@pytest.mark.parametrize("enabled", [False, True])
def test_update_job(mock_api: Mock, tmp_path: Path, job_data: dict[str, Any], enabled: bool) -> None:
    """The CLI passes a complete typed schedule using only the cached account."""
    job_data["enabled"] = enabled
    job_file = tmp_path / "job.json"
    job_file.write_text(json.dumps(job_data), encoding="utf-8")

    result = CliRunner().invoke(cli, ["update-job", "--device_id", "123456", "--job-file", str(job_file)])

    assert result.exit_code == 0, result.output
    assert result.output == "Updated job 3878757 for device 123456\n"
    mock_api.assert_called_once_with(USER_EMAIL)
    client = mock_api.return_value
    client.update_job.assert_awaited_once_with(UserData.from_dict(USER_DATA), "123456", HomeDataSchedule(**job_data))
    client.get_home_data_v3.assert_not_called()


def test_update_job_api_error(mock_api: Mock, tmp_path: Path, job_data: dict[str, Any]) -> None:
    """A cloud rejection produces an unsuccessful command exit."""
    mock_api.return_value.update_job.side_effect = RoborockException("Job not found")
    job_file = tmp_path / "job.json"
    job_file.write_text(json.dumps(job_data), encoding="utf-8")

    result = CliRunner().invoke(cli, ["update-job", "--device_id", "123456", "--job-file", str(job_file)])

    assert result.exit_code == 1
    assert result.output == "Error: Job not found\n"
    mock_api.return_value.update_job.assert_awaited_once()


def test_update_job_requires_login(mock_api: Mock, tmp_path: Path, job_data: dict[str, Any]) -> None:
    """Missing cached credentials fail without creating a cloud client."""
    (tmp_path / ".roborock").unlink()
    job_file = tmp_path / "job.json"
    job_file.write_text(json.dumps(job_data), encoding="utf-8")

    result = CliRunner().invoke(cli, ["update-job", "--device_id", "123456", "--job-file", str(job_file)])

    assert result.exit_code == 1
    assert result.output == "Error: You must login first\n"
    mock_api.assert_not_called()


@pytest.mark.parametrize("field", ["id", "cron", "repeated", "enabled", "param"])
def test_update_job_missing_fields(mock_api: Mock, tmp_path: Path, job_data: dict[str, Any], field: str) -> None:
    """Partial schedule files cannot reach the update endpoint."""
    del job_data[field]
    job_file = tmp_path / "job.json"
    job_file.write_text(json.dumps(job_data), encoding="utf-8")

    result = CliRunner().invoke(cli, ["update-job", "--device_id", "123456", "--job-file", str(job_file)])

    assert result.exit_code == 2
    assert f"Complete job required; missing fields: {field}" in result.output
    mock_api.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", True),
        ("id", "3878757"),
        ("id", 1.5),
        ("cron", None),
        ("cron", " "),
        ("repeated", 1),
        ("enabled", "false"),
        ("param", None),
        ("param", []),
        ("param", "{}"),
    ],
)
def test_update_job_invalid_fields(
    mock_api: Mock, tmp_path: Path, job_data: dict[str, Any], field: str, value: Any
) -> None:
    """Malformed scalar types are rejected instead of silently coerced."""
    job_data[field] = value
    job_file = tmp_path / "job.json"
    job_file.write_text(json.dumps(job_data), encoding="utf-8")

    result = CliRunner().invoke(cli, ["update-job", "--device_id", "123456", "--job-file", str(job_file)])

    assert result.exit_code == 2
    assert f"'{field}' must be" in result.output
    mock_api.assert_not_called()


def test_update_job_unknown_fields(mock_api: Mock, tmp_path: Path, job_data: dict[str, Any]) -> None:
    """Unknown top-level settings cannot be silently discarded during replacement."""
    job_data["additionalSetting"] = {"value": 1}
    job_file = tmp_path / "job.json"
    job_file.write_text(json.dumps(job_data), encoding="utf-8")

    result = CliRunner().invoke(cli, ["update-job", "--device_id", "123456", "--job-file", str(job_file)])

    assert result.exit_code == 2
    assert "Unknown job fields: additionalSetting" in result.output
    mock_api.assert_not_called()


@pytest.mark.parametrize("contents", ["[", "[]", "null", '"schedule"'])
def test_update_job_invalid_json(mock_api: Mock, tmp_path: Path, contents: str) -> None:
    """Invalid JSON and non-object roots fail before creating a cloud client."""
    job_file = tmp_path / "job.json"
    job_file.write_text(contents, encoding="utf-8")

    result = CliRunner().invoke(cli, ["update-job", "--device_id", "123456", "--job-file", str(job_file)])

    assert result.exit_code == 2
    assert "Invalid value for '--job-file'" in result.output
    mock_api.assert_not_called()


def test_update_job_missing_file(mock_api: Mock, tmp_path: Path) -> None:
    """A nonexistent input file fails without cloud access."""
    result = CliRunner().invoke(
        cli, ["update-job", "--device_id", "123456", "--job-file", str(tmp_path / "missing.json")]
    )

    assert result.exit_code == 2
    assert "does not exist" in result.output
    mock_api.assert_not_called()


def test_update_job_help(mock_api: Mock) -> None:
    """Help explains that this operation replaces all schedule settings."""
    result = CliRunner().invoke(cli, ["update-job", "--help"])

    assert result.exit_code == 0
    assert "Include all existing settings" in result.output
    assert "id, cron, repeated, enabled, and param" in result.output
    mock_api.assert_not_called()
