"""Tests for login and verification-code flows."""

import re

import aiohttp
import pytest
from aioresponses.compat import normalize_url

from roborock import UserData
from roborock.exceptions import RoborockAccountDoesNotExist
from roborock.web_api import (
    DEFAULT_AGREEMENT_MAJOR_VERSION,
    DEFAULT_AGREEMENT_MINOR_VERSION,
    RoborockApiClient,
)
from tests.mock_data import USER_DATA


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


async def test_code_login_v4_flow(mock_rest) -> None:
    """Test that we can login with a code and we get back the correct userdata object."""
    api = RoborockApiClient(username="test_user@gmail.com")
    await api.request_code_v4()
    ud = await api.code_login_v4(4123, "US", 1)
    assert ud == UserData.from_dict(USER_DATA)


async def test_code_login_v4_uses_latest_agreement_version(mock_rest) -> None:
    """Test that the agreement version sent on login is fetched, not hardcoded.

    The login endpoint rejects a stale agreement version with code 3006, and the
    current version differs per server and country, so it cannot be hardcoded.
    """
    mock_rest.get(
        re.compile(r"https://.*iot\.roborock\.com/api/v3/app/agreement/latest.*"),
        status=200,
        payload={"code": 200, "data": {"majorVersion": 19, "minorVersion": 1}, "msg": "success"},
    )

    api = RoborockApiClient(username="test_user@gmail.com")
    await api.request_code_v4()
    await api.code_login_v4(4123, "US", 1)

    login_calls = [
        (key, call)
        for key, calls in mock_rest.requests.items()
        for call in calls
        if "api/v4/auth/email/login/code" in str(key[1])
    ]
    assert login_calls, "expected a v4 login request"
    data = login_calls[-1][1].kwargs["data"]
    assert data["majorVersion"] == 19
    assert data["minorVersion"] == 1


async def test_code_login_v4_agreement_version_fallback(mock_rest) -> None:
    """Test that login still proceeds when the agreement version lookup fails."""
    mock_rest.get(
        re.compile(r"https://.*iot\.roborock\.com/api/v3/app/agreement/latest.*"),
        exception=aiohttp.ClientError("boom"),
    )

    api = RoborockApiClient(username="test_user@gmail.com")
    await api.request_code_v4()
    ud = await api.code_login_v4(4123, "US", 1)
    assert ud == UserData.from_dict(USER_DATA)

    login_calls = [
        (key, call)
        for key, calls in mock_rest.requests.items()
        for call in calls
        if "api/v4/auth/email/login/code" in str(key[1])
    ]
    data = login_calls[-1][1].kwargs["data"]
    assert data["majorVersion"] == DEFAULT_AGREEMENT_MAJOR_VERSION
    assert data["minorVersion"] == DEFAULT_AGREEMENT_MINOR_VERSION


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
