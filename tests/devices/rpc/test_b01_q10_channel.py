"""Tests for the b01_q10_channel."""

from unittest.mock import patch

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.rpc.b01_q10_channel import send_decoded_command
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import encode_mqtt_payload
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.fixtures.channel_fixtures import FakeChannel


@pytest.fixture
def mock_mqtt_channel() -> FakeChannel:
    """Fixture for a fake MQTT channel."""
    return FakeChannel()


async def test_send_decoded_command_success(mock_mqtt_channel: FakeChannel):
    """Test successful command sending and response decoding."""
    # Prepare response data
    response_data = {
        B01_Q10_DP.STATUS: 1,  # sleepstate
        B01_Q10_DP.BATTERY: 91,
    }

    # Encode response message
    encoded = encode_mqtt_payload(B01_Q10_DP.STATUS, {})
    response_message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=encoded.payload,
        version=encoded.version,
    )

    # Mock the decode_rpc_response to return test data
    with patch("roborock.devices.rpc.b01_q10_channel.decode_rpc_response") as mock_decode:
        mock_decode.return_value = response_data
        mock_mqtt_channel.response_queue.append(response_message)

        # Call the function
        result = await send_decoded_command(
            mock_mqtt_channel,  # type: ignore[arg-type]
            B01_Q10_DP.REQUETDPS,
            {},
            expected_dps={B01_Q10_DP.STATUS, B01_Q10_DP.BATTERY},
        )

        # Assertions
        assert result == response_data
        mock_mqtt_channel.publish.assert_awaited_once()
        mock_mqtt_channel.subscribe.assert_awaited_once()


async def test_send_decoded_command_filters_by_expected_dps(mock_mqtt_channel: FakeChannel):
    """Test that responses are filtered by expected_dps."""
    # First response doesn't match expected_dps
    non_matching_data = {B01_Q10_DP.CLEANING_PROGRESS: 50}

    # Second response matches
    matching_data = {B01_Q10_DP.STATUS: 1, B01_Q10_DP.BATTERY: 91}

    encoded1 = encode_mqtt_payload(B01_Q10_DP.CLEANING_PROGRESS, {})
    response1 = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=encoded1.payload,
        version=encoded1.version,
    )

    encoded2 = encode_mqtt_payload(B01_Q10_DP.STATUS, {})
    response2 = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=encoded2.payload,
        version=encoded2.version,
    )

    with patch("roborock.devices.rpc.b01_q10_channel.decode_rpc_response") as mock_decode:
        mock_decode.side_effect = [non_matching_data, matching_data]

        # Add both responses to queue
        mock_mqtt_channel.response_queue.extend([response1, response2])

        # Call the function with expected_dps
        result = await send_decoded_command(
            mock_mqtt_channel,  # type: ignore[arg-type]
            B01_Q10_DP.REQUETDPS,
            {},
            expected_dps={B01_Q10_DP.STATUS, B01_Q10_DP.BATTERY},
        )

        # Should get the matching response, not the first one
        assert result == matching_data


async def test_send_decoded_command_timeout():
    """Test that command times out if no matching response."""
    mock_mqtt_channel = FakeChannel()

    with patch("roborock.devices.rpc.b01_q10_channel.decode_rpc_response") as mock_decode:
        mock_decode.return_value = {B01_Q10_DP.CLEANING_PROGRESS: 50}

        # Don't add any responses to queue
        with pytest.raises(RoborockException, match="timed out"):
            await send_decoded_command(
                mock_mqtt_channel,  # type: ignore[arg-type]
                B01_Q10_DP.REQUETDPS,
                {},
                expected_dps={B01_Q10_DP.STATUS},  # Won't match CLEANING_PROGRESS
            )


async def test_send_decoded_command_ignores_decode_errors(mock_mqtt_channel: FakeChannel):
    """Test that decode errors are logged but don't fail the command."""
    # First response has decode error, second is valid
    valid_data = {B01_Q10_DP.STATUS: 1}

    encoded1 = encode_mqtt_payload(B01_Q10_DP.STATUS, {})
    response1 = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=encoded1.payload,
        version=encoded1.version,
    )

    encoded2 = encode_mqtt_payload(B01_Q10_DP.STATUS, {})
    response2 = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=encoded2.payload,
        version=encoded2.version,
    )

    with patch("roborock.devices.rpc.b01_q10_channel.decode_rpc_response") as mock_decode:
        # First call raises, second returns valid data
        mock_decode.side_effect = [
            RoborockException("Decode error"),
            valid_data,
        ]

        mock_mqtt_channel.response_queue.extend([response1, response2])

        # Command should still succeed with second response
        result = await send_decoded_command(
            mock_mqtt_channel,  # type: ignore[arg-type]
            B01_Q10_DP.REQUETDPS,
            {},
            expected_dps={B01_Q10_DP.STATUS},
        )

        assert result == valid_data


async def test_send_decoded_command_no_expected_dps_filter():
    """Test that without expected_dps, any decoded response is accepted."""
    mock_mqtt_channel = FakeChannel()

    response_data = {B01_Q10_DP.CLEANING_PROGRESS: 50}

    encoded = encode_mqtt_payload(B01_Q10_DP.CLEANING_PROGRESS, {})
    response = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=encoded.payload,
        version=encoded.version,
    )

    with patch("roborock.devices.rpc.b01_q10_channel.decode_rpc_response") as mock_decode:
        mock_decode.return_value = response_data
        mock_mqtt_channel.response_queue.append(response)

        # Call without expected_dps
        result = await send_decoded_command(
            mock_mqtt_channel,  # type: ignore[arg-type]
            B01_Q10_DP.REQUETDPS,
            {},
        )

        assert result == response_data


async def test_send_decoded_command_publishes_message(mock_mqtt_channel: FakeChannel):
    """Test that the command is properly published."""
    response_data = {B01_Q10_DP.STATUS: 1}

    encoded = encode_mqtt_payload(B01_Q10_DP.STATUS, {})
    response = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=encoded.payload,
        version=encoded.version,
    )

    with patch("roborock.devices.rpc.b01_q10_channel.decode_rpc_response") as mock_decode:
        mock_decode.return_value = response_data
        mock_mqtt_channel.response_queue.append(response)

        await send_decoded_command(
            mock_mqtt_channel,  # type: ignore[arg-type]
            B01_Q10_DP.REQUETDPS,
            {},
        )

        # Verify message was published
        assert len(mock_mqtt_channel.published_messages) == 1
