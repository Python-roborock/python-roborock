import re
from typing import Any

import aiohttp
import pytest
from aioresponses.compat import normalize_url

from roborock import HomeData, HomeDataScene, UserData
from roborock.exceptions import RoborockAccountDoesNotExist
from roborock.web_api import IotLoginInfo, RoborockApiClient
from tests.mock_data import HOME_DATA_RAW, USER_DATA

pytest_plugins = [
    "tests.fixtures.web_api_fixtures",
]


@pytest.fixture(autouse=True)
def auto_mock_rest_fixture(mock_rest: Any) -> None:
    """Auto use the mock rest fixture for all tests in this module."""
    pass


async def test_pass_login_flow() -> None:
    """Test that we can login with a password and we get back the correct userdata object."""
    my_session = aiohttp.ClientSession()
    api = RoborockApiClient(username="test_user@gmail.com", session=my_session)
    ud = await api.pass_login("password")
    assert ud == UserData.from_dict(USER_DATA)
    assert not my_session.closed


async def test_code_login_flow() -> None:
    """Test that we can login with a code and we get back the correct userdata object."""
    api = RoborockApiClient(username="test_user@gmail.com")
    await api.request_code()
    ud = await api.code_login(4123)
    assert ud == UserData.from_dict(USER_DATA)


async def test_get_home_data_v2():
    """Test a full standard flow where we get the home data to end it off.
    This matches what HA does"""
    api = RoborockApiClient(username="test_user@gmail.com")
    await api.request_code()
    ud = await api.code_login(4123)
    hd = await api.get_home_data_v2(ud)
    assert hd == HomeData.from_dict(HOME_DATA_RAW)


async def test_nc_prepare():
    """Test adding a device and that nothing breaks"""
    api = RoborockApiClient(username="test_user@gmail.com")
    await api.request_code()
    ud = await api.code_login(4123)
    prepare = await api.nc_prepare(ud, "America/New_York")
    new_device = await api.add_device(ud, prepare["s"], prepare["t"])
    assert new_device["duid"] == "rand_duid"


async def test_get_scenes():
    """Test that we can get scenes"""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = await api.pass_login("password")
    sc = await api.get_scenes(ud, "123456")
    assert sc == [
        HomeDataScene.from_dict(
            {
                "id": 1234567,
                "name": "My plan",
            }
        )
    ]


async def test_execute_scene(mock_rest):
    """Test that we can execute a scene"""
    api = RoborockApiClient(username="test_user@gmail.com")
    ud = await api.pass_login("password")
    await api.execute_scene(ud, 123456)
    mock_rest.assert_any_call("https://api-us.roborock.com/user/scene/123456/execute", "post")


async def test_code_login_v4_flow(mock_rest) -> None:
    """Test that we can login with a code and we get back the correct userdata object."""
    api = RoborockApiClient(username="test_user@gmail.com")
    await api.request_code_v4()
    ud = await api.code_login_v4(4123, "US", 1)
    assert ud == UserData.from_dict(USER_DATA)


async def test_code_login_v4_account_does_not_exist(mock_rest) -> None:
    """Test that response code 3039 raises RoborockAccountDoesNotExist."""
    mock_rest.clear()

    mock_rest.post(
        re.compile(r"https://.*iot\.roborock\.com/api/v1/getUrlByEmail.*"),
        status=200,
        payload={
            "code": 200,
            "data": {"country": "US", "countrycode": "1", "url": "https://usiot.roborock.com"},
            "msg": "success",
        },
    )
    mock_rest.post(
        re.compile(r"https://.*iot\.roborock\.com/api/v4/email/code/send.*"),
        status=200,
        payload={"code": 200, "data": None, "msg": "success"},
    )
    mock_rest.post(
        re.compile(r"https://.*iot\.roborock\.com/api/v3/key/sign.*"),
        status=200,
        payload={"code": 200, "data": {"k": "mock_k"}, "msg": "success"},
    )
    mock_rest.post(
        re.compile(r"https://.*iot\.roborock\.com/api/v4/auth/email/login/code.*"),
        status=200,
        payload={"code": 3039, "data": None, "msg": "account does not exist"},
    )

    api = RoborockApiClient(username="test_user@gmail.com")
    await api.request_code_v4()
    with pytest.raises(RoborockAccountDoesNotExist) as exc_info:
        await api.code_login_v4(4123, "US", 1)
    assert "This account does not exist" in str(exc_info.value)


