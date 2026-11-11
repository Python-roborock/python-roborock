"""Tests for the command line interface."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
import yaml
from click.testing import CliRunner

from roborock.cli import ConnectionCache, RoborockContext, cli
from roborock.data import HomeDataSchedule, UserData
from roborock.data.code_mappings import RoborockProductNickname
from roborock.device_features import DeviceFeatures
from roborock.exceptions import RoborockException
from roborock.web_api import RoborockApiClient
from tests.mock_data import USER_DATA, USER_EMAIL


@pytest.mark.parametrize(
    ("nickname_name", "nickname"),
    [
        ("PEARLPLUS", RoborockProductNickname.PEARLPLUS),
        ("TANOS", RoborockProductNickname.TANOS),
        ("ULTRONLITE", RoborockProductNickname.ULTRONLITE),
        ("Unknown", None),
        ("", None),
        (None, None),
    ],
)
def test_update_docs_nickname(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    nickname_name: str | None,
    nickname: RoborockProductNickname | None,
) -> None:
    """Generated capabilities agree with runtime decoding of the same family."""
    monkeypatch.chdir(tmp_path)
    data_file = tmp_path / "devices.yaml"
    output_file = tmp_path / "features.md"
    data_file.write_text(
        yaml.safe_dump(
            {
                "roborock.vacuum.test": {
                    "product_nickname": nickname_name,
                    "new_feature_info": 0,
                    "new_feature_info_str": "0",
                    "feature_info": [119],
                }
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["update-docs", "--data-file", str(data_file), "--output-file", str(output_file)])

    assert result.exit_code == 0, result.output
    rows = {
        cells[0].strip("`"): cells[1]
        for line in output_file.read_text(encoding="utf-8").splitlines()[2:]
        if (cells := [cell.strip() for cell in line.strip("|").split("|")])
    }
    expected = {
        name: value
        for name, value in asdict(DeviceFeatures.from_feature_flags(0, "0", [119], nickname)).items()
        if isinstance(value, bool)
    }
    assert {name: rows[name] == "X" for name in expected} == expected
    assert rows["119"] == "X"
    assert rows["new_feature_info"] == "0"
    assert rows["new_feature_info_str"] == "0"
    assert "feature_info" not in rows


def test_update_docs_invalid_nickname(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A misspelled family is reported rather than silently losing capabilities."""
    monkeypatch.chdir(tmp_path)
    data_file = tmp_path / "devices.yaml"
    output_file = tmp_path / "features.md"
    data_file.write_text(
        yaml.safe_dump({"roborock.vacuum.test": {"product_nickname": "PEARLPLUSS_TYPO"}}),
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["update-docs", "--data-file", str(data_file), "--output-file", str(output_file)])

    assert result.exit_code != 0
    assert "PEARLPLUSS_TYPO" in result.output
    assert "roborock.vacuum.test" in result.output
    assert not output_file.exists()


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
