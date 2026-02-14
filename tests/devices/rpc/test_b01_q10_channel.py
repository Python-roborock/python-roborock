"""Tests for B01 Q10 channel functions."""

import json
from typing import Any, cast

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.rpc.b01_q10_channel import send_command, send_decoded_command
from roborock.exceptions import RoborockException
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.fixtures.channel_fixtures import FakeChannel


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


def build_q10_dps_response(dps: dict[str, Any]) -> RoborockMessage:
    """Build a Q10 MQTT response message with DPS data."""
    payload = {"dps": dps}
    return RoborockMessage(
        protocol=cast(RoborockMessageProtocol, 11),  # MQTT protocol for B01 Q10
        payload=json.dumps(payload).encode(),
        seq=0,
        version=b"B01",
    )


async def test_send_command(fake_channel: FakeChannel) -> None:
    """Test sending a command without waiting for response."""
    await send_command(fake_channel, B01_Q10_DP.START_CLEAN, {"cmd": 1})  # type: ignore[arg-type]

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.payload is not None
    payload_data = json.loads(message.payload.decode())
    assert payload_data == {"dps": {"201": {"cmd": 1}}}


async def test_send_decoded_command_basic(fake_channel: FakeChannel) -> None:
    """Test sending a command and receiving a decoded response."""
    # Queue a response
    fake_channel.response_queue.append(build_q10_dps_response({"121": 5, "122": 100}))

    result = await send_decoded_command(
        fake_channel,  # type: ignore[arg-type]
        B01_Q10_DP.REQUEST_DPS,
        {},
        expected_dps={B01_Q10_DP.STATUS, B01_Q10_DP.BATTERY},
    )

    assert B01_Q10_DP.STATUS in result
    assert B01_Q10_DP.BATTERY in result
    assert result[B01_Q10_DP.STATUS] == 5
    assert result[B01_Q10_DP.BATTERY] == 100


async def test_send_decoded_command_without_expected_dps(fake_channel: FakeChannel) -> None:
    """Test send_decoded_command accepts any response when expected_dps is None."""
    # Queue a response with any DPS
    fake_channel.response_queue.append(build_q10_dps_response({"123": 2}))

    result = await send_decoded_command(
        fake_channel,  # type: ignore[arg-type]
        B01_Q10_DP.REQUEST_DPS,
        {},
        expected_dps=None,
    )

    # Should accept any response
    assert B01_Q10_DP.FAN_LEVEL in result
    assert result[B01_Q10_DP.FAN_LEVEL] == 2


async def test_send_decoded_command_filters_by_expected_dps(fake_channel: FakeChannel) -> None:
    """Test that send_decoded_command filters by expected DPS."""
    # Queue response with expected DPS
    fake_channel.response_queue.append(build_q10_dps_response({"121": 5, "122": 100}))

    result = await send_decoded_command(
        fake_channel,  # type: ignore[arg-type]
        B01_Q10_DP.REQUEST_DPS,
        {},
        expected_dps={B01_Q10_DP.STATUS},
    )

    # Should accept response with expected DPS
    assert B01_Q10_DP.STATUS in result
    assert result[B01_Q10_DP.STATUS] == 5


async def test_send_decoded_command_timeout(fake_channel: FakeChannel) -> None:
    """Test that send_decoded_command times out when no matching response."""
    # Don't queue any response

    with pytest.raises(RoborockException, match="B01 Q10 command timed out"):
        await send_decoded_command(
            fake_channel,  # type: ignore[arg-type]
            B01_Q10_DP.REQUEST_DPS,
            {},
            expected_dps={B01_Q10_DP.STATUS},
        )


async def test_send_decoded_command_ignores_decode_errors(fake_channel: FakeChannel) -> None:
    """Test that send_decoded_command ignores non-decodable messages."""
    # Queue a valid response (invalid responses are ignored by not matching expected_dps)
    fake_channel.response_queue.append(build_q10_dps_response({"121": 5, "122": 100}))

    result = await send_decoded_command(
        fake_channel,  # type: ignore[arg-type]
        B01_Q10_DP.REQUEST_DPS,
        {},
        expected_dps={B01_Q10_DP.STATUS},
    )

    # Should successfully decode and return valid response
    assert B01_Q10_DP.STATUS in result


async def test_send_decoded_command_partial_match(fake_channel: FakeChannel) -> None:
    """Test that send_decoded_command accepts response with at least one expected DPS."""
    # Queue response with only one of multiple expected DPS
    fake_channel.response_queue.append(build_q10_dps_response({"121": 5}))

    result = await send_decoded_command(
        fake_channel,  # type: ignore[arg-type]
        B01_Q10_DP.REQUEST_DPS,
        {},
        expected_dps={B01_Q10_DP.STATUS, B01_Q10_DP.BATTERY},
    )

    # Should accept response with at least one expected DPS
    assert B01_Q10_DP.STATUS in result
    assert result[B01_Q10_DP.STATUS] == 5


async def test_send_decoded_command_published_message(fake_channel: FakeChannel) -> None:
    """Test that send_decoded_command publishes the correct message."""
    fake_channel.response_queue.append(build_q10_dps_response({"121": 5, "122": 100}))

    await send_decoded_command(
        fake_channel,  # type: ignore[arg-type]
        B01_Q10_DP.REQUEST_DPS,
        {},
        expected_dps={B01_Q10_DP.STATUS},
    )

    # Check published message
    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.payload is not None
    payload_data = json.loads(message.payload.decode())
    assert payload_data == {"dps": {"102": {}}}


async def test_send_decoded_command_with_params(fake_channel: FakeChannel) -> None:
    """Test send_decoded_command with command parameters."""
    fake_channel.response_queue.append(build_q10_dps_response({"121": 3, "122": 100}))

    await send_decoded_command(
        fake_channel,  # type: ignore[arg-type]
        B01_Q10_DP.START_CLEAN,
        {"cmd": 1},
        expected_dps={B01_Q10_DP.STATUS},
    )

    message = fake_channel.published_messages[0]
    assert message.payload is not None
    payload_data = json.loads(message.payload.decode())
    assert payload_data == {"dps": {"201": {"cmd": 1}}}
