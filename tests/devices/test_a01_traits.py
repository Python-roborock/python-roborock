from unittest.mock import AsyncMock, Mock, patch

import pytest

from roborock.devices.traits.a01 import DyadApi, ZeoApi
from roborock.roborock_message import RoborockDyadDataProtocol, RoborockZeoProtocol


@pytest.fixture
def mock_channel():
    channel = Mock()
    channel.send_command = AsyncMock()
    return channel


@pytest.mark.asyncio
async def test_dyad_query_values(mock_channel):
    with patch("roborock.devices.traits.a01.send_decoded_command", new_callable=AsyncMock) as mock_send:
        api = DyadApi(mock_channel)

        # Setup mock return value (raw values)
        mock_send.return_value = {
            int(RoborockDyadDataProtocol.CLEAN_MODE): 1,
            int(RoborockDyadDataProtocol.POWER): 100,
        }

        protocols = [RoborockDyadDataProtocol.CLEAN_MODE, RoborockDyadDataProtocol.POWER]
        result = await api.query_values(protocols)

        # Verify conversion
        assert RoborockDyadDataProtocol.CLEAN_MODE in result
        assert RoborockDyadDataProtocol.POWER in result

        assert isinstance(result[RoborockDyadDataProtocol.CLEAN_MODE], str)
        assert result[RoborockDyadDataProtocol.POWER] == 100


@pytest.mark.asyncio
async def test_zeo_query_values(mock_channel):
    with patch("roborock.devices.traits.a01.send_decoded_command", new_callable=AsyncMock) as mock_send:
        api = ZeoApi(mock_channel)

        mock_send.return_value = {
            int(RoborockZeoProtocol.STATE): 6,  # spinning
            int(RoborockZeoProtocol.COUNTDOWN): 120,
        }

        protocols = [RoborockZeoProtocol.STATE, RoborockZeoProtocol.COUNTDOWN]
        result = await api.query_values(protocols)

        assert RoborockZeoProtocol.STATE in result
        assert result[RoborockZeoProtocol.STATE] == "spinning"
        assert result[RoborockZeoProtocol.COUNTDOWN] == 120
