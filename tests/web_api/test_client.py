"""Tests for the composed public clients and the backwards-compatible module surface."""

from unittest.mock import AsyncMock, Mock

import pytest

from roborock import UserData
from roborock.exceptions import RoborockInvalidCredentials
from roborock.web_api import RoborockApiClient, UserWebApiClient
from tests.mock_data import USER_DATA


def test_legacy_module_exports() -> None:
    """Names previously importable from the ``roborock.web_api`` module keep resolving."""
    from roborock import web_api

    for name in (
        "BASE_URLS",
        "DEFAULT_AGREEMENT_MAJOR_VERSION",
        "DEFAULT_AGREEMENT_MINOR_VERSION",
        "IotLoginInfo",
        "PreparedRequest",
        "RoborockApiClient",
        "UserWebApiClient",
        "_compact_json",
        "_get_hawk_authentication",
        "_LOGGER",
        "aiohttp",
        "secrets",
        "time",
    ):
        assert hasattr(web_api, name), name


async def test_user_web_api_client_unauthorized_hook() -> None:
    """Test that UserWebApiClient triggers unauthorized hook on RoborockInvalidCredentials."""
    mock_hook = Mock()
    mock_api = AsyncMock(spec=RoborockApiClient)

    # Setup mock to raise RoborockInvalidCredentials
    mock_api.get_home_data_v3.side_effect = RoborockInvalidCredentials("Unauthorized")

    client = UserWebApiClient(mock_api, UserData.from_dict(USER_DATA), unauthorized_hook=mock_hook)

    with pytest.raises(RoborockInvalidCredentials):
        await client.get_home_data()

    mock_hook.assert_called_once()

    # Test another method
    mock_hook.reset_mock()
    mock_api.get_rooms.side_effect = RoborockInvalidCredentials("Unauthorized")
    with pytest.raises(RoborockInvalidCredentials):
        await client.get_rooms()
    mock_hook.assert_called_once()
