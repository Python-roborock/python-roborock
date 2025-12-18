"""Tests for the V1Channel class.

This test simulates communication across both the MQTT and local connections
and failure modes, ensuring the V1Channel behaves correctly in various scenarios.
"""

import json
import logging
from collections.abc import Iterator
from unittest.mock import AsyncMock, Mock, patch

import pytest

from roborock.data import NetworkInfo, RoborockStateCode, S5MaxStatus, UserData
from roborock.devices.cache import DeviceCache, DeviceCacheData, InMemoryCache
from roborock.devices.local_channel import LocalSession
from roborock.devices.v1_channel import V1Channel
from roborock.exceptions import RoborockException
from roborock.protocol import (
    create_local_decoder,
    create_local_encoder,
    create_mqtt_decoder,
    create_mqtt_encoder,
)
from roborock.protocols.v1_protocol import MapResponse, SecurityData, V1RpcChannel
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.roborock_typing import RoborockCommand

from .. import mock_data
from ..conftest import FakeChannel

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
TEST_DEVICE_UID = "abc123"
TEST_LOCAL_KEY = "local_key"
TEST_SECURITY_DATA = SecurityData(endpoint="test_endpoint", nonce=b"test_nonce_16byte")
TEST_HOST = mock_data.TEST_LOCAL_API_HOST


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


@pytest.fixture(name="mock_create_map_response_decoder")
def setup_mock_map_decoder() -> Iterator[Mock]:
    """Mock the map response decoder to control its behavior in tests."""
    with patch("roborock.devices.v1_channel.create_map_response_decoder") as mock_create_decoder:
        yield mock_create_decoder


@pytest.fixture(name="cache")
def cache_fixtures() -> InMemoryCache:
    """Mock cache for testing."""
    return InMemoryCache()


@pytest.fixture(name="device_cache")
def device_cache_fixtures() -> DeviceCache:
    """Mock device cache for testing."""
    return DeviceCache(TEST_DEVICE_UID, InMemoryCache())


@pytest.fixture(name="v1_channel")
def setup_v1_channel(
    mock_mqtt_channel: Mock,
    mock_local_session: Mock,
    mock_create_map_response_decoder: Mock,
    device_cache: DeviceCache,
) -> V1Channel:
    """Fixture to set up the V1 channel for tests."""
    return V1Channel(
        device_uid=TEST_DEVICE_UID,
        security_data=TEST_SECURITY_DATA,
        mqtt_channel=mock_mqtt_channel,
        local_session=mock_local_session,
        device_cache=device_cache,
    )


@pytest.fixture(name="rpc_channel")
def setup_rpc_channel(v1_channel: V1Channel) -> V1RpcChannel:
    """Fixture to set up the RPC channel for tests.

    We expect tests to use this to send commands via the V1Channel since we
    want to exercise the behavior that the V1RpcChannel is long lived and
    respects the current state of the underlying channels.
    """
    return v1_channel.rpc_channel


@pytest.fixture(name="mqtt_rpc_channel")
def setup_mqtt_rpc_channel(v1_channel: V1Channel) -> V1RpcChannel:
    """Fixture to set up the MQTT RPC channel for tests."""
    return v1_channel.mqtt_rpc_channel


@pytest.fixture(name="map_rpc_channel")
def setup_map_rpc_channel(v1_channel: V1Channel) -> V1RpcChannel:
    """Fixture to set up the Map RPC channel for tests."""
    return v1_channel.map_rpc_channel


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
    mock_mqtt_channel.close()

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
    assert v1_channel.is_mqtt_connected
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


async def test_v1_channel_send_command_local_preferred(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
    rpc_channel: V1RpcChannel,
) -> None:
    """Test command sending prefers local connection when available."""
    # Establish connections
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    await v1_channel.subscribe(Mock())

    # Send command
    mock_local_channel.response_queue.append(TEST_RESPONSE)
    result = await rpc_channel.send_command(
        RoborockCommand.GET_STATUS,
        response_type=S5MaxStatus,
    )

    # Verify local response was parsed
    assert result.state == RoborockStateCode.cleaning


async def test_v1_channel_send_command_local_fails(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
    rpc_channel: V1RpcChannel,
) -> None:
    """Test case where sending with local connection fails, falling back to MQTT."""

    # Establish connections
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    await v1_channel.subscribe(Mock())

    # Local command fails
    mock_local_channel.publish = Mock()
    mock_local_channel.publish.side_effect = RoborockException("Local failed")

    # MQTT command succeeds
    mock_mqtt_channel.response_queue.append(TEST_RESPONSE)

    # Send command
    result = await rpc_channel.send_command(
        RoborockCommand.GET_STATUS,
        response_type=S5MaxStatus,
    )

    # Verify result
    assert result.state == RoborockStateCode.cleaning

    # Verify local was attempted
    mock_local_channel.publish.assert_called_once()

    # Verify MQTT was used
    assert mock_mqtt_channel.published_messages
    # The last message should be the command we sent
    assert mock_mqtt_channel.published_messages[-1].protocol == RoborockMessageProtocol.RPC_REQUEST


