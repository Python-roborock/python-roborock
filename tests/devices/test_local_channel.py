"""Tests for the LocalChannel class."""

import asyncio
import json
from collections.abc import Generator
from unittest.mock import AsyncMock, Mock, patch

import pytest

from roborock.devices.local_channel import LocalChannel
from roborock.exceptions import RoborockConnectionException
from roborock.protocol import create_local_decoder, create_local_encoder
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

TEST_HOST = "192.168.1.100"
TEST_LOCAL_KEY = "local_key"
TEST_PORT = 58867

TEST_REQUEST = RoborockMessage(
    protocol=RoborockMessageProtocol.RPC_REQUEST,
    payload=json.dumps({"dps": {"101": json.dumps({"id": 12345, "method": "get_status"})}}).encode(),
)
TEST_RESPONSE = RoborockMessage(
    protocol=RoborockMessageProtocol.RPC_RESPONSE,
    payload=json.dumps({"dps": {"102": json.dumps({"id": 12345, "result": {"state": "cleaning"}})}}).encode(),
)
TEST_REQUEST2 = RoborockMessage(
    protocol=RoborockMessageProtocol.RPC_REQUEST,
    payload=json.dumps({"dps": {"101": json.dumps({"id": 54321, "method": "get_status"})}}).encode(),
)
TEST_RESPONSE2 = RoborockMessage(
    protocol=RoborockMessageProtocol.RPC_RESPONSE,
    payload=json.dumps({"dps": {"102": json.dumps({"id": 54321, "result": {"state": "cleaning"}})}}).encode(),
)
ENCODER = create_local_encoder(TEST_LOCAL_KEY)
DECODER = create_local_decoder(TEST_LOCAL_KEY)


@pytest.fixture(name="mock_transport")
def setup_mock_transport() -> Mock:
    """Mock transport for testing."""
    transport = Mock()
    transport.write = Mock()
    transport.close = Mock()
    return transport


@pytest.fixture(name="mock_loop")
def setup_mock_loop(mock_transport: Mock) -> Generator[Mock, None, None]:
    """Mock event loop for testing."""
    loop = Mock()
    loop.create_connection = AsyncMock(return_value=(mock_transport, Mock()))

    with patch("asyncio.get_running_loop", return_value=loop):
        yield loop


@pytest.fixture(name="local_channel")
def setup_local_channel() -> LocalChannel:
    """Fixture to set up the local channel for tests."""
    return LocalChannel(host=TEST_HOST, local_key=TEST_LOCAL_KEY)


@pytest.fixture(name="received_messages")
async def setup_subscribe_callback(local_channel: LocalChannel) -> list[RoborockMessage]:
    """Fixture to record messages received by the subscriber."""
    messages: list[RoborockMessage] = []
    await local_channel.subscribe(messages.append)
    return messages


async def test_successful_connection(local_channel: LocalChannel, mock_loop: Mock, mock_transport: Mock) -> None:
    """Test successful connection to device."""
    await local_channel.connect()

    mock_loop.create_connection.assert_called_once()
    call_args = mock_loop.create_connection.call_args
    assert call_args[0][1] == TEST_HOST
    assert call_args[0][2] == TEST_PORT
    assert local_channel._is_connected is True


async def test_connection_failure(local_channel: LocalChannel, mock_loop: Mock) -> None:
    """Test connection failure handling."""
    mock_loop.create_connection.side_effect = OSError("Connection failed")

    with pytest.raises(RoborockConnectionException, match="Failed to connect to 192.168.1.100:58867"):
        await local_channel.connect()

    assert local_channel._is_connected is False


