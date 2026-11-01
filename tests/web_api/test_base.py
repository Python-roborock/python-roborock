"""Tests for regional base URL discovery shared by every web API mixin."""

import re

from aioresponses.compat import normalize_url

from roborock.web_api import IotLoginInfo, RoborockApiClient


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
    for region in ("us", "eu", "cn"):
        key = (
            "post",
            normalize_url(
                f"https://{region}iot.roborock.com/api/v1/getUrlByEmail?email=test%2540example.com&needtwostepauth=false"
            ),
        )
        assert len(mock_rest.requests[key]) == 1
    # Make sure we just have the three we tested for above.
    assert len(mock_rest.requests) == 3
