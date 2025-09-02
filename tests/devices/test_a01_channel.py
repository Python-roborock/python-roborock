"""Tests for the a01_channel."""

from typing import Any

import pytest

from roborock.devices.a01_channel import send_decoded_command
from roborock.protocols.a01_protocol import encode_mqtt_payload
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
)

from ..conftest import FakeChannel


@pytest.fixture
def mock_mqtt_channel() -> FakeChannel:
    """Fixture for a fake MQTT channel."""
    return FakeChannel()


async def test_id_query(mock_mqtt_channel: FakeChannel):
    """Test successful command sending and response decoding."""
    # Command parameters to send
    params: dict[RoborockDyadDataProtocol, Any] = {
        RoborockDyadDataProtocol.ID_QUERY: [
            RoborockDyadDataProtocol.WARM_LEVEL,
            RoborockDyadDataProtocol.POWER,
        ]
    }
    encoded = encode_mqtt_payload(
        {
            RoborockDyadDataProtocol.WARM_LEVEL: 101,
            RoborockDyadDataProtocol.POWER: 75,
        }
    )
    response_message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=encoded.payload, version=encoded.version
    )
    mock_mqtt_channel.response_queue.append(response_message)

    # Call the function to be tested
    result = await send_decoded_command(mock_mqtt_channel, params)  # type: ignore[call-overload]

    # Assertions
    assert result == {RoborockDyadDataProtocol.WARM_LEVEL: 101, RoborockDyadDataProtocol.POWER: 75}
    mock_mqtt_channel.publish.assert_awaited_once()
    mock_mqtt_channel.subscribe.assert_awaited_once()
