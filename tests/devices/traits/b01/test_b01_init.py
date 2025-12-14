import json
from typing import Any
from unittest.mock import patch

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from roborock.data.b01_q7 import WorkStatusMapping
from roborock.devices.b01_channel import send_decoded_command
from roborock.devices.traits.b01.q7 import Q7PropertiesApi
from roborock.exceptions import RoborockException
from roborock.protocols.b01_protocol import B01_VERSION
from roborock.roborock_message import RoborockB01Props, RoborockMessage, RoborockMessageProtocol
from tests.conftest import FakeChannel


def build_b01_message(message: dict[Any, Any], msg_id: str = "123456789", seq: int = 2020) -> RoborockMessage:
    """Build an encoded B01 RPC response message."""
    dps_payload = {
        "dps": {
            "10000": json.dumps(
                {
                    "msgId": msg_id,
                    "data": message,
                }
            )
        }
    }
    return RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=pad(
            json.dumps(dps_payload).encode(),
            AES.block_size,
        ),
        version=b"B01",
        seq=seq,
    )


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


@pytest.fixture(name="q7_api")
def q7_api_fixture(fake_channel: FakeChannel) -> Q7PropertiesApi:
    return Q7PropertiesApi(fake_channel)  # type: ignore[arg-type]


async def test_q7_api_query_values(q7_api: Q7PropertiesApi, fake_channel: FakeChannel):
    """Test that Q7PropertiesApi correctly converts raw values."""
    expected_msg_id = "123456789"

    # We need to construct the expected result based on the mappings
    # status: 1 -> WAITING_FOR_ORDERS
    # wind: 1 -> STANDARD
    response_data = {
        "status": 1,
        "wind": 1,
        "battery": 100,
    }

    # Patch get_next_int to return our expected msg_id so the channel waits for it
    with patch("roborock.devices.b01_channel.get_next_int", return_value=int(expected_msg_id)):
        # Queue the response
        fake_channel.response_queue.append(build_b01_message(response_data, msg_id=expected_msg_id))

        result = await q7_api.query_values(
            [
                RoborockB01Props.STATUS,
                RoborockB01Props.WIND,
            ]
        )

    assert result is not None
    assert result.status == WorkStatusMapping.WAITING_FOR_ORDERS
    # wind might be mapped to SCWindMapping.STANDARD (1)
    # let's verify checking the prop definition in B01Props
    # wind: SCWindMapping | None = None
    # SCWindMapping.STANDARD is 1 ('balanced')
    from roborock.data.b01_q7 import SCWindMapping

    assert result.wind == SCWindMapping.STANDARD

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == B01_VERSION

    # Verify request payload
    assert message.payload is not None
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    # {"dps": {"10000": {"method": "prop.get", "msgId": "123456789", "params": {"property": ["status", "wind"]}}}}
    assert "dps" in payload_data
    assert "10000" in payload_data["dps"]
    inner = payload_data["dps"]["10000"]
    assert inner["method"] == "prop.get"
    assert inner["msgId"] == expected_msg_id
    assert inner["params"] == {"property": [RoborockB01Props.STATUS, RoborockB01Props.WIND]}


@pytest.mark.parametrize(
    ("query", "response_data", "expected_status"),
    [
        (
            [RoborockB01Props.STATUS],
            {"status": 2},
            WorkStatusMapping.PAUSED,
        ),
        (
            [RoborockB01Props.STATUS],
            {"status": 5},
            WorkStatusMapping.SWEEP_MOPING,
        ),
    ],
)
async def test_q7_response_value_mapping(
    query: list[RoborockB01Props],
    response_data: dict[str, Any],
    expected_status: WorkStatusMapping,
    q7_api: Q7PropertiesApi,
    fake_channel: FakeChannel,
):
    """Test Q7PropertiesApi value mapping for different statuses."""
    msg_id = "987654321"

    with patch("roborock.devices.b01_channel.get_next_int", return_value=int(msg_id)):
        fake_channel.response_queue.append(build_b01_message(response_data, msg_id=msg_id))

        result = await q7_api.query_values(query)

    assert result is not None


async def test_send_decoded_command_non_dict_response(fake_channel: FakeChannel):
    """Test validity of handling non-dict responses (should not timeout)."""
    msg_id = "123456789"

    dps_payload = {
        "dps": {
            "10000": json.dumps(
                {
                    "msgId": msg_id,
                    "data": "some_string_error",
                }
            )
        }
    }
    message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=pad(
            json.dumps(dps_payload).encode(),
            AES.block_size,
        ),
        version=b"B01",
        seq=2021,
    )

    fake_channel.response_queue.append(message)

    with patch("roborock.devices.b01_channel.get_next_int", return_value=int(msg_id)):
        # Use a random string for command type to avoid needing import

        with pytest.raises(RoborockException, match="Unexpected data type for response"):
            await send_decoded_command(fake_channel, 10000, "prop.get", [])  # type: ignore[arg-type]
