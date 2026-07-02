import json
from collections.abc import AsyncGenerator

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.rpc.b01_q10_channel import create_b01_q10_channel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import Q10DpsUpdate
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.fixtures.channel_fixtures import FakeChannel


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


async def test_create_b01_q10_channel(fake_channel: FakeChannel) -> None:
    channel = create_b01_q10_channel(fake_channel)  # type: ignore[arg-type]
    assert channel is not None
    assert channel.is_connected is False
    assert channel.is_local_connected is False


async def test_q10_channel_send_command(fake_channel: FakeChannel) -> None:
    channel = create_b01_q10_channel(fake_channel)  # type: ignore[arg-type]
    await channel.send_command(B01_Q10_DP.VOLUME, 50)

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.payload is not None
    payload_data = json.loads(message.payload.decode())
    assert payload_data == {"dps": {"26": 50}}


async def test_q10_channel_send_command_error(fake_channel: FakeChannel) -> None:
    channel = create_b01_q10_channel(fake_channel)  # type: ignore[arg-type]
    fake_channel.publish_side_effect = RoborockException("Publish error")

    with pytest.raises(RoborockException, match="Publish error"):
        await channel.send_command(B01_Q10_DP.VOLUME, 50)


async def test_q10_channel_subscribe_stream(fake_channel: FakeChannel) -> None:
    channel = create_b01_q10_channel(fake_channel)  # type: ignore[arg-type]

    async def simulate_messages() -> AsyncGenerator[RoborockMessage, None]:
        dps_payload = {"dps": {"26": 30}}
        # Valid message
        yield RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_RESPONSE,
            payload=json.dumps(dps_payload).encode(),
            version=b"B01",
        )
        # Invalid message (causes decode failure/RoborockException)
        yield RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_RESPONSE,
            payload=b"invalid-json{",
            version=b"B01",
        )
        # JSON but no dps key (returns None from decoder)
        yield RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_RESPONSE,
            payload=b'{"not_dps": 1}',
            version=b"B01",
        )
        # Another valid message
        dps_payload_2 = {"dps": {"26": 40}}
        yield RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_RESPONSE,
            payload=json.dumps(dps_payload_2).encode(),
            version=b"B01",
        )

    # Patch fake_channel.subscribe_stream
    setattr(fake_channel, "subscribe_stream", MockStream(simulate_messages()))

    messages = []
    async for msg in channel.subscribe_stream():
        messages.append(msg)

    assert len(messages) == 2
    assert isinstance(messages[0], Q10DpsUpdate)
    assert messages[0].dps[B01_Q10_DP.VOLUME] == 30
    assert isinstance(messages[1], Q10DpsUpdate)
    assert messages[1].dps[B01_Q10_DP.VOLUME] == 40


class MockStream:
    def __init__(self, generator: AsyncGenerator[RoborockMessage, None]) -> None:
        self._generator = generator

    def __call__(self, *args, **kwargs):
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self._generator.__anext__()
