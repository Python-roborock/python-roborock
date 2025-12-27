"""Tests for the MqttChannel class."""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator, Callable
from unittest.mock import AsyncMock, Mock

import pytest

from roborock.data import HomeData, UserData
from roborock.devices.mqtt_channel import MqttChannel
from roborock.mqtt.session import MqttParams
from roborock.protocol import create_mqtt_decoder, create_mqtt_encoder
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests import mock_data

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
def setup_mqtt_session() -> Mock:
    """Fixture to set up the MQTT session for the tests."""
    return AsyncMock()


@pytest.fixture(name="mqtt_channel", autouse=True)
def setup_mqtt_channel(mqtt_session: Mock) -> MqttChannel:
    """Fixture to set up the MQTT channel for the tests."""
    return MqttChannel(
        mqtt_session, duid="abc123", local_key=TEST_LOCAL_KEY, rriot=USER_DATA.rriot, mqtt_params=TEST_MQTT_PARAMS
    )


@pytest.fixture(name="mqtt_subscribers", autouse=True)
async def setup_subscribe_callback(mqtt_session: Mock) -> AsyncGenerator[list[Callable[[bytes], None]], None]:
    """Fixture to record messages received by the subscriber."""
    subscriber_callbacks = []

    def mock_subscribe(_: str, callback: Callable[[bytes], None]) -> Callable[[], None]:
        subscriber_callbacks.append(callback)
        return lambda: subscriber_callbacks.remove(callback)

    mqtt_session.subscribe.side_effect = mock_subscribe
    yield subscriber_callbacks
    assert not subscriber_callbacks, "Not all subscribers were unsubscribed"


@pytest.fixture(name="mqtt_message_handler")
async def setup_message_handler(mqtt_subscribers: list[Callable[[bytes], None]]) -> Callable[[bytes], None]:
    """Fixture to allow simulating incoming MQTT messages."""

    def invoke_all_callbacks(message: bytes) -> None:
        for callback in mqtt_subscribers:
            callback(message)

    return invoke_all_callbacks


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


async def test_publish_success(
    mqtt_session: Mock,
    mqtt_channel: MqttChannel,
    mqtt_message_handler: Callable[[bytes], None],
) -> None:
    """Test successful RPC command sending and response handling."""
    # Send a test request. We use a task so we can simulate receiving the response
    # while the command is still being processed.
    await mqtt_channel.publish(TEST_REQUEST)
    await asyncio.sleep(0.01)  # yield

    # Simulate receiving the response message via MQTT
    mqtt_message_handler(ENCODER(TEST_RESPONSE))
    await asyncio.sleep(0.01)  # yield

    # Verify the command was sent
    assert mqtt_session.publish.called
    assert mqtt_session.publish.call_args[0][0] == "rr/m/i/user123/username/abc123"
    raw_sent_msg = mqtt_session.publish.call_args[0][1]  # == b"encoded_message"
    decoded_message = next(iter(DECODER(raw_sent_msg)))
    assert decoded_message == TEST_REQUEST
    assert decoded_message.protocol == RoborockMessageProtocol.RPC_REQUEST


@pytest.mark.parametrize(("connected"), [(True), (False)])
async def test_connection_status(
    mqtt_session: Mock,
    mqtt_channel: MqttChannel,
    connected: bool,
) -> None:
    """Test successful RPC command sending and response handling."""
    mqtt_session.connected = connected
    assert mqtt_channel.is_connected is connected
    assert mqtt_channel.is_local_connected is False


