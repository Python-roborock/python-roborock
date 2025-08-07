"""Tests for the MqttChannel class."""

import asyncio
import json
import logging
from collections.abc import Callable, Generator
from unittest.mock import AsyncMock, Mock, patch

import pytest

from roborock.containers import HomeData, UserData
from roborock.devices.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.mqtt.session import MqttParams
from roborock.protocol import create_mqtt_decoder, create_mqtt_encoder
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

from .. import mock_data

USER_DATA = UserData.from_dict(mock_data.USER_DATA)
TEST_MQTT_PARAMS = MqttParams(
    host="localhost",
    port=1883,
    tls=False,
    username="username",
    password="password",
    timeout=10.0,
)
TEST_LOCAL_KEY = "local_key"

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
ENCODER = create_mqtt_encoder(TEST_LOCAL_KEY)
DECODER = create_mqtt_decoder(TEST_LOCAL_KEY)


@pytest.fixture(name="mqtt_session", autouse=True)
def setup_mqtt_session() -> Generator[Mock, None, None]:
    """Fixture to set up the MQTT session for the tests."""
    mock_session = AsyncMock()
    with patch("roborock.devices.device_manager.create_mqtt_session", return_value=mock_session):
        yield mock_session


@pytest.fixture(name="mqtt_channel", autouse=True)
def setup_mqtt_channel(mqtt_session: Mock) -> MqttChannel:
    """Fixture to set up the MQTT channel for the tests."""
    return MqttChannel(
        mqtt_session, duid="abc123", local_key=TEST_LOCAL_KEY, rriot=USER_DATA.rriot, mqtt_params=TEST_MQTT_PARAMS
    )


@pytest.fixture(name="received_messages", autouse=True)
async def setup_subscribe_callback(mqtt_channel: MqttChannel) -> list[RoborockMessage]:
    """Fixture to record messages received by the subscriber."""
    messages: list[RoborockMessage] = []
    await mqtt_channel.subscribe(messages.append)
    return messages


@pytest.fixture(name="mqtt_message_handler")
async def setup_message_handler(mqtt_session: Mock, mqtt_channel: MqttChannel) -> Callable[[bytes], None]:
    """Fixture to allow simulating incoming MQTT messages."""
    # Subscribe to set up message handling. We grab the message handler callback
    # and use it to simulate receiving a response.
    assert mqtt_session.subscribe
    subscribe_call_args = mqtt_session.subscribe.call_args
    message_handler = subscribe_call_args[0][1]
    return message_handler


@pytest.fixture
def warning_caplog(
    caplog: pytest.LogCaptureFixture,
) -> pytest.LogCaptureFixture:
    """Fixture to capture warning messages."""
    caplog.set_level(logging.WARNING)
    return caplog


async def home_home_data_no_devices() -> HomeData:
    """Mock home data API that returns no devices."""
    return HomeData(
        id=1,
        name="Test Home",
        devices=[],
        products=[],
    )


async def mock_home_data() -> HomeData:
    """Mock home data API that returns devices."""
    return HomeData.from_dict(mock_data.HOME_DATA_RAW)


async def test_mqtt_channel(mqtt_session: Mock, mqtt_channel: MqttChannel) -> None:
    """Test MQTT channel setup."""

    unsub = Mock()
    mqtt_session.subscribe.return_value = unsub

    callback = Mock()
    result = await mqtt_channel.subscribe(callback)

    assert mqtt_session.subscribe.called
    assert mqtt_session.subscribe.call_args[0][0] == "rr/m/o/user123/username/abc123"

    unsub.assert_not_called()
    result()
    unsub.assert_called_once()


async def test_send_message_success(
    mqtt_session: Mock,
    mqtt_channel: MqttChannel,
    mqtt_message_handler: Callable[[bytes], None],
) -> None:
    """Test successful RPC command sending and response handling."""
    # Send a test request. We use a task so we can simulate receiving the response
    # while the command is still being processed.
    command_task = asyncio.create_task(mqtt_channel.send_message(TEST_REQUEST))
    await asyncio.sleep(0.01)  # yield

    # Simulate receiving the response message via MQTT
    mqtt_message_handler(ENCODER(TEST_RESPONSE))
    await asyncio.sleep(0.01)  # yield

    # Get the result
    result = await command_task

    # Verify the command was sent
    assert mqtt_session.publish.called
    assert mqtt_session.publish.call_args[0][0] == "rr/m/i/user123/username/abc123"
    raw_sent_msg = mqtt_session.publish.call_args[0][1]  # == b"encoded_message"
    decoded_message = next(iter(DECODER(raw_sent_msg)))
    assert decoded_message == TEST_REQUEST
    assert decoded_message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert decoded_message.get_request_id() == 12345

    # Verify we got the response message back
    assert result == TEST_RESPONSE


