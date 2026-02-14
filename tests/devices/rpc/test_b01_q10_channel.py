"""Tests for B01 Q10 channel functions."""

import json

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.rpc.b01_q10_channel import send_command
from tests.fixtures.channel_fixtures import FakeChannel


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


async def test_send_command(fake_channel: FakeChannel) -> None:
    """Test sending a command without waiting for response."""
    await send_command(fake_channel, B01_Q10_DP.START_CLEAN, {"cmd": 1})  # type: ignore[arg-type]

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.payload is not None
    payload_data = json.loads(message.payload.decode())
    assert payload_data == {"dps": {"201": {"cmd": 1}}}
