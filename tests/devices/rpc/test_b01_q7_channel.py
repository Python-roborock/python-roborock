import asyncio
import json
import math
import time
from collections.abc import Generator
from typing import Any, cast
from unittest.mock import patch

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from roborock.data import HomeDataDevice, HomeDataProduct, RoborockCategory
from roborock.devices.rpc.b01_q7_channel import (
    create_b01_q7_channel,
    send_decoded_command,
)
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q7_protocol import B01_VERSION, Q7RequestMessage
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.fixtures.channel_fixtures import FakeChannel


class B01MessageBuilder:
    """Helper class to build B01 RPC response messages for tests."""

    def __init__(self) -> None:
        self.msg_id = 123456789
        self.seq = 2020

    def build(self, data: dict[str, Any] | str, code: int | None = None) -> RoborockMessage:
        """Build an encoded B01 RPC response message."""
        message: dict[str, Any] = {
            "msgId": str(self.msg_id),
            "data": data,
        }
        if code is not None:
            message["code"] = code
        return self._build_dps(message)

    def _build_dps(self, message: dict[str, Any] | str) -> RoborockMessage:
        """Build an encoded B01 RPC response message."""
        dps_payload = {"dps": {"10000": json.dumps(message)}}
        self.seq += 1
        return RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_RESPONSE,
            payload=pad(
                json.dumps(dps_payload).encode(),
                AES.block_size,
            ),
            version=b"B01",
            seq=self.seq,
        )

    def build_map_response(self, payload: bytes) -> RoborockMessage:
        """Build a dummy MAP_RESPONSE message."""
        self.seq += 1
        return RoborockMessage(
            protocol=RoborockMessageProtocol.MAP_RESPONSE,
            payload=payload,
            version=b"B01",
            seq=self.seq,
        )


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


@pytest.fixture(name="product")
def product_fixture() -> HomeDataProduct:
    return HomeDataProduct(
        id="product-id-q7",
        name="Roborock Q7",
        model="roborock.vacuum.sc05",
        category=RoborockCategory.VACUUM,
    )


@pytest.fixture(name="device")
def device_fixture() -> HomeDataDevice:
    return HomeDataDevice(
        duid="abc123",
        name="Q7",
        local_key="key123key123key1",
        product_id="product-id-q7",
        sn="testsn012345",
    )


@pytest.fixture(name="expected_msg_id", autouse=True)
def next_message_id_fixture() -> Generator[int, None, None]:
    expected_msg_id = math.floor(time.time())
    with patch("roborock.protocols.b01_q7_protocol.get_next_int", return_value=expected_msg_id):
        yield expected_msg_id


@pytest.fixture(name="message_builder")
def message_builder_fixture(expected_msg_id: int) -> B01MessageBuilder:
    builder = B01MessageBuilder()
    builder.msg_id = expected_msg_id
    return builder


async def test_create_b01_q7_channel(
    device: HomeDataDevice, product: HomeDataProduct, fake_channel: FakeChannel
) -> None:
    channel = create_b01_q7_channel(device, product, fake_channel)  # type: ignore[arg-type]
    assert channel is not None
    assert channel.is_connected is False
    assert channel.is_local_connected is False


async def test_create_b01_q7_channel_missing_metadata(
    device: HomeDataDevice,
    product: HomeDataProduct,
    fake_channel: FakeChannel,
) -> None:
    """Test creating Q7 channel without required metadata raises RoborockException."""
    device.sn = None
    with pytest.raises(RoborockException, match="Device serial number and product model are required"):
        create_b01_q7_channel(device, product, fake_channel)  # type: ignore[arg-type]


async def test_q7_channel_send_command(
    device: HomeDataDevice,
    product: HomeDataProduct,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
) -> None:
    channel = create_b01_q7_channel(device, product, fake_channel)  # type: ignore[arg-type]
    fake_channel.response_queue.append(message_builder.build({"status": 1}))

    result = await channel.send_command("prop.get", {"property": ["status"]})
    assert result == {"status": 1}

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == B01_VERSION

    assert message.payload is not None
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    assert payload_data["dps"]["10000"]["method"] == "prop.get"


async def test_q7_channel_send_map_command(
    device: HomeDataDevice,
    product: HomeDataProduct,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
) -> None:
    channel = create_b01_q7_channel(device, product, fake_channel)  # type: ignore[arg-type]
    unrelated_msg = message_builder.build({"status": 1})
    fake_channel.response_queue.append(unrelated_msg)

    with patch(
        "roborock.devices.rpc.b01_q7_channel.decode_map_payload",
        return_value=b"inflated-payload",
    ) as mock_decode:
        task = asyncio.create_task(channel.send_map_command("service.upload_by_mapid", {"map_id": 123}))
        await asyncio.sleep(0)

        fake_channel.notify_subscribers(message_builder.build_map_response(b"raw-map-payload"))
        result = await task
        assert result == b"inflated-payload"
        mock_decode.assert_called_once()


