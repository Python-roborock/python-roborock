"""Tests for the V1Channel class.

This test simulates communication across both the MQTT and local connections
and failure modes, ensuring the V1Channel behaves correctly in various scenarios.
"""

import json
import logging
from unittest.mock import AsyncMock, Mock

import pytest

from roborock.containers import NetworkInfo, RoborockStateCode, S5MaxStatus, UserData
from roborock.devices.cache import CacheData, InMemoryCache
from roborock.devices.local_channel import LocalChannel, LocalSession
from roborock.devices.mqtt_channel import MqttChannel
from roborock.devices.v1_channel import V1Channel
from roborock.exceptions import RoborockException
from roborock.protocol import create_local_decoder, create_local_encoder, create_mqtt_decoder, create_mqtt_encoder
from roborock.protocols.v1_protocol import SecurityData
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.roborock_typing import RoborockCommand

from .. import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
TEST_DEVICE_UID = "abc123"
TEST_LOCAL_KEY = "local_key"
TEST_SECURITY_DATA = SecurityData(endpoint="test_endpoint", nonce=b"test_nonce_16byte")
TEST_HOST = "1.1.1.1"


# Test messages for V1 protocol
TEST_REQUEST = RoborockMessage(
    protocol=RoborockMessageProtocol.RPC_REQUEST,
    payload=json.dumps({"dps": {"101": json.dumps({"id": 12345, "method": "get_status"})}}).encode(),
)
TEST_RESPONSE = RoborockMessage(
    protocol=RoborockMessageProtocol.RPC_RESPONSE,
    payload=json.dumps(
        {"dps": {"102": json.dumps({"id": 12345, "result": {"state": RoborockStateCode.cleaning}})}}
    ).encode(),
)
TEST_NETWORK_INFO_RESPONSE = RoborockMessage(
    protocol=RoborockMessageProtocol.RPC_RESPONSE,
    payload=json.dumps({"dps": {"102": json.dumps({"id": 12345, "result": mock_data.NETWORK_INFO})}}).encode(),
)

TEST_NETWORKING_INFO = NetworkInfo.from_dict(mock_data.NETWORK_INFO)

# Encoders/Decoders
MQTT_ENCODER = create_mqtt_encoder(TEST_LOCAL_KEY)
MQTT_DECODER = create_mqtt_decoder(TEST_LOCAL_KEY)
LOCAL_ENCODER = create_local_encoder(TEST_LOCAL_KEY)
LOCAL_DECODER = create_local_decoder(TEST_LOCAL_KEY)


@pytest.fixture(name="mock_mqtt_channel")
def setup_mock_mqtt_channel() -> Mock:
    """Mock MQTT channel for testing."""
    mock_mqtt = AsyncMock(spec=MqttChannel)
    mock_mqtt.subscribe = AsyncMock()
    mock_mqtt.send_message = AsyncMock()
    return mock_mqtt


@pytest.fixture(name="mqtt_responses", autouse=True)
def setup_mqtt_responses(mock_mqtt_channel: Mock) -> list[RoborockMessage]:
    """Fixture to provide a list of mock MQTT responses."""

    responses: list[RoborockMessage] = [TEST_NETWORK_INFO_RESPONSE]

    def send_message(*args) -> RoborockMessage:
        return responses.pop(0)

    mock_mqtt_channel.send_message.side_effect = send_message
    return responses


@pytest.fixture(name="mock_local_channel")
def setup_mock_local_channel() -> Mock:
    """Mock Local channel for testing."""
    mock_local = AsyncMock(spec=LocalChannel)
    mock_local.connect = AsyncMock()
    mock_local.subscribe = AsyncMock()
    mock_local.send_message = AsyncMock()
    return mock_local


@pytest.fixture(name="mock_local_session")
def setup_mock_local_session(mock_local_channel: Mock) -> Mock:
    """Mock Local session factory for testing."""
    mock_session = Mock(spec=LocalSession)
    mock_session.return_value = mock_local_channel
    return mock_session


