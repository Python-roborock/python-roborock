"""Tests for the low-level PreparedRequest helper."""

import re
from typing import Any

import aiohttp
import pytest

from roborock.exceptions import RoborockException
from roborock.web_api import PreparedRequest


@pytest.mark.parametrize(
    "exception",
    [
        aiohttp.ClientError("connection failed"),
        TimeoutError("timed out"),
        OSError("dns failure"),
    ],
    ids=["client_error", "timeout", "os_error"],
)
async def test_prepared_request_wraps_network_errors(exception: Exception, mock_rest: Any) -> None:
    """Network errors from aiohttp must be wrapped as RoborockException so
    consumers can rely on the typed exception hierarchy."""
    url_pattern = re.compile(r"https://example\.com/api/test.*")
    mock_rest.post(url_pattern, exception=exception)

    req = PreparedRequest("https://example.com")
    with pytest.raises(RoborockException) as exc_info:
        await req.request("post", "/api/test")
    assert exc_info.value.__cause__ is exception