async def test_already_connected_warning(
    local_channel: LocalChannel, mock_loop: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test warning when trying to connect when already connected."""
    await local_channel.connect()
    await local_channel.connect()  # Second connection attempt

    assert "Already connected" in caplog.text
    assert mock_loop.create_connection.call_count == 1


async def test_close_connection(local_channel: LocalChannel, mock_loop: Mock, mock_transport: Mock) -> None:
    """Test closing the connection."""
    await local_channel.connect()
    local_channel.close()

    mock_transport.close.assert_called_once()
    assert local_channel._is_connected is False


async def test_close_without_connection(local_channel: LocalChannel) -> None:
    """Test closing when not connected."""
    local_channel.close()
    assert local_channel._is_connected is False


async def test_publish_not_connected(local_channel: LocalChannel) -> None:
    """Test sending command when not connected raises exception."""
    with pytest.raises(RoborockConnectionException, match="Not connected to device"):
        await local_channel.publish(TEST_REQUEST)


async def test_successful_command_response(local_channel: LocalChannel, mock_loop: Mock, mock_transport: Mock) -> None:
    """Test successful command sending and response handling."""
    await local_channel.connect()

    # Send command in background task
    await local_channel.publish(TEST_REQUEST)
    await asyncio.sleep(0.01)  # yield

    # Simulate receiving response via the protocol callback
    local_channel._data_received(ENCODER(TEST_RESPONSE))
    await asyncio.sleep(0.01)  # yield

    # Verify command was sent
    mock_transport.write.assert_called_once()
    sent_data = mock_transport.write.call_args[0][0]
    decoded_sent = next(iter(DECODER(sent_data)))
    assert decoded_sent == TEST_REQUEST


async def test_message_decode_error(local_channel: LocalChannel, caplog: pytest.LogCaptureFixture) -> None:
    """Test handling of message decode errors."""
    local_channel._data_received(b"invalid_payload")
    await asyncio.sleep(0.01)  # yield

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert "Failed to decode local message" in caplog.records[0].message


async def test_subscribe_callback(
    local_channel: LocalChannel, received_messages: list[RoborockMessage], mock_loop: Mock
) -> None:
    """Test that subscribe callback receives all messages."""
    await local_channel.connect()

    # Send some messages without an RPC
    local_channel._data_received(ENCODER(TEST_RESPONSE))
    local_channel._data_received(ENCODER(TEST_RESPONSE2))
    await asyncio.sleep(0.01)  # yield

    assert received_messages == [TEST_RESPONSE, TEST_RESPONSE2]


async def test_subscribe_callback_exception_handling(
    local_channel: LocalChannel, mock_loop: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that exceptions in subscriber callbacks are handled gracefully."""

    def failing_callback(message: RoborockMessage) -> None:
        raise ValueError("Test exception")

    await local_channel.subscribe(failing_callback)
    await local_channel.connect()

    # Send message that will cause callback to fail
    local_channel._data_received(ENCODER(TEST_RESPONSE))
    await asyncio.sleep(0.01)  # yield

    # Should log the exception but not crash
    assert any("Uncaught error in message handler callback" in record.message for record in caplog.records)


async def test_unsubscribe(local_channel: LocalChannel, mock_loop: Mock) -> None:
    """Test unsubscribing from messages."""
    messages: list[RoborockMessage] = []
    unsubscribe = await local_channel.subscribe(messages.append)
    await local_channel.connect()

    # Send message while subscribed
    local_channel._data_received(ENCODER(TEST_RESPONSE))
    await asyncio.sleep(0.01)  # yield
    assert len(messages) == 1

    # Unsubscribe and send another message
    unsubscribe()
    local_channel._data_received(ENCODER(TEST_RESPONSE2))
    await asyncio.sleep(0.01)  # yield

    # Should still have only one message
    assert len(messages) == 1


async def test_connection_lost_callback(
    local_channel: LocalChannel, mock_loop: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test connection lost callback handling."""
    await local_channel.connect()

    # Simulate connection loss
    test_exception = OSError("Connection lost")
    local_channel._connection_lost(test_exception)

    assert local_channel._is_connected is False
    assert local_channel._transport is None
    assert "Connection lost to 192.168.1.100" in caplog.text


async def test_connection_lost_without_exception(
    local_channel: LocalChannel, mock_loop: Mock, caplog: pytest.LogCaptureFixture
) -> None:
    """Test connection lost callback without exception."""
    await local_channel.connect()

    # Simulate connection loss without exception
    local_channel._connection_lost(None)

    assert local_channel._is_connected is False
    assert local_channel._transport is None
    assert "Connection lost to 192.168.1.100" in caplog.text