async def test_url_cycling(mock_rest) -> None:
    """Test that we cycle through the URLs correctly."""
    # Clear mock rest so that we can override the patches.
    mock_rest.clear()

    # 1. Mock US URL to return valid status but None for countrycode
    mock_rest.post(
        re.compile("https://usiot.roborock.com/api/v1/getUrlByEmail.*"),
        status=200,
        payload={
            "code": 200,
            "data": {"url": "https://usiot.roborock.com", "country": None, "countrycode": None},
            "msg": "Success",
        },
    )

    # 2. Mock EU URL to return valid status but None for countrycode
    mock_rest.post(
        re.compile("https://euiot.roborock.com/api/v1/getUrlByEmail.*"),
        status=200,
        payload={
            "code": 200,
            "data": {"url": "https://euiot.roborock.com", "country": None, "countrycode": None},
            "msg": "Success",
        },
    )

    # 3. Mock CN URL to return the correct, valid data
    mock_rest.post(
        re.compile("https://cniot.roborock.com/api/v1/getUrlByEmail.*"),
        status=200,
        payload={
            "code": 200,
            "data": {"url": "https://cniot.roborock.com", "country": "CN", "countrycode": "86"},
            "msg": "Success",
        },
    )

    # The RU URL should not be called, but we can mock it just in case
    # to catch unexpected behavior.
    mock_rest.post(re.compile("https://ruiot.roborock.com/api/v1/getUrlByEmail.*"), status=500)

    client = RoborockApiClient("test@example.com")
    result = await client._get_iot_login_info()

    assert result is not None
    assert isinstance(result, IotLoginInfo)
    assert result.base_url == "https://cniot.roborock.com"
    assert result.country == "CN"
    assert result.country_code == "86"

    assert client._iot_login_info == result
    # Check that all three urls were called. We have to do this kind of weirdly as aioresponses seems to have a bug.
    assert (
        len(
            mock_rest.requests[
                (
                    "post",
                    normalize_url(
                        "https://usiot.roborock.com/api/v1/getUrlByEmail?email=test%2540example.com&needtwostepauth=false"
                    ),
                )
            ]
        )
        == 1
    )
    assert (
        len(
            mock_rest.requests[
                (
                    "post",
                    normalize_url(
                        "https://euiot.roborock.com/api/v1/getUrlByEmail?email=test%2540example.com&needtwostepauth=false"
                    ),
                )
            ]
        )
        == 1
    )
    assert (
        len(
            mock_rest.requests[
                (
                    "post",
                    normalize_url(
                        "https://cniot.roborock.com/api/v1/getUrlByEmail?email=test%2540example.com&needtwostepauth=false"
                    ),
                )
            ]
        )
        == 1
    )
    # Make sure we just have the three we tested for above.
    assert len(mock_rest.requests) == 3


async def test_thirty_thirty_cycling(mock_rest) -> None:
    """Test that we cycle through the URLs correctly when users have deleted accounts in higher prio regions."""
    # Clear mock rest so that we can override the patches.
    mock_rest.clear()

    mock_rest.post(
        re.compile("https://usiot.roborock.com/api/v1/getUrlByEmail.*"),
        status=200,
        payload={
            "code": 200,
            "data": {"url": "https://usiot.roborock.com", "country": "US", "countrycode": 1},
            "msg": "Account in deletion",
        },
    )

    mock_rest.post(
        re.compile("https://euiot.roborock.com/api/v1/getUrlByEmail.*"),
        status=200,
        payload={
            "code": 200,
            "data": {"url": "https://euiot.roborock.com", "country": "EU", "countrycode": 49},
            "msg": "Success",
        },
    )

    mock_rest.post(
        re.compile("https://usiot.roborock.com/api/v4/email/code/send.*"),
        status=200,
        payload={
            "code": 3030,
        },
    )
    mock_rest.post(
        re.compile("https://euiot.roborock.com/api/v4/email/code/send.*"),
        status=200,
        payload={
            "code": 200,
        },
    )

    mock_rest.post(re.compile("https://ruiot.roborock.com/api/v1/getUrlByEmail.*"), status=500)
    mock_rest.post(re.compile("https://cniot.roborock.com/api/v1/getUrlByEmail.*"), status=500)

    client = RoborockApiClient("test@example.com")
    await client.request_code_v4()

    assert (
        len(
            mock_rest.requests[
                (
                    "post",
                    normalize_url("https://euiot.roborock.com/api/v4/email/code/send"),
                )
            ]
        )
        == 1
    )
    assert (
        len(
            mock_rest.requests[
                (
                    "post",
                    normalize_url("https://usiot.roborock.com/api/v4/email/code/send"),
                )
            ]
        )
        == 1
    )
    # Assert that we didn't try on the Russian or Chinese regions
    assert "https://ruiot.roborock.com/api/v4/email/code/send" not in mock_rest.requests
    assert "https://cniot.roborock.com/api/v4/email/code/send" not in mock_rest.requests


async def test_missing_country_login(mock_rest) -> None:
    """Test that we cycle through the URLs correctly."""
    mock_rest.clear()
    # Make country None, but country code set.
    mock_rest.post(
        re.compile("https://usiot.roborock.com/api/v1/getUrlByEmail.*"),
        status=200,
        payload={
            "code": 200,
            "data": {"url": "https://usiot.roborock.com", "country": None, "countrycode": 1},
            "msg": "Success",
        },
    )
    # v4 is not mocked, so it would fail it were called.
    mock_rest.post(
        re.compile(r"https://.*iot\.roborock\.com/api/v1/loginWithCode.*"),
        status=200,
        payload={"code": 200, "data": USER_DATA, "msg": "success"},
    )
    mock_rest.post(
        re.compile(r"https://.*iot\.roborock\.com/api/v1/sendEmailCode.*"),
        status=200,
        payload={"code": 200, "data": None, "msg": "success"},
    )

    client = RoborockApiClient("test@example.com")
    await client.request_code_v4()
    ud = await client.code_login_v4(4123)
    assert ud is not None
    # Ensure we have no surprise REST calls.
    assert len(mock_rest.requests) == 3


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
