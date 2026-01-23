import re
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from aioresponses import aioresponses

from tests.mock_data import HOME_DATA_RAW, HOME_DATA_SCENES_RAW, USER_DATA


@pytest.fixture
def skip_rate_limit() -> Generator[None, None, None]:
    """Don't rate limit tests as they aren't actually hitting the api."""
    with (
        patch("roborock.web_api.RoborockApiClient._login_limiter.try_acquire", return_value=True),
        patch("roborock.web_api.RoborockApiClient._login_limiter.try_acquire_async", return_value=True),
        patch("roborock.web_api.RoborockApiClient._home_data_limiter.try_acquire", return_value=True),
    ):
        yield


@pytest.fixture(name="home_data")
def home_data_fixture() -> dict[str, Any]:
    """Fixture to provide HomeData instance for tests."""
    return HOME_DATA_RAW


@pytest.fixture(name="mock_rest")
def mock_rest_fixture(skip_rate_limit: Any, home_data: dict[str, Any]) -> aioresponses:
    """Mock all rest endpoints so they won't hit real endpoints"""
    with aioresponses() as mocked:
        # Match the base URL and allow any query params
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/getUrlByEmail.*"),
            status=200,
            payload={
                "code": 200,
                "data": {"country": "US", "countrycode": "1", "url": "https://usiot.roborock.com"},
                "msg": "success",
            },
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/login.*"),
            status=200,
            payload={"code": 200, "data": USER_DATA, "msg": "success"},
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/loginWithCode.*"),
            status=200,
            payload={"code": 200, "data": USER_DATA, "msg": "success"},
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/sendEmailCode.*"),
            status=200,
            payload={"code": 200, "data": None, "msg": "success"},
        )
        mocked.get(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/getHomeDetail.*"),
            status=200,
            payload={
                "code": 200,
                "data": {"deviceListOrder": None, "id": 123456, "name": "My Home", "rrHomeId": 123456, "tuyaHomeId": 0},
                "msg": "success",
            },
        )
        mocked.get(
            re.compile(r"https://api-.*\.roborock\.com/v2/user/homes*"),
            status=200,
            payload={"api": None, "code": 200, "result": home_data, "status": "ok", "success": True},
        )
        mocked.get(
            re.compile(r"https://api-.*\.roborock\.com/v3/user/homes*"),
            status=200,
            payload={"api": None, "code": 200, "result": home_data, "status": "ok", "success": True},
        )
        mocked.post(
            re.compile(r"https://api-.*\.roborock\.com/nc/prepare"),
            status=200,
            payload={
                "api": None,
                "result": {"r": "US", "s": "ffffff", "t": "eOf6d2BBBB"},
                "status": "ok",
                "success": True,
            },
        )

        mocked.get(
            re.compile(r"https://api-.*\.roborock\.com/user/devices/newadd/*"),
            status=200,
            payload={
                "api": "获取新增设备信息",
                "result": {
                    "activeTime": 1737724598,
                    "attribute": None,
                    "cid": None,
                    "createTime": 0,
                    "deviceStatus": None,
                    "duid": "rand_duid",
                    "extra": "{}",
                    "f": False,
                    "featureSet": "0",
                    "fv": "02.16.12",
                    "iconUrl": "",
                    "lat": None,
                    "localKey": "random_lk",
                    "lon": None,
                    "name": "S7",
                    "newFeatureSet": "0000000000002000",
                    "online": True,
                    "productId": "rand_prod_id",
                    "pv": "1.0",
                    "roomId": None,
                    "runtimeEnv": None,
                    "setting": None,
                    "share": False,
                    "shareTime": None,
                    "silentOtaSwitch": False,
                    "sn": "Rand_sn",
                    "timeZoneId": "America/New_York",
                    "tuyaMigrated": False,
                    "tuyaUuid": None,
                },
                "status": "ok",
                "success": True,
            },
        )
        mocked.get(
            re.compile(r"https://api-.*\.roborock\.com/user/scene/device/.*"),
            status=200,
            payload={"api": None, "code": 200, "result": HOME_DATA_SCENES_RAW, "status": "ok", "success": True},
        )
        mocked.post(
            re.compile(r"https://api-.*\.roborock\.com/user/scene/.*/execute"),
            status=200,
            payload={"api": None, "code": 200, "result": None, "status": "ok", "success": True},
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v4/email/code/send.*"),
            status=200,
            payload={"code": 200, "data": None, "msg": "success"},
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v3/key/sign.*"),
            status=200,
            payload={"code": 200, "data": {"k": "mock_k"}, "msg": "success"},
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v4/auth/email/login/code.*"),
            status=200,
            payload={"code": 200, "data": USER_DATA, "msg": "success"},
        )
        yield mocked