@pytest.mark.parametrize(
    ("local_channel_side_effect", "local_channel_responses", "mock_mqtt_channel_responses"),
    [
        (RoborockException("Local failed"), [], [TEST_RESPONSE]),
        (None, [], [TEST_RESPONSE]),
        (None, [RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=b"invalid")], [TEST_RESPONSE]),
    ],
    ids=[
        "local-fails-mqtt-succeeds",
        "local-no-response-mqtt-succeeds",
        "local-invalid-response-mqtt-succeeds",
    ],
)
async def test_v1_channel_send_pick_first_available(
    v1_channel: V1Channel,
    rpc_channel: V1RpcChannel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
    local_channel_side_effect: Exception | None,
    local_channel_responses: list[RoborockMessage],
    mock_mqtt_channel_responses: list[RoborockMessage],
) -> None:
    """Test command sending works with MQTT only."""
    # Setup: only MQTT connection
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    mock_local_channel.connect.side_effect = local_channel_side_effect

    await v1_channel.subscribe(Mock())

    # Send command
    mock_mqtt_channel.response_queue.extend(mock_mqtt_channel_responses)
    mock_local_channel.response_queue.extend(local_channel_responses)
    result = await rpc_channel.send_command(
        RoborockCommand.GET_STATUS,
        response_type=S5MaxStatus,
    )

    # Verify only MQTT was used
    assert result.state == RoborockStateCode.cleaning


async def test_v1_channel_send_decoded_command_with_params(
    v1_channel: V1Channel,
    rpc_channel: V1RpcChannel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test command sending with parameters."""

    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    await v1_channel.subscribe(Mock())

    # Send command with params
    mock_local_channel.response_queue.append(TEST_RESPONSE)
    test_params = {"volume": 80}
    await rpc_channel.send_command(
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
    device_cache_data = DeviceCacheData()
    device_cache_data.network_info = TEST_NETWORKING_INFO

    mock_device_cache = AsyncMock()
    mock_device_cache.get.return_value = device_cache_data
    mock_device_cache.set = AsyncMock()

    # Create V1Channel with the mock cache
    v1_channel = V1Channel(
        device_uid=TEST_DEVICE_UID,
        security_data=TEST_SECURITY_DATA,
        mqtt_channel=mock_mqtt_channel,
        local_session=mock_local_session,
        device_cache=mock_device_cache,
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
    mock_device_cache.get.assert_called_once()
    mock_device_cache.set.assert_not_called()


# V1Channel edge cases tests


async def test_v1_channel_local_connect_network_info_failure(
    v1_channel: V1Channel,
    mock_mqtt_channel: Mock,
) -> None:
    """Test local connection when network info retrieval fails."""
    mock_mqtt_channel.publish_side_effect = RoborockException("Network info failed")

    with pytest.raises(RoborockException):
        await v1_channel._local_connect()


async def test_v1_channel_local_connect_network_info_failure_fallback_to_cache(
    mock_mqtt_channel: FakeChannel,
    mock_local_session: Mock,
    v1_channel: V1Channel,
    device_cache: DeviceCache,
) -> None:
    """Test local connection falls back to cache when network info retrieval fails."""
    # Create a cache with pre-populated network info
    await device_cache.set(DeviceCacheData(network_info=TEST_NETWORKING_INFO))

    # Setup: MQTT fails to publish
    mock_mqtt_channel.publish_side_effect = RoborockException("Network info failed")

    # Attempt local connect, forcing a refresh (prefer_cache=False)
    # This should try MQTT, fail, and then fall back to cache
    await v1_channel._local_connect(prefer_cache=False)

    # Verify local connection was established
    assert v1_channel.is_local_connected

    # Verify MQTT was attempted (published message)
    assert mock_mqtt_channel.published_messages

    # Verify local session was created with the correct IP from cache
    mock_local_session.assert_called_once_with(TEST_HOST)


async def test_v1_channel_command_encoding_validation(
    v1_channel: V1Channel,
    mqtt_rpc_channel: V1RpcChannel,
    rpc_channel: V1RpcChannel,
    mock_mqtt_channel: Mock,
    mock_local_channel: Mock,
) -> None:
    """Test that command encoding works for different protocols."""
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    await v1_channel.subscribe(Mock())

    # Send mqtt command and capture the request
    mock_mqtt_channel.response_queue.append(TEST_RESPONSE)
    await mqtt_rpc_channel.send_command(RoborockCommand.CHANGE_SOUND_VOLUME, params={"volume": 50})
    assert mock_mqtt_channel.published_messages
    mqtt_message = mock_mqtt_channel.published_messages[0]

    # Send local command and capture the request
    mock_local_channel.response_queue.append(TEST_RESPONSE_2)
    await rpc_channel.send_command(RoborockCommand.CHANGE_SOUND_VOLUME, params={"volume": 50})
    assert mock_local_channel.published_messages
    local_message = mock_local_channel.published_messages[0]

    # Verify both are RoborockMessage instances
    assert isinstance(mqtt_message, RoborockMessage)
    assert isinstance(local_message, RoborockMessage)

    # But they should have different protocols
    assert mqtt_message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert local_message.protocol == RoborockMessageProtocol.GENERAL_REQUEST


async def test_v1_channel_send_map_command(
    v1_channel: V1Channel,
    map_rpc_channel: V1RpcChannel,
    mock_mqtt_channel: Mock,
    mock_create_map_response_decoder: Mock,
) -> None:
    """Test that the map channel can correctly decode a map response."""
    # Establish connections
    mock_mqtt_channel.response_queue.append(TEST_NETWORK_INFO_RESPONSE)
    await v1_channel.subscribe(Mock())

    # Prepare a mock map response
    decompressed_map_data = b"this is the decompressed map data"
    request_id = 12346  # from the mock_request_id fixture

    # Mock the decoder to return a known response
    map_response = MapResponse(request_id=request_id, data=decompressed_map_data)
    mock_create_map_response_decoder.return_value.return_value = map_response

    # The actual message content doesn't matter as much since the decoder is mocked
    map_response_message = RoborockMessage(
        protocol=RoborockMessageProtocol.MAP_RESPONSE,
        payload=b"dummy_payload",
    )
    mock_mqtt_channel.response_queue.append(map_response_message)

    # Send the command and get the result
    result = await map_rpc_channel.send_command(RoborockCommand.GET_MAP_V1)

    # Verify the result is the data from our mocked decoder
    assert result == decompressed_map_data
