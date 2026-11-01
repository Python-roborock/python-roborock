"""Tests for scheduled job endpoints."""

import json

import aiohttp
import pytest
from aioresponses.compat import normalize_url

from roborock import HomeDataSchedule, UserData
from roborock.exceptions import RoborockException
from roborock.web_api import RoborockApiClient
from tests.mock_data import USER_DATA


async def test_get_schedules(mock_rest) -> None:
    """Test that we can get schedules."""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = await api.pass_login("password")

    # Mock the response
    mock_rest.get(
        "https://api-us.roborock.com/user/devices/123456/jobs",
        status=200,
        payload={
            "api": None,
            "result": [
                {
                    "id": 3878757,
                    "cron": "03 13 15 12 ?",
                    "repeated": False,
                    "enabled": True,
                    "param": {
                        "id": 1,
                        "method": "server_scheduled_start",
                        "params": [
                            {
                                "repeat": 1,
                                "water_box_mode": 202,
                                "segments": "0",
                                "fan_power": 102,
                                "mop_mode": 300,
                                "clean_mop": 1,
                                "map_index": -1,
                                "name": "1765735413736",
                            }
                        ],
                    },
                }
            ],
            "status": "ok",
            "success": True,
        },
    )

    schedules = await api.get_schedules(ud, "123456")
    assert len(schedules) == 1
    schedule = schedules[0]
    assert schedule.id == 3878757
    assert schedule.cron == "03 13 15 12 ?"
    assert schedule.repeated is False
    assert schedule.enabled is True


async def test_create_job(mock_rest) -> None:
    """A /jobs write (schedule or one-time clean) POSTs the body and returns the parsed result."""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = await api.pass_login("password")

    mock_rest.post(
        "https://api-us.roborock.com/user/devices/123456/jobs",
        status=200,
        payload={"api": None, "result": "done", "status": "ok", "success": True},
    )

    job = {"cron": "05 10 * * ?", "repeated": True, "enabled": True, "param": {"rooms": [1, 2], "roomCount": 2}}
    response = await api.create_job(ud, "123456", job)
    assert response["success"] is True
    assert response["result"] == "done"


@pytest.mark.parametrize(
    ("enabled", "mac"),
    [
        (True, "fCO2ogG/WjxJjWEZw6l3ncC7cFChl/95jjjzu/YNRV0="),
        (False, "GsGuHY1XF375VJRdhMmoIYI/AacILSNCFBU1+3G/O0Y="),
    ],
)
async def test_update_job(mock_rest, monkeypatch, enabled: bool, mac: str) -> None:
    """Updates send the full schedule as compact JSON with a matching body-aware Hawk MAC."""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = UserData.from_dict(USER_DATA)
    monkeypatch.setattr("roborock.web_api._hawk.time.time", lambda: 1_700_000_000)
    monkeypatch.setattr("roborock.web_api._hawk.secrets.token_urlsafe", lambda n: "fixednonce")
    url = "https://api-us.roborock.com/user/devices/123456/jobs/3878757"
    mock_rest.put(url, payload={"result": "done", "status": "ok", "success": True})
    job = HomeDataSchedule(
        id=3878757,
        cron="05 10 * * ?",
        repeated=True,
        enabled=enabled,
        param={"mapId": 0, "rooms": [1, 2], "roomCount": 2, "custom_key": {"id": 7, "value": None}},
    )
    original_job = job.as_dict()

    await api.update_job(ud, "123456", job)

    enabled_json = b"true" if enabled else b"false"
    expected_body = (
        b'{"cron":"05 10 * * ?","repeated":true,"enabled":'
        + enabled_json
        + b',"param":{"mapId":0,"rooms":[1,2],"roomCount":2,"custom_key":{"id":7,"value":null}}}'
    )
    mock_rest.assert_called_once()
    request = mock_rest.requests[("put", normalize_url(url))][0]
    assert request.kwargs["data"] == expected_body
    assert request.kwargs["headers"] == {
        "Authorization": f'Hawk id="user123",s="pass123",ts="1700000000",nonce="fixednonce",mac="{mac}"',
        "Content-Type": "application/json",
    }
    assert request.kwargs["params"] is None
    assert request.kwargs["json"] is None
    assert job.as_dict() == original_job


@pytest.mark.parametrize("response", [{"success": False, "error": "Job not found"}, {}, None])
async def test_update_job_failed_response(mock_rest, response: dict | None) -> None:
    """Rejected and missing success responses raise the library's exception."""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = UserData.from_dict(USER_DATA)
    mock_rest.put(
        "https://api-us.roborock.com/user/devices/123456/jobs/3878757",
        body=json.dumps(response),
        content_type="application/json",
    )
    job = HomeDataSchedule(id=3878757, cron="05 10 * * ?", repeated=True, enabled=False)

    with pytest.raises(RoborockException) as exc_info:
        await api.update_job(ud, "123456", job)

    assert exc_info.value.args == (response,)


@pytest.mark.parametrize("missing_field", ["rriot", "a"])
async def test_update_job_missing_credentials(mock_rest, missing_field: str) -> None:
    """Missing cloud credentials are rejected before making a request."""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = UserData.from_dict(USER_DATA)
    if missing_field == "rriot":
        ud.rriot = None
        message = "rriot is none"
    else:
        assert ud.rriot is not None
        ud.rriot.r.a = None
        message = "Missing field 'a' in rriot reference"
    job = HomeDataSchedule(id=3878757, cron="05 10 * * ?", repeated=True, enabled=False)

    with pytest.raises(RoborockException, match=message):
        await api.update_job(ud, "123456", job)

    assert not mock_rest.requests


async def test_update_job_network_error(mock_rest) -> None:
    """Network failures surface as RoborockException through the shared request layer."""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = UserData.from_dict(USER_DATA)
    mock_rest.put(
        "https://api-us.roborock.com/user/devices/123456/jobs/3878757",
        exception=aiohttp.ClientConnectionError("connection lost"),
    )
    job = HomeDataSchedule(id=3878757, cron="05 10 * * ?", repeated=True, enabled=False)

    with pytest.raises(RoborockException, match="Network error contacting .*: connection lost"):
        await api.update_job(ud, "123456", job)