async def test_send_decoded_command_non_dict_response(fake_channel: FakeChannel, message_builder: B01MessageBuilder):
    """Test validity of handling non-dict responses."""
    message = message_builder.build("some_string_error")
    fake_channel.response_queue.append(message)

    with pytest.raises(RoborockException, match="Unexpected data type for response"):
        await send_decoded_command(fake_channel, Q7RequestMessage(dps=10000, command="prop.get", params=[]))  # type: ignore[arg-type]


async def test_send_decoded_command_error_code(fake_channel: FakeChannel, message_builder: B01MessageBuilder):
    """Test that non-zero error codes from device are properly handled."""
    message = message_builder.build({}, code=5001)
    fake_channel.response_queue.append(message)

    with pytest.raises(RoborockException, match="B01 command failed with code 5001"):
        await send_decoded_command(fake_channel, Q7RequestMessage(dps=10000, command="prop.get", params=[]))  # type: ignore[arg-type]


async def test_send_decoded_command_allows_ok_string_ack(fake_channel: FakeChannel, message_builder: B01MessageBuilder):
    """Command ACKs may return plain string payloads like ``ok``."""
    message = message_builder.build("ok")
    fake_channel.response_queue.append(message)

    result = await send_decoded_command(
        cast(Any, fake_channel),
        Q7RequestMessage(dps=10000, command="service.set_room_clean", params=[]),  # type: ignore[arg-type]
    )

    assert result == "ok"


async def test_send_command_timeout(
    device: HomeDataDevice,
    product: HomeDataProduct,
    fake_channel: FakeChannel,
) -> None:
    """Test timeout behavior on regular send_command."""
    channel = create_b01_q7_channel(device, product, fake_channel)  # type: ignore[arg-type]

    with patch("roborock.devices.rpc.b01_q7_channel._TIMEOUT", 0.01):
        with pytest.raises(RoborockException, match="B01 command timed out after"):
            await channel.send_command("prop.get", {"property": ["status"]})


async def test_send_map_command_timeout(
    device: HomeDataDevice,
    product: HomeDataProduct,
    fake_channel: FakeChannel,
) -> None:
    """Test timeout behavior on send_map_command."""
    channel = create_b01_q7_channel(device, product, fake_channel)  # type: ignore[arg-type]

    with patch("roborock.devices.rpc.b01_q7_channel._TIMEOUT", 0.01):
        with pytest.raises(RoborockException, match="B01 map command timed out after"):
            await channel.send_map_command("service.upload_by_mapid", {"map_id": 123})


@pytest.mark.parametrize(
    "bad_payload",
    [
        # Undecryptable/unpad-failing message
        b"short",
        # Non-string dps value
        pad(b'{"dps": {"10000": 123}}', AES.block_size),
        # Invalid JSON string in dps value
        pad(b'{"dps": {"10000": "invalid-json{"}}', AES.block_size),
        # Message with incorrect msgId
        pad(b'{"dps": {"10000": "{\\"msgId\\": \\"999\\"}"}}', AES.block_size),
    ],
)
async def test_send_command_ignores_invalid_response(
    device: HomeDataDevice,
    product: HomeDataProduct,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
    bad_payload: bytes,
) -> None:
    """Test that invalid, unparsable, or wrong-msgId messages are skipped gracefully."""
    channel = create_b01_q7_channel(device, product, fake_channel)  # type: ignore[arg-type]

    bad_message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=bad_payload,
        version=b"B01",
    )
    fake_channel.response_queue.append(bad_message)

    task = asyncio.create_task(channel.send_command("prop.get", {"property": ["status"]}))
    await asyncio.sleep(0)

    fake_channel.notify_subscribers(message_builder.build({"status": 1}))
    result = await task
    assert result == {"status": 1}


async def test_send_command_ignores_messages_after_resolve(
    device: HomeDataDevice,
    product: HomeDataProduct,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
) -> None:
    """Test that messages arriving after the command has resolved are ignored."""
    channel = create_b01_q7_channel(device, product, fake_channel)  # type: ignore[arg-type]

    fake_channel.response_queue.append(message_builder.build({"status": 1}))

    task = asyncio.create_task(channel.send_command("prop.get", {"property": ["status"]}))
    await asyncio.sleep(0)

    fake_channel.notify_subscribers(message_builder.build({"status": 1}))
    result = await task
    assert result == {"status": 1}


async def test_send_command_general_exception(
    device: HomeDataDevice,
    product: HomeDataProduct,
    fake_channel: FakeChannel,
) -> None:
    """Test that non-RoborockException errors are propagated and logged."""
    channel = create_b01_q7_channel(device, product, fake_channel)  # type: ignore[arg-type]
    fake_channel.publish_side_effect = RuntimeError("Generic publish crash")

    with pytest.raises(RuntimeError, match="Generic publish crash"):
        await channel.send_command("prop.get", {"property": ["status"]})
