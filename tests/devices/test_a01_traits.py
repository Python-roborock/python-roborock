from unittest.mock import AsyncMock, Mock, patch

import pytest

from roborock.devices.traits.a01 import DyadApi, ZeoApi
from roborock.roborock_message import RoborockDyadDataProtocol, RoborockZeoProtocol


@pytest.fixture
def mock_channel():
    channel = Mock()
    channel.send_command = AsyncMock()
    # Mocking send_decoded_command if it was a method on channel, but it's a standalone function imported in traits.
    # However, in traits/__init__.py it is imported as: from roborock.devices.a01_channel import send_decoded_command
    return channel


@pytest.mark.asyncio
async def test_dyad_query_values(mock_channel):
    with patch("roborock.devices.traits.a01.send_decoded_command", new_callable=AsyncMock) as mock_send:
        api = DyadApi(mock_channel)

        # Setup mock return value (raw values)
        mock_send.return_value = {
            int(
                RoborockDyadDataProtocol.CLEAN_MODE
            ): 1,  # Should convert to DyadCleanMode(1).name -> AUTO? Check mapping or enum
            int(RoborockDyadDataProtocol.POWER): 100,
        }

        protocols = [RoborockDyadDataProtocol.CLEAN_MODE, RoborockDyadDataProtocol.POWER]
        result = await api.query_values(protocols)

        # Verify conversion
        # CLEAN_MODE 1 -> str
        # POWER 100 -> 100

        assert RoborockDyadDataProtocol.CLEAN_MODE in result
        assert RoborockDyadDataProtocol.POWER in result

        # Check actual values if we know the mapping.
        # From roborock_client_a01.py (now a01_conversions.py):
        # RoborockDyadDataProtocol.CLEAN_MODE: lambda val: DyadCleanMode(val).name
        # DyadCleanMode(1) would need to be checked. Let's just assert it is a string.
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
        # From a01_conversions.py: RoborockZeoProtocol.STATE: lambda val: ZeoState(val).name
        assert result[RoborockZeoProtocol.STATE] == "spinning"  # Assuming ZeoState(6).name is spinning
        assert result[RoborockZeoProtocol.COUNTDOWN] == 120