@pytest.fixture(name="v1_channel")
def setup_v1_channel(
    mock_mqtt_channel: Mock,
    mock_local_session: Mock,
) -> V1Channel:
    """Fixture to set up the V1 channel for tests."""
    return V1Channel(
        device_uid=TEST_DEVICE_UID,
        security_data=TEST_SECURITY_DATA,
        mqtt_channel=mock_mqtt_channel,
        local_session=mock_local_session,
        cache=InMemoryCache(),
    )


@pytest.fixture(name="warning_caplog")
def setup_warning_caplog(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    """Fixture to capture warning messages."""
    caplog.set_level(logging.WARNING)
    return caplog


async def test_v1_channel_subscribe_mqtt_only_success(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_session: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test successful subscription with MQTT only (local connection fails)."""
    # Setup: MQTT succeeds, local fails
    mqtt_unsub = Mock()
    mock_mqtt_channel.subscribe.return_value = mqtt_unsub
    mock_mqtt_channel.send_message.return_value = TEST_NETWORK_INFO_RESPONSE
    mock_local_channel.connect.side_effect = RoborockException("Connection failed")

    callback = Mock()
    unsub = await v1_channel.subscribe(callback)

    # Verify MQTT connection was established
    mock_mqtt_channel.subscribe.assert_called_once()
    # Check that a callback was passed to MQTT subscription
    assert callable(mock_mqtt_channel.subscribe.call_args[0][0])

    # Verify local connection was attempted but failed
    mock_local_session.assert_called_once_with(TEST_HOST)
    mock_local_channel.connect.assert_called_once()

    # Verify properties
    assert v1_channel.is_mqtt_connected
    assert not v1_channel.is_local_connected

    # Test unsubscribe
    unsub()
    mqtt_unsub.assert_called_once()


async def test_v1_channel_subscribe_both_connections_success(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test successful subscription with both MQTT and local connections."""
    # Setup: both succeed
    mqtt_unsub = Mock()
    local_unsub = Mock()
    mock_mqtt_channel.subscribe.return_value = mqtt_unsub
    mock_local_channel.subscribe.return_value = local_unsub

    # Mock network info retrieval
    callback = Mock()
    unsub = await v1_channel.subscribe(callback)

    # Verify both connections established
    mock_mqtt_channel.subscribe.assert_called_once()
    mock_local_channel.connect.assert_called_once()
    mock_local_channel.subscribe.assert_called_once()

    # Verify properties
    assert v1_channel.is_mqtt_connected
    assert v1_channel.is_local_connected

    # Test unsubscribe cleans up both
    unsub()
    mqtt_unsub.assert_called_once()
    local_unsub.assert_called_once()


async def test_v1_channel_subscribe_already_connected_error(v1_channel: V1Channel, mock_mqtt_channel: Mock) -> None:
    """Test error when trying to subscribe when already connected."""
    mock_mqtt_channel.subscribe.return_value = Mock()

    # First subscription succeeds
    await v1_channel.subscribe(Mock())

    # Second subscription should fail
    with pytest.raises(ValueError, match="Already connected to the device"):
        await v1_channel.subscribe(Mock())


async def test_v1_channel_local_connection_warning_logged(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
    warning_caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that local connection failures are logged as warnings."""
    mock_mqtt_channel.subscribe.return_value = Mock()
    mock_local_channel.connect.side_effect = RoborockException("Local connection failed")

    await v1_channel.subscribe(Mock())

    assert "Could not establish local connection for device abc123" in warning_caplog.text
    assert "Local connection failed" in warning_caplog.text


# V1Channel command sending with fallback logic tests


async def test_v1_channel_send_command_local_preferred(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test command sending prefers local connection when available."""
    # Establish connections
    await v1_channel.subscribe(Mock())
    mock_mqtt_channel.send_message.reset_mock(return_value=False)

    # Send command
    mock_local_channel.send_message.return_value = TEST_RESPONSE
    result = await v1_channel.rpc_channel.send_command(
        RoborockCommand.CHANGE_SOUND_VOLUME,
        response_type=S5MaxStatus,
    )

    # Verify local was used, not MQTT
    mock_local_channel.send_message.assert_called_once()
    mock_mqtt_channel.send_message.assert_not_called()
    assert result.state == RoborockStateCode.cleaning


async def test_v1_channel_send_command_local_fails(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
    mqtt_responses: list[RoborockMessage],
) -> None:
    """Test case where sending with local connection fails."""

    # Establish connections
    await v1_channel.subscribe(Mock())
    mock_mqtt_channel.send_message.reset_mock(return_value=False)

    # Local command fails
    mock_local_channel.send_message.side_effect = RoborockException("Local failed")

    # Send command
    mqtt_responses.append(TEST_RESPONSE)
    with pytest.raises(RoborockException, match="Local failed"):
        await v1_channel.rpc_channel.send_command(
            RoborockCommand.CHANGE_SOUND_VOLUME,
            response_type=S5MaxStatus,
        )

    # Verify local was attempted but not mqtt
    mock_local_channel.send_message.assert_called_once()
    mock_mqtt_channel.send_message.assert_not_called()


async def test_v1_channel_send_decoded_command_mqtt_only(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
    mqtt_responses: list[RoborockMessage],
) -> None:
    """Test command sending works with MQTT only."""
    # Setup: only MQTT connection
    # mock_mqtt_channel.subscribe.return_value = Mock()
    mock_local_channel.connect.side_effect = RoborockException("No local")

    await v1_channel.subscribe(Mock())
    mock_mqtt_channel.send_message.assert_called_once()  # network info
    mock_mqtt_channel.send_message.reset_mock(return_value=False)

    # Send command
    mqtt_responses.append(TEST_RESPONSE)
    result = await v1_channel.rpc_channel.send_command(
        RoborockCommand.CHANGE_SOUND_VOLUME,
        response_type=S5MaxStatus,
    )

    # Verify only MQTT was used
    mock_local_channel.send_message.assert_not_called()
    mock_mqtt_channel.send_message.assert_called_once()
    assert result.state == RoborockStateCode.cleaning


async def test_v1_channel_send_decoded_command_with_params(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test command sending with parameters."""

    await v1_channel.subscribe(Mock())

    # Send command with params
    mock_local_channel.send_message.return_value = TEST_RESPONSE
    test_params = {"volume": 80}
    await v1_channel.rpc_channel.send_command(
        RoborockCommand.CHANGE_SOUND_VOLUME,
        response_type=S5MaxStatus,
        params=test_params,
    )

    # Verify command was sent with correct params
    mock_local_channel.send_message.assert_called_once()
    call_args = mock_local_channel.send_message.call_args
    sent_message = call_args[0][0]
    assert sent_message
    assert isinstance(sent_message, RoborockMessage)
    assert sent_message.payload
    payload = sent_message.payload.decode()
    json_data = json.loads(payload)
    assert "dps" in json_data
    assert "101" in json_data["dps"]
    decoded_payload = json.loads(json_data["dps"]["101"])
    assert decoded_payload["method"] == "change_sound_volume"
    assert decoded_payload["params"] == {"volume": 80}


async def test_v1_channel_subscription_receives_mqtt_messages(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test that subscribed callback receives MQTT messages."""
    callback = Mock()

    # Setup MQTT subscription to capture the internal callback
    mock_mqtt_channel.subscribe.return_value = Mock()
    mock_local_channel.connect.side_effect = RoborockException("Local failed")

    # Subscribe
    await v1_channel.subscribe(callback)

    # Get the MQTT callback that was registered
    mqtt_callback = mock_mqtt_channel.subscribe.call_args[0][0]

    # Simulate MQTT message
    test_message = TEST_RESPONSE
    mqtt_callback(test_message)

    # Verify user callback was called
    callback.assert_called_once_with(test_message)


async def test_v1_channel_subscription_receives_local_messages(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test that subscribed callback receives local messages."""
    callback = Mock()

    # Setup both connections
    mock_mqtt_channel.subscribe.return_value = Mock()
    mock_local_channel.subscribe.return_value = Mock()

    # Subscribe
    await v1_channel.subscribe(callback)

    # Get the local callback that was registered
    local_callback = mock_local_channel.subscribe.call_args[0][0]

    # Simulate local message
    test_message = TEST_RESPONSE
    local_callback(test_message)

    # Verify user callback was called
    callback.assert_called_once_with(test_message)


# V1Channel networking tests


async def test_v1_channel_networking_info_retrieved_during_connection(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
    mock_local_session: Mock,
) -> None:
    """Test that networking information is retrieved during local connection setup."""
    # Setup: MQTT returns network info when requested
    mock_mqtt_channel.subscribe.return_value = Mock()
    mock_mqtt_channel.send_message.return_value = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=json.dumps({"dps": {"102": json.dumps({"id": 12345, "result": mock_data.NETWORK_INFO})}}).encode(),
    )
    mock_local_channel.subscribe.return_value = Mock()

    # Subscribe - this should trigger network info retrieval for local connection
    await v1_channel.subscribe(Mock())

    # Verify both connections are established
    assert v1_channel.is_mqtt_connected
    assert v1_channel.is_local_connected

    # Verify network info was requested via MQTT
    mock_mqtt_channel.send_message.assert_called_once()

    # Verify local session was created with the correct IP
    mock_local_session.assert_called_once_with(mock_data.NETWORK_INFO["ip"])


async def test_v1_channel_networking_info_cached_during_connection(
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
    mock_local_session: Mock,
) -> None:
    """Test that networking information is cached and reused on subsequent connections."""

    # Create a cache with pre-populated network info
    cache_data = CacheData()
    cache_data.network_info[TEST_DEVICE_UID] = TEST_NETWORKING_INFO

    mock_cache = AsyncMock()
    mock_cache.get.return_value = cache_data
    mock_cache.set = AsyncMock()

    # Setup: MQTT and local connections succeed
    mock_mqtt_channel.subscribe.return_value = Mock()
    mock_local_channel.subscribe.return_value = Mock()

    # Create V1Channel with the mock cache
    v1_channel = V1Channel(
        device_uid=TEST_DEVICE_UID,
        security_data=TEST_SECURITY_DATA,
        mqtt_channel=mock_mqtt_channel,
        local_session=mock_local_session,
        cache=mock_cache,
    )

    # Subscribe - should use cached network info
    await v1_channel.subscribe(Mock())

    # Verify both connections are established
    assert v1_channel.is_mqtt_connected
    assert v1_channel.is_local_connected

    # Verify network info was NOT requested via MQTT (cache hit)
    mock_mqtt_channel.send_message.assert_not_called()

    # Verify local session was created with the correct IP from cache
    mock_local_session.assert_called_once_with(mock_data.NETWORK_INFO["ip"])

    # Verify cache was accessed but not updated (cache hit)
    mock_cache.get.assert_called_once()
    mock_cache.set.assert_not_called()


# V1Channel edge cases tests


async def test_v1_channel_local_connect_network_info_failure(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
) -> None:
    """Test local connection when network info retrieval fails."""
    mock_mqtt_channel.send_message.side_effect = RoborockException("Network info failed")

    with pytest.raises(RoborockException):
        await v1_channel._local_connect()


async def test_v1_channel_local_connect_connection_failure(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test local connection when connection itself fails."""
    # Network info succeeds but connection fails
    mock_mqtt_channel.send_message.return_value = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=json.dumps({"dps": {"102": json.dumps({"id": 12345, "result": mock_data.NETWORK_INFO})}}).encode(),
    )
    mock_local_channel.connect.side_effect = RoborockException("Connection failed")

    with pytest.raises(RoborockException):
        await v1_channel._local_connect()


async def test_v1_channel_command_encoding_validation(
    v1_channel: V1Channel,
    mqtt_responses: list[RoborockMessage],
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test that command encoding works for different protocols."""
    await v1_channel.subscribe(Mock())
    mock_mqtt_channel.send_message.reset_mock(return_value=False)

    # Send mqtt command and capture the request
    mqtt_responses.append(TEST_RESPONSE)
    await v1_channel.mqtt_rpc_channel.send_command(RoborockCommand.CHANGE_SOUND_VOLUME, params={"volume": 50})
    mock_mqtt_channel.send_message.assert_called_once()
    mqtt_message = mock_mqtt_channel.send_message.call_args[0][0]

    # Send local command and capture the request
    mock_local_channel.send_message.return_value = TEST_RESPONSE
    await v1_channel.rpc_channel.send_command(RoborockCommand.CHANGE_SOUND_VOLUME, params={"volume": 50})
    mock_local_channel.send_message.assert_called_once()
    local_message = mock_local_channel.send_message.call_args[0][0]

    # Verify both are RoborockMessage instances
    assert isinstance(mqtt_message, RoborockMessage)
    assert isinstance(local_message, RoborockMessage)

    # But they should have different protocols
    assert mqtt_message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert local_message.protocol == RoborockMessageProtocol.GENERAL_REQUEST


async def test_v1_channel_connection_state_properties(v1_channel: V1Channel) -> None:
    """Test connection state properties work correctly."""
    # Initially not connected
    assert not v1_channel.is_mqtt_connected
    assert not v1_channel.is_local_connected

    # Set up MQTT connection
    v1_channel._mqtt_unsub = Mock()
    assert v1_channel.is_mqtt_connected
    assert not v1_channel.is_local_connected

    # Set up local connection
    v1_channel._local_unsub = Mock()
    assert v1_channel.is_mqtt_connected
    assert v1_channel.is_local_connected

    # Clear connections
    v1_channel._mqtt_unsub = None
    v1_channel._local_unsub = None
    assert not v1_channel.is_mqtt_connected
    assert not v1_channel.is_local_connected


async def test_v1_channel_full_subscribe_and_command_flow(
    mock_mqtt_channel: Mock,
    mock_local_session: Mock,
    mock_local_channel: Mock,
    mqtt_responses: list[RoborockMessage],
) -> None:
    """Test the complete flow from subscription to command execution."""
    # Setup: successful connections and responses
    mqtt_unsub = Mock()
    local_unsub = Mock()
    mock_mqtt_channel.subscribe.return_value = mqtt_unsub
    mock_local_channel.subscribe.return_value = local_unsub
    mock_local_channel.send_message.return_value = TEST_RESPONSE

    # Create V1Channel and subscribe
    v1_channel = V1Channel(
        device_uid=TEST_DEVICE_UID,
        security_data=TEST_SECURITY_DATA,
        mqtt_channel=mock_mqtt_channel,
        local_session=mock_local_session,
        cache=InMemoryCache(),
    )

    # Mock network info for local connection
    callback = Mock()
    unsub = await v1_channel.subscribe(callback)
    mock_mqtt_channel.send_message.reset_mock(return_value=False)

    # Verify both connections established
    assert v1_channel.is_mqtt_connected
    assert v1_channel.is_local_connected

    # Send a command (should use local)
    result = await v1_channel.rpc_channel.send_command(
        RoborockCommand.GET_STATUS,
        response_type=S5MaxStatus,
    )

    # Verify command was sent via local connection
    mock_local_channel.send_message.assert_called_once()
    mock_mqtt_channel.send_message.assert_not_called()
    assert result.state == RoborockStateCode.cleaning

    # Test message callback
    test_message = TEST_RESPONSE
    v1_channel._callback = callback
    v1_channel._on_local_message(test_message)
    callback.assert_called_with(test_message)

    # Clean up
    unsub()
    mqtt_unsub.assert_called_once()
    local_unsub.assert_called_once()
