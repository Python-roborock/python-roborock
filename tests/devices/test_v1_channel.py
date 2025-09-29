"""Tests for the V1Channel class.

This test simulates communication across both the MQTT and local connections
and failure modes, ensuring the V1Channel behaves correctly in various scenarios.
"""

import json
import logging
from collections.abc import Iterator
from unittest.mock import AsyncMock, Mock, patch

import pytest

from roborock.containers import NetworkInfo, RoborockStateCode, S5MaxStatus, UserData
from roborock.devices.cache import CacheData, InMemoryCache
from roborock.devices.local_channel import LocalSession
from roborock.devices.v1_channel import V1Channel
from roborock.exceptions import RoborockException
from roborock.protocol import create_local_decoder, create_local_encoder, create_mqtt_decoder, create_mqtt_encoder
from roborock.protocols.v1_protocol import SecurityData
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.roborock_typing import RoborockCommand

from .. import mock_data
from ..conftest import FakeChannel

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
TEST_DEVICE_UID = "abc123"
TEST_LOCAL_KEY = "local_key"
TEST_SECURITY_DATA = SecurityData(endpoint="test_endpoint", nonce=b"test_nonce_16byte")
TEST_HOST = "1.1.1.1"


# Test messages for V1 protocol
TEST_REQUEST = RoborockMessage(
    protocol=RoborockMessageProtocol.RPC_REQUEST,
    payload=json.dumps({"dps": {"101": json.dumps({"id": 12346, "method": "get_status"})}}).encode(),
)
TEST_RESPONSE = RoborockMessage(
    protocol=RoborockMessageProtocol.RPC_RESPONSE,
    payload=json.dumps(
        {"dps": {"102": json.dumps({"id": 12346, "result": {"state": RoborockStateCode.cleaning}})}}
    ).encode(),
)
TEST_RESPONSE_2 = RoborockMessage(
    protocol=RoborockMessageProtocol.RPC_RESPONSE,
    payload=json.dumps(
        {"dps": {"102": json.dumps({"id": 12347, "result": {"state": RoborockStateCode.cleaning}})}}
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
async def setup_mock_mqtt_channel() -> FakeChannel:
    """Mock MQTT channel for testing."""
    channel = FakeChannel()
    await channel.connect()
    return channel


@pytest.fixture(name="mock_local_channel")
async def setup_mock_local_channel() -> FakeChannel:
    """Mock Local channel for testing."""
    return FakeChannel()


@pytest.fixture(name="mock_local_session")
def setup_mock_local_session(mock_local_channel: Mock) -> Mock:
    """Mock Local session factory for testing."""
    mock_session = Mock(spec=LocalSession)
    mock_session.return_value = mock_local_channel
    return mock_session


@pytest.fixture(name="mock_request_id", autouse=True)
def setup_mock_request_id() -> Iterator[None]:
    """Assign sequential request ids for testing."""

    next_id = 12345

    def fake_next_int(*args) -> int:
        nonlocal next_id
        id_to_return = next_id
        next_id += 1
        return id_to_return

    with patch("roborock.protocols.v1_protocol.get_next_int", side_effect=fake_next_int):
        yield


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
    mock_mqtt_channel: FakeChannel,
    mock_local_session: Mock,
    mock_local_channel: FakeChannel,
) -> None:
    """Test successful subscription with MQTT only (local connection fails)."""
    # Setup: MQTT succeeds, local fails
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    mock_local_channel.connect.side_effect = RoborockException("Connection failed")

    callback = Mock()
    unsub = await v1_channel.subscribe(callback)

    # Verify MQTT connection was established
    assert mock_mqtt_channel.subscribers

    # Verify local connection was attempted but failed
    mock_local_session.assert_called_once_with(TEST_HOST)
    mock_local_channel.connect.assert_called_once()

    # Verify properties
    assert v1_channel.is_mqtt_connected
    assert not v1_channel.is_local_connected

    # Test unsubscribe
    unsub()
    assert not mock_mqtt_channel.subscribers


async def test_v1_channel_mqtt_disconnected(
    v1_channel: V1Channel,
    mock_mqtt_channel: FakeChannel,
    mock_local_session: Mock,
    mock_local_channel: FakeChannel,
) -> None:
    """Test successful subscription with MQTT only (local connection fails)."""
    # Setup: MQTT succeeds, local fails
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    mock_local_channel.connect.side_effect = RoborockException("Connection failed")

    callback = Mock()
    unsub = await v1_channel.subscribe(callback)

    # Verify MQTT connection was established
    assert mock_mqtt_channel.subscribers

    # Verify local connection was attempted but failed
    mock_local_session.assert_called_once_with(TEST_HOST)
    mock_local_channel.connect.assert_called_once()

    # Simulate an MQTT disconnection where the channel is not healthy
    await mock_mqtt_channel.close()

    # Verify properties
    assert not v1_channel.is_mqtt_connected
    assert not v1_channel.is_local_connected

    # Test unsubscribe
    unsub()
    assert not mock_mqtt_channel.subscribers


async def test_v1_channel_subscribe_local_success(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
    mock_local_session: Mock,
) -> None:
    """Test successful subscription with local connections."""
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)

    # Mock network info retrieval
    callback = Mock()
    unsub = await v1_channel.subscribe(callback)

    # Verify local connection was attempted and succeeded
    mock_local_session.assert_called_once_with(TEST_HOST)
    mock_local_channel.connect.assert_called_once()

    # Verify local connection established and not mqtt
    assert not mock_mqtt_channel.subscribers
    assert mock_local_channel.subscribers

    # Verify properties
    assert not v1_channel.is_mqtt_connected
    assert v1_channel.is_local_connected

    # Test unsubscribe cleans up both
    unsub()
    assert not mock_mqtt_channel.subscribers
    assert not mock_local_channel.subscribers


