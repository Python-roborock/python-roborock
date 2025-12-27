import asyncio
import json
import pathlib
from collections.abc import AsyncGenerator

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.traits.b01.q10 import Q10PropertiesApi
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.fixtures.channel_fixtures import FakeChannel

PAYLOAD_FILE = pathlib.Path("tests/protocols/testdata/b01_protocol/q10/dpRequetdps.json")
TEST_RESPONSE_PAYLOAD = PAYLOAD_FILE.read_bytes()


def build_b01_message(dps_payload: bytes, seq: int) -> RoborockMessage:
    """Build an encoded B01 RPC response message."""
    return RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=pad(dps_payload, AES.block_size),
        version=b"B01",
        seq=seq,
    )


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


@pytest.fixture(name="q10_api")
async def q10_api_fixture(fake_channel: FakeChannel) -> AsyncGenerator[Q10PropertiesApi, None]:
    properties = Q10PropertiesApi(fake_channel)  # type: ignore[arg-type]
    await properties.start()
    yield properties
    await properties.close()


async def test_subscribe(q10_api: Q10PropertiesApi, fake_channel: FakeChannel):
    """Test that Q10PropertiesApi handles incoming messages."""
    assert len(fake_channel.subscribers) == 1

    message_callback = fake_channel.subscribers[0]
    message_callback(build_b01_message(TEST_RESPONSE_PAYLOAD, seq=12345))

    # We currently don't do anything with the incoming messages in this test,
    # but we want to ensure no exceptions are raised during processing.
    await asyncio.sleep(0.1)  # Allow some time for the message to be processed


async def test_start_clean(q10_api: Q10PropertiesApi, fake_channel: FakeChannel):
    """Test sending a command via Q10PropertiesApi."""
    await q10_api.start_clean()

    assert len(fake_channel.published_messages) == 1
    published_message = fake_channel.published_messages[0]
    assert published_message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert published_message.version == b"B01"
    assert published_message.payload

    payload_data = json.loads(published_message.payload.decode())
    assert payload_data == {"dps": {"201": {"cmd": 1}}}


async def test_send_command(q10_api: Q10PropertiesApi, fake_channel: FakeChannel):
    """Test sending a command via Q10PropertiesApi."""
    await q10_api.send(B01_Q10_DP.REQUETDPS, {})

    assert len(fake_channel.published_messages) == 1
    published_message = fake_channel.published_messages[0]
    assert published_message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert published_message.version == b"B01"
    assert published_message.payload

    payload_data = json.loads(published_message.payload.decode())
    assert payload_data == {"dps": {"102": {}}}