async def test_message_decode_error(
    mqtt_channel: MqttChannel,
    mqtt_message_handler: Callable[[bytes], None],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test an error during message decoding."""
    callback = Mock()
    unsub = await mqtt_channel.subscribe(callback)

    with caplog.at_level(logging.WARNING):
        mqtt_message_handler(b"invalid_payload")
        await asyncio.sleep(0.01)  # yield

    assert callback.call_count == 0
    unsub()


async def test_concurrent_subscribers(mqtt_session: Mock, mqtt_channel: MqttChannel) -> None:
    """Test multiple concurrent subscribers receive all messages."""
    # Set up multiple subscribers
    subscriber1_messages: list[RoborockMessage] = []
    subscriber2_messages: list[RoborockMessage] = []
    subscriber3_messages: list[RoborockMessage] = []

    unsub1 = await mqtt_channel.subscribe(subscriber1_messages.append)
    unsub2 = await mqtt_channel.subscribe(subscriber2_messages.append)
    unsub3 = await mqtt_channel.subscribe(subscriber3_messages.append)

    # Verify that each subscription creates a separate call to the MQTT session
    assert mqtt_session.subscribe.call_count == 3

    # All subscriptions should be to the same topic
    for call in mqtt_session.subscribe.call_args_list:
        assert call[0][0] == "rr/m/o/user123/username/abc123"

    # Get the message handlers for each subscriber
    handler1 = mqtt_session.subscribe.call_args_list[0][0][1]
    handler2 = mqtt_session.subscribe.call_args_list[1][0][1]
    handler3 = mqtt_session.subscribe.call_args_list[2][0][1]

    # Simulate receiving messages - each handler should decode the message independently
    handler1(ENCODER(TEST_REQUEST))
    handler2(ENCODER(TEST_REQUEST))
    handler3(ENCODER(TEST_REQUEST))
    await asyncio.sleep(0.01)  # yield

    # All subscribers should receive the message
    assert len(subscriber1_messages) == 1
    assert len(subscriber2_messages) == 1
    assert len(subscriber3_messages) == 1
    assert subscriber1_messages[0] == TEST_REQUEST
    assert subscriber2_messages[0] == TEST_REQUEST
    assert subscriber3_messages[0] == TEST_REQUEST

    # Send another message to all handlers
    handler1(ENCODER(TEST_RESPONSE))
    handler2(ENCODER(TEST_RESPONSE))
    handler3(ENCODER(TEST_RESPONSE))
    await asyncio.sleep(0.01)  # yield

    # All subscribers should have received both messages
    assert len(subscriber1_messages) == 2
    assert len(subscriber2_messages) == 2
    assert len(subscriber3_messages) == 2
    assert subscriber1_messages == [TEST_REQUEST, TEST_RESPONSE]
    assert subscriber2_messages == [TEST_REQUEST, TEST_RESPONSE]
    assert subscriber3_messages == [TEST_REQUEST, TEST_RESPONSE]

    # Test unsubscribing one subscriber
    unsub1()

    # Send another message only to remaining handlers
    handler2(ENCODER(TEST_REQUEST2))
    handler3(ENCODER(TEST_REQUEST2))
    await asyncio.sleep(0.01)  # yield

    # First subscriber should not have received the new message
    assert len(subscriber1_messages) == 2
    assert len(subscriber2_messages) == 3
    assert len(subscriber3_messages) == 3
    assert subscriber2_messages[2] == TEST_REQUEST2
    assert subscriber3_messages[2] == TEST_REQUEST2

    # Unsubscribe remaining subscribers
    unsub2()
    unsub3()


async def test_concurrent_subscribers_with_callback_exception(
    mqtt_session: Mock, mqtt_channel: MqttChannel, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that exception in one subscriber callback doesn't affect others."""
    caplog.set_level(logging.ERROR)

    def failing_callback(message: RoborockMessage) -> None:
        raise ValueError("Callback error")

    subscriber2_messages: list[RoborockMessage] = []

    unsub1 = await mqtt_channel.subscribe(failing_callback)
    unsub2 = await mqtt_channel.subscribe(subscriber2_messages.append)

    # Get the message handlers
    handler1 = mqtt_session.subscribe.call_args_list[0][0][1]
    handler2 = mqtt_session.subscribe.call_args_list[1][0][1]

    # Simulate receiving a message - first handler will raise exception
    handler1(ENCODER(TEST_REQUEST))
    handler2(ENCODER(TEST_REQUEST))
    await asyncio.sleep(0.01)  # yield

    # Exception should be logged but other subscribers should still work
    assert len(subscriber2_messages) == 1
    assert subscriber2_messages[0] == TEST_REQUEST

    # Check that exception was logged
    error_records = [record for record in caplog.records if record.levelname == "ERROR"]
    assert len(error_records) == 1
    assert "Uncaught error in callback 'failing_callback'" in error_records[0].message

    # Unsubscribe all remaining subscribers
    unsub1()
    unsub2()