async def test_send_message_without_request_id(
    mqtt_session: Mock,
    mqtt_channel: MqttChannel,
    mqtt_message_handler: Callable[[bytes], None],
) -> None:
    """Test sending command without request ID raises exception."""
    # Create a message without request ID
    test_message = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        payload=b"no_request_id",
    )

    with pytest.raises(RoborockException, match="Message must have a request_id"):
        await mqtt_channel.send_message(test_message)


async def test_concurrent_commands(
    mqtt_session: Mock,
    mqtt_channel: MqttChannel,
    mqtt_message_handler: Callable[[bytes], None],
    warning_caplog: pytest.LogCaptureFixture,
) -> None:
    """Test handling multiple concurrent RPC commands."""

    # Create multiple test messages with different request IDs
    # Start both commands concurrently
    task1 = asyncio.create_task(mqtt_channel.send_message(TEST_REQUEST, timeout=5.0))
    task2 = asyncio.create_task(mqtt_channel.send_message(TEST_REQUEST2, timeout=5.0))
    await asyncio.sleep(0.01)  # yield

    # Create responses for both
    mqtt_message_handler(ENCODER(TEST_RESPONSE))
    await asyncio.sleep(0.01)  # yield

    mqtt_message_handler(ENCODER(TEST_RESPONSE2))
    await asyncio.sleep(0.01)  # yield

    # Both should complete successfully
    result1 = await task1
    result2 = await task2

    assert result1 == TEST_RESPONSE
    assert result2 == TEST_RESPONSE2

    assert not warning_caplog.records


async def test_concurrent_commands_same_request_id(
    mqtt_session: Mock,
    mqtt_channel: MqttChannel,
    mqtt_message_handler: Callable[[bytes], None],
) -> None:
    """Test that we are not allowed to send two commands with the same request id."""

    # Create multiple test messages with different request IDs
    # Start both commands concurrently
    task1 = asyncio.create_task(mqtt_channel.send_message(TEST_REQUEST, timeout=5.0))
    task2 = asyncio.create_task(mqtt_channel.send_message(TEST_REQUEST, timeout=5.0))
    await asyncio.sleep(0.01)  # yield

    # Create response
    mqtt_message_handler(ENCODER(TEST_RESPONSE))
    await asyncio.sleep(0.01)  # yield

    # Both should complete successfully
    result1 = await task1
    assert result1 == TEST_RESPONSE

    with pytest.raises(RoborockException, match="Request ID 12345 already pending, cannot send command"):
        await task2


async def test_handle_completed_future(
    mqtt_session: Mock,
    mqtt_channel: MqttChannel,
    mqtt_message_handler: Callable[[bytes], None],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test handling response for an already completed future."""
    # Send request
    task = asyncio.create_task(mqtt_channel.send_message(TEST_REQUEST, timeout=5.0))
    await asyncio.sleep(0.01)  # yield

    # Send the response twice
    mqtt_message_handler(ENCODER(TEST_RESPONSE))
    await asyncio.sleep(0.01)  # yield
    mqtt_message_handler(ENCODER(TEST_RESPONSE))
    await asyncio.sleep(0.01)  # yield

    # Task completes and second message is not associated with a waiting handler
    result = await task
    assert result == TEST_RESPONSE


async def test_subscribe_callback_with_rpc_response(
    mqtt_session: Mock,
    mqtt_channel: MqttChannel,
    received_messages: list[RoborockMessage],
    mqtt_message_handler: Callable[[bytes], None],
) -> None:
    """Test that subscribe callback is called independent of RPC handling."""
    # Send request
    task = asyncio.create_task(mqtt_channel.send_message(TEST_REQUEST, timeout=5.0))
    await asyncio.sleep(0.01)  # yield

    assert not received_messages

    # Send the response for this command and an unrelated command
    mqtt_message_handler(ENCODER(TEST_RESPONSE))
    await asyncio.sleep(0.01)  # yield
    mqtt_message_handler(ENCODER(TEST_RESPONSE2))
    await asyncio.sleep(0.01)  # yield

    # Task completes
    result = await task
    assert result == TEST_RESPONSE

    # The subscribe callback should have been called with the same response
    assert received_messages == [TEST_RESPONSE, TEST_RESPONSE2]


async def test_message_decode_error(
    mqtt_message_handler: Callable[[bytes], None],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test an error during message decoding."""
    mqtt_message_handler(b"invalid_payload")
    await asyncio.sleep(0.01)  # yield

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"
    assert "Failed to decode MQTT message" in caplog.records[0].message
