"""Tests for home data and room endpoints."""

import pytest
from aioresponses.compat import normalize_url

from roborock import HomeData, HomeDataRoom, UserData
from roborock.exceptions import RoborockException
from roborock.web_api import RoborockApiClient
from tests.mock_data import HOME_DATA_RAW, USER_DATA


async def test_get_home_data_v2():
    """Test a full standard flow where we get the home data to end it off.
    This matches what HA does"""
    api = RoborockApiClient(username="test_user@gmail.com")
    await api.request_code()
    ud = await api.code_login(4123)
    hd = await api.get_home_data_v2(ud)
    assert hd == HomeData.from_dict(HOME_DATA_RAW)


async def test_get_home_data_v3(mock_rest):
    """Test that the v3 home data endpoint is requested and parsed."""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = await api.pass_login("password")
    hd = await api.get_home_data_v3(ud)
    assert hd == HomeData.from_dict(HOME_DATA_RAW)
    assert ("get", normalize_url("https://api-us.roborock.com/v3/user/homes/123456")) in mock_rest.requests


@pytest.mark.parametrize(
    "result_payload",
    [
        # roomId field (deviceshare endpoint convention)
        [
            {"roomId": "2362048", "name": "Living Room"},
            {"roomId": 2362044, "name": "Kitchen"},
        ],
        # id field (matches /user/homes/{id}/rooms — defensive in case the API normalizes)
        [
            {"id": 2362048, "name": "Living Room"},
            {"id": 2362044, "name": "Kitchen"},
        ],
    ],
)
async def test_get_shared_device_rooms(mock_rest, result_payload) -> None:
    """Test that shared-device rooms are fetched from the deviceshare query path."""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = await api.pass_login("password")

    mock_rest.get(
        "https://api-us.roborock.com/user/deviceshare/query/device-id-q7/rooms",
        status=200,
        payload={
            "api": None,
            "code": 200,
            "result": result_payload,
            "status": "ok",
            "success": True,
        },
    )

    rooms = await api.get_shared_device_rooms(ud, "device-id-q7")

    assert rooms == [
        HomeDataRoom(id=2362048, name="Living Room"),
        HomeDataRoom(id=2362044, name="Kitchen"),
    ]


@pytest.mark.parametrize("method", ["get_home_data", "get_home_data_v2", "get_home_data_v3", "get_rooms"])
async def test_missing_rriot_fails_before_network(mock_rest, method: str) -> None:
    """Missing rriot credentials are rejected before the home-detail lookup is made."""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = UserData.from_dict(USER_DATA)
    ud.rriot = None

    with pytest.raises(RoborockException, match="rriot is none"):
        await getattr(api, method)(ud)

    assert not mock_rest.requests