async def test_v1_channel_subscribe_already_connected_error(v1_channel: V1Channel, mock_mqtt_channel: Mock) -> None:
    """Test error when trying to subscribe when already connected."""
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)

    # First subscription succeeds
    await v1_channel.subscribe(Mock())

    # Second subscription should fail
    with pytest.raises(ValueError, match="Only one subscription allowed at a time"):
        await v1_channel.subscribe(Mock())


async def test_v1_channel_local_connection_warning_logged(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
    warning_caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that local connection failures are logged as warnings."""
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    mock_local_channel.connect.side_effect = RoborockException("Local connection failed")

    await v1_channel.subscribe(Mock())

    assert "Could not establish local connection for device abc123" in warning_caplog.text
    assert "Local connection failed" in warning_caplog.text


async def test_v1_channel_send_command_local_preferred(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test command sending prefers local connection when available."""
    # Establish connections
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    await v1_channel.subscribe(Mock())

    # Send command
    mock_local_channel.response_queue.append(TEST_RESPONSE)
    result = await v1_channel.rpc_channel.send_command(
        RoborockCommand.CHANGE_SOUND_VOLUME,
        response_type=S5MaxStatus,
    )

    # Verify local response was parsed
    assert result.state == RoborockStateCode.cleaning


async def test_v1_channel_send_command_local_fails(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test case where sending with local connection fails."""

    # Establish connections
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    await v1_channel.subscribe(Mock())

    # Local command fails
    mock_local_channel.publish = Mock()
    mock_local_channel.publish.side_effect = RoborockException("Local failed")

    # Send command
    with pytest.raises(RoborockException, match="Local failed"):
        await v1_channel.rpc_channel.send_command(
            RoborockCommand.CHANGE_SOUND_VOLUME,
            response_type=S5MaxStatus,
        )


async def test_v1_channel_send_decoded_command_mqtt_only(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test command sending works with MQTT only."""
    # Setup: only MQTT connection
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    mock_local_channel.connect.side_effect = RoborockException("No local")

    await v1_channel.subscribe(Mock())

    # Send command
    mock_mqtt_channel.response_queue.append(TEST_RESPONSE)
    result = await v1_channel.rpc_channel.send_command(
        RoborockCommand.CHANGE_SOUND_VOLUME,
        response_type=S5MaxStatus,
    )

    # Verify only MQTT was used
    assert result.state == RoborockStateCode.cleaning


async def test_v1_channel_send_decoded_command_with_params(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test command sending with parameters."""

    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    await v1_channel.subscribe(Mock())

    # Send command with params
    mock_local_channel.response_queue.append(TEST_RESPONSE)
    test_params = {"volume": 80}
    await v1_channel.rpc_channel.send_command(
        RoborockCommand.CHANGE_SOUND_VOLUME,
        response_type=S5MaxStatus,
        params=test_params,
    )

    # Verify command was sent with correct params
    assert mock_local_channel.published_messages
    sent_message = mock_local_channel.published_messages[0]
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


async def test_v1_channel_networking_info_retrieved_during_connection(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
    mock_local_session: Mock,
) -> None:
    """Test that networking information is retrieved during local connection setup."""
    # Setup: MQTT returns network info when requested
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)

    # Subscribe - this should trigger network info retrieval for local connection
    await v1_channel.subscribe(Mock())

    # Verify local connection was esablished
    assert v1_channel.is_local_connected

    # Verify network info was requested via MQTT
    assert mock_mqtt_channel.published_messages

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

    # Verify local connections are established
    assert v1_channel.is_local_connected

    # Verify network info was NOT requested via MQTT (cache hit)
    assert not mock_mqtt_channel.published_messages
    assert not mock_local_channel.published_messages

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
    mock_mqtt_channel.publish_side_effect = RoborockException("Network info failed")

    with pytest.raises(RoborockException):
        await v1_channel._local_connect()


async def test_v1_channel_command_encoding_validation(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test that command encoding works for different protocols."""
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    await v1_channel.subscribe(Mock())

    # Send mqtt command and capture the request
    mock_mqtt_channel.response_queue.append(TEST_RESPONSE)
    await v1_channel.mqtt_rpc_channel.send_command(RoborockCommand.CHANGE_SOUND_VOLUME, params={"volume": 50})
    assert mock_mqtt_channel.published_messages
    mqtt_message = mock_mqtt_channel.published_messages[0]

    # Send local command and capture the request
    mock_local_channel.response_queue.append(TEST_RESPONSE_2)
    await v1_channel.rpc_channel.send_command(RoborockCommand.CHANGE_SOUND_VOLUME, params={"volume": 50})
    assert mock_local_channel.published_messages
    local_message = mock_local_channel.published_messages[0]

    # Verify both are RoborockMessage instances
    assert isinstance(mqtt_message, RoborockMessage)
    assert isinstance(local_message, RoborockMessage)

    # But they should have different protocols
    assert mqtt_message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert local_message.protocol == RoborockMessageProtocol.GENERAL_REQUEST
