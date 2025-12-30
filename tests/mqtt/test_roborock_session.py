"""Tests for the MQTT session module."""

import asyncio
import copy
import datetime
from collections.abc import Callable, Generator
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import aiomqtt
import pytest

from roborock.diagnostics import Diagnostics
from roborock.mqtt.roborock_session import RoborockMqttSession, create_mqtt_session
from roborock.mqtt.session import MqttSessionException, MqttSessionUnauthorized
from tests import mqtt_packet
from tests.fixtures.mqtt import FAKE_PARAMS, Subscriber

pytest_plugins = [
    "tests.fixtures.logging_fixtures",
    "tests.fixtures.pahomqtt_fixtures",
    "tests.fixtures.aiomqtt_fixtures",
]


@pytest.fixture(autouse=True)
def mqtt_server_fixture(
    mock_paho_mqtt_create_connection: None,
    mock_paho_mqtt_select: None,
) -> None:
    """Fixture to prepare a fake MQTT server."""


@pytest.fixture(autouse=True)
def auto_mock_aiomqtt_client(
    mock_aiomqtt_client: None,
) -> None:
    """Automatically use the mock mqtt client fixture."""


@pytest.fixture(autouse=True)
def auto_fast_backoff(fast_backoff_fixture: None) -> None:
    """Automatically use the fast backoff fixture."""


class FakeAsyncIterator:
    """Fake async iterator that waits for messages to arrive, but they never do.

    This is used for testing exceptions in other client functions.
    """

    def __init__(self) -> None:
        self.loop = True

    def __aiter__(self):
        return self

    async def __anext__(self) -> None:
        """Iterator that does not generate any messages."""
        while self.loop:
            await asyncio.sleep(0.01)


@pytest.fixture(name="message_iterator")
def message_iterator_fixture() -> FakeAsyncIterator:
    """Fixture to provide a side effect for creating the MQTT client."""
    return FakeAsyncIterator()


@pytest.fixture(name="mock_client")
def mock_client_fixture(message_iterator: FakeAsyncIterator) -> Generator[AsyncMock, None, None]:
    """A fixture that provides a mocked aiomqtt Client.

    This is lighter weight that `mock_aiomqtt_client` that uses real sockets.
    """
    mock_client = AsyncMock()
    mock_client.messages = message_iterator
    return mock_client


@pytest.fixture(name="create_client_side_effect")
def create_client_side_effect_fixture() -> Exception | None:
    """Fixture to provide a side effect for creating the MQTT client."""
    return None


@pytest.fixture(name="mock_aenter_client")
def mock_aenter_client_fixture(mock_client: AsyncMock, create_client_side_effect: Exception | None) -> AsyncMock:
    """Fixture to provide a side effect for creating the MQTT client."""
    mock_aenter = AsyncMock()
    mock_aenter.return_value = mock_client
    mock_aenter.side_effect = create_client_side_effect
    return mock_aenter


@pytest.fixture(name="mqtt_client_lite")
def mqtt_client_lite_fixture(
    mock_client: AsyncMock,
    mock_aenter_client: AsyncMock,
) -> Generator[AsyncMock, None, None]:
    """Fixture to create a mock MQTT client with patched aiomqtt.Client."""

    mock_shim = Mock()
    mock_shim.return_value.__aenter__ = mock_aenter_client
    mock_shim.return_value.__aexit__ = AsyncMock()

    with patch("roborock.mqtt.roborock_session.aiomqtt.Client", mock_shim):
        yield mock_client


async def test_session(push_mqtt_response: Callable[[bytes], None]) -> None:
    """Test the MQTT session."""

    push_mqtt_response(mqtt_packet.gen_connack(rc=0, flags=2))
    session = await create_mqtt_session(FAKE_PARAMS)
    assert session.connected

    push_mqtt_response(mqtt_packet.gen_suback(mid=1))
    subscriber1 = Subscriber()
    unsub1 = await session.subscribe("topic-1", subscriber1.append)

    push_mqtt_response(mqtt_packet.gen_suback(mid=2))
    subscriber2 = Subscriber()
    await session.subscribe("topic-2", subscriber2.append)

    push_mqtt_response(mqtt_packet.gen_publish("topic-1", mid=3, payload=b"12345"))
    await subscriber1.wait()
    assert subscriber1.messages == [b"12345"]
    assert not subscriber2.messages

    push_mqtt_response(mqtt_packet.gen_publish("topic-2", mid=4, payload=b"67890"))
    await subscriber2.wait()
    assert subscriber2.messages == [b"67890"]

    push_mqtt_response(mqtt_packet.gen_publish("topic-1", mid=5, payload=b"ABC"))
    await subscriber1.wait()
    assert subscriber1.messages == [b"12345", b"ABC"]
    assert subscriber2.messages == [b"67890"]

    # Messages are no longer received after unsubscribing
    unsub1()
    push_mqtt_response(mqtt_packet.gen_publish("topic-1", payload=b"ignored"))
    assert subscriber1.messages == [b"12345", b"ABC"]

    assert session.connected
    await session.close()
    assert not session.connected


async def test_session_no_subscribers(push_mqtt_response: Callable[[bytes], None]) -> None:
    """Test the MQTT session."""

    push_mqtt_response(mqtt_packet.gen_connack(rc=0, flags=2))
    session = await create_mqtt_session(FAKE_PARAMS)
    assert session.connected

    await session.close()
    assert not session.connected


async def test_publish_command(push_mqtt_response: Callable[[bytes], None]) -> None:
    """Test publishing during an MQTT session."""

    push_mqtt_response(mqtt_packet.gen_connack(rc=0, flags=2))
    session = await create_mqtt_session(FAKE_PARAMS)

    push_mqtt_response(mqtt_packet.gen_publish("topic-1", mid=3, payload=b"12345"))
    await session.publish("topic-1", message=b"payload")

    assert session.connected
    await session.close()
    assert not session.connected


async def test_publish_failure(mqtt_client_lite: AsyncMock) -> None:
    """Test an MQTT error is received when publishing a message."""

    session = await create_mqtt_session(FAKE_PARAMS)
    assert session.connected

    mqtt_client_lite.publish.side_effect = aiomqtt.MqttError

    with pytest.raises(MqttSessionException, match="Error publishing message"):
        await session.publish("topic-1", message=b"payload")

    await session.close()


async def test_subscribe_failure(mqtt_client_lite: AsyncMock) -> None:
    """Test an MQTT error while subscribing."""

    session = await create_mqtt_session(FAKE_PARAMS)
    assert session.connected

    mqtt_client_lite.subscribe.side_effect = aiomqtt.MqttError

    subscriber1 = Subscriber()
    with pytest.raises(MqttSessionException, match="Error subscribing to topic"):
        await session.subscribe("topic-1", subscriber1.append)

    assert not subscriber1.messages
    await session.close()


async def test_restart(push_mqtt_response: Callable[[bytes], None]) -> None:
    """Test restarting the MQTT session."""

    push_mqtt_response(mqtt_packet.gen_connack(rc=0, flags=2))
    session = await create_mqtt_session(FAKE_PARAMS)
    assert session.connected

    # Subscribe to a topic
    push_mqtt_response(mqtt_packet.gen_suback(mid=1))
    subscriber = Subscriber()
    await session.subscribe("topic-1", subscriber.append)

    # Verify we can receive messages
    push_mqtt_response(mqtt_packet.gen_publish("topic-1", mid=2, payload=b"12345"))
    await subscriber.wait()
    assert subscriber.messages == [b"12345"]

    # Restart the session.
    await session.restart()
    # This is a hack where we grab on to the client and wait for it to be
    # closed properly and restarted.
    while session._client:  # type: ignore[attr-defined]
        await asyncio.sleep(0.01)

    # We need to queue up a new connack for the reconnection
    push_mqtt_response(mqtt_packet.gen_connack(rc=0, flags=2))

    # And a suback for the resubscription. Since we created a new client,
    # the message ID resets to 1.
    push_mqtt_response(mqtt_packet.gen_suback(mid=1))

    push_mqtt_response(mqtt_packet.gen_publish("topic-1", mid=4, payload=b"67890"))
    await subscriber.wait()
    assert subscriber.messages == [b"12345", b"67890"]

    await session.close()


async def test_idle_timeout_resubscribe(mqtt_client_lite: AsyncMock) -> None:
    """Test that resubscribing before idle timeout cancels the unsubscribe."""

    # Create session with idle timeout
    session = RoborockMqttSession(FAKE_PARAMS, topic_idle_timeout=datetime.timedelta(seconds=5))
    await session.start()
    assert session.connected

    topic = "test/topic"
    subscriber1 = Subscriber()
    unsub1 = await session.subscribe(topic, subscriber1.append)

    # Unsubscribe to start idle timer
    unsub1()

    # Resubscribe before idle timeout expires (should cancel timer)
    subscriber2 = Subscriber()
    await session.subscribe(topic, subscriber2.append)

    # Give a brief moment for any async operations to complete
    await asyncio.sleep(0.01)

    # unsubscribe should NOT have been called because we resubscribed
    mqtt_client_lite.unsubscribe.assert_not_called()

    await session.close()


async def test_idle_timeout_unsubscribe(mqtt_client_lite: AsyncMock) -> None:
    """Test that unsubscribe happens after idle timeout expires."""

    # Create session with very short idle timeout for fast test
    session = RoborockMqttSession(FAKE_PARAMS, topic_idle_timeout=datetime.timedelta(milliseconds=50))
    await session.start()
    assert session.connected

    topic = "test/topic"
    subscriber = Subscriber()
    unsub = await session.subscribe(topic, subscriber.append)

    # Unsubscribe to start idle timer
    unsub()

    # Wait for idle timeout plus a small buffer
    await asyncio.sleep(0.1)

    # unsubscribe should have been called after idle timeout
    mqtt_client_lite.unsubscribe.assert_called_once_with(topic)

    await session.close()


async def test_idle_timeout_multiple_callbacks(mqtt_client_lite: AsyncMock) -> None:
    """Test that unsubscribe is delayed when multiple subscribers exist."""

    # Create session with very short idle timeout for fast test
    session = RoborockMqttSession(FAKE_PARAMS, topic_idle_timeout=datetime.timedelta(milliseconds=50))
    await session.start()
    assert session.connected

    topic = "test/topic"
    subscriber1 = Subscriber()
    subscriber2 = Subscriber()

    unsub1 = await session.subscribe(topic, subscriber1.append)
    unsub2 = await session.subscribe(topic, subscriber2.append)

    # Unsubscribe first callback (should NOT start timer, subscriber2 still active)
    unsub1()

    # Brief wait to ensure no timer fires
    await asyncio.sleep(0.1)

    # unsubscribe should NOT have been called because subscriber2 is still active
    mqtt_client_lite.unsubscribe.assert_not_called()

    # Unsubscribe second callback (NOW timer should start)
    unsub2()

    # Wait for idle timeout plus a small buffer
    await asyncio.sleep(0.1)

    # Now unsubscribe should have been called
    mqtt_client_lite.unsubscribe.assert_called_once_with(topic)

    await session.close()


async def test_subscription_reuse(mqtt_client_lite: AsyncMock) -> None:
    """Test that subscriptions are reused and not duplicated."""
    session = RoborockMqttSession(FAKE_PARAMS)
    await session.start()
    assert session.connected

    # 1. First subscription
    cb1 = Mock()
    unsub1 = await session.subscribe("topic1", cb1)

    # Verify subscribe called
    mqtt_client_lite.subscribe.assert_called_with("topic1")
    mqtt_client_lite.subscribe.reset_mock()

    # 2. Second subscription (same topic)
    cb2 = Mock()
    unsub2 = await session.subscribe("topic1", cb2)

    # Verify subscribe NOT called
    mqtt_client_lite.subscribe.assert_not_called()

    # 3. Unsubscribe one
    unsub1()
    # Verify unsubscribe NOT called (still have cb2)
    mqtt_client_lite.unsubscribe.assert_not_called()

    # 4. Unsubscribe second (starts idle timer)
    unsub2()
    # Verify unsubscribe NOT called yet (idle)
    mqtt_client_lite.unsubscribe.assert_not_called()

    # 5. Resubscribe during idle
    cb3 = Mock()
    _ = await session.subscribe("topic1", cb3)

    # Verify subscribe NOT called (reused)
    mqtt_client_lite.subscribe.assert_not_called()

    await session.close()


@pytest.mark.parametrize(
    ("side_effect", "expected_exception", "match"),
    [
        (
            aiomqtt.MqttError("Connection failed"),
            MqttSessionException,
            "Error starting MQTT session",
        ),
        (
            aiomqtt.MqttCodeError(rc=135),
            MqttSessionUnauthorized,
            "Authorization error starting MQTT session",
        ),
        (
            aiomqtt.MqttCodeError(rc=128),
            MqttSessionException,
            "Error starting MQTT session",
        ),
        (
            ValueError("Unexpected"),
            MqttSessionException,
            "Unexpected error starting session",
        ),
    ],
)
async def test_connect_failure(
    side_effect: Exception,
    expected_exception: type[Exception],
    match: str,
) -> None:
    """Test connection failure with different exceptions."""
    mock_aenter = AsyncMock()
    mock_aenter.side_effect = side_effect

    with patch("roborock.mqtt.roborock_session.aiomqtt.Client.__aenter__", mock_aenter):
        with pytest.raises(expected_exception, match=match):
            await create_mqtt_session(FAKE_PARAMS)


async def test_diagnostics_data(push_mqtt_response: Callable[[bytes], None]) -> None:
    """Test the MQTT session."""

    diagnostics = Diagnostics()

    params = copy.deepcopy(FAKE_PARAMS)
    params.diagnostics = diagnostics

    push_mqtt_response(mqtt_packet.gen_connack(rc=0, flags=2))
    session = await create_mqtt_session(params)
    assert session.connected

    # Verify diagnostics after connection
    data = diagnostics.as_dict()
    assert data.get("start_attempt") == 1
    assert data.get("start_loop") == 1
    assert data.get("start_success") == 1
    assert data.get("subscribe_count") is None
    assert data.get("dispatch_message_count") is None
    assert data.get("close") is None

    push_mqtt_response(mqtt_packet.gen_suback(mid=1))
    subscriber1 = Subscriber()
    unsub1 = await session.subscribe("topic-1", subscriber1.append)

    push_mqtt_response(mqtt_packet.gen_suback(mid=2))
    subscriber2 = Subscriber()
    await session.subscribe("topic-2", subscriber2.append)

    push_mqtt_response(mqtt_packet.gen_publish("topic-1", mid=3, payload=b"12345"))
    await subscriber1.wait()
    assert subscriber1.messages == [b"12345"]
    assert not subscriber2.messages

    push_mqtt_response(mqtt_packet.gen_publish("topic-2", mid=4, payload=b"67890"))
    await subscriber2.wait()
    assert subscriber2.messages == [b"67890"]

    push_mqtt_response(mqtt_packet.gen_publish("topic-1", mid=5, payload=b"ABC"))
    await subscriber1.wait()
    assert subscriber1.messages == [b"12345", b"ABC"]
    assert subscriber2.messages == [b"67890"]

    # Verify diagnostics after subscribing and receiving messages
    data = diagnostics.as_dict()
    assert data.get("start_attempt") == 1
    assert data.get("start_loop") == 1
    assert data.get("subscribe_count") == 2
    assert data.get("dispatch_message_count") == 3
    assert data.get("close") is None

    # Messages are no longer received after unsubscribing
    unsub1()
    push_mqtt_response(mqtt_packet.gen_publish("topic-1", payload=b"ignored"))
    assert subscriber1.messages == [b"12345", b"ABC"]

    assert session.connected
    await session.close()
    assert not session.connected

    # Verify diagnostics after closing session
    data = diagnostics.as_dict()
    assert data.get("start_attempt") == 1
    assert data.get("start_loop") == 1
    assert data.get("subscribe_count") == 2
    assert data.get("dispatch_message_count") == 3
    assert data.get("close") == 1


@pytest.mark.parametrize(
    ("create_client_side_effect"),
    [
        # Unauthorized
        aiomqtt.MqttCodeError(rc=135),
    ],
)
async def test_session_unauthorized_hook(mqtt_client_lite: AsyncMock) -> None:
    """Test the MQTT session."""

    unauthorized = asyncio.Event()

    params = copy.deepcopy(FAKE_PARAMS)
    params.unauthorized_hook = unauthorized.set

    with pytest.raises(MqttSessionUnauthorized):
        await create_mqtt_session(params)

    assert unauthorized.is_set()


async def test_session_unauthorized_after_start(
    mock_aenter_client: AsyncMock,
    message_iterator: FakeAsyncIterator,
    mqtt_client_lite: AsyncMock,
    push_mqtt_response: Callable[[bytes], None],
) -> None:
    """Test the MQTT session."""

    # Configure a hook that is notified of unauthorized errors
    unauthorized = asyncio.Event()
    params = copy.deepcopy(FAKE_PARAMS)
    params.unauthorized_hook = unauthorized.set

    # The client will succeed on first connection attempt, then fail with
    # unauthorized messages on all future attempts.
    request_count = 0

    def succeed_then_fail_unauthorized() -> Any:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return mqtt_client_lite
        raise aiomqtt.MqttCodeError(rc=135)

    mock_aenter_client.side_effect = succeed_then_fail_unauthorized
    # Don't produce messages, just exit and restart to reconnect
    message_iterator.loop = False

    session = await create_mqtt_session(params)
    assert session.connected

    try:
        async with asyncio.timeout(10):
            assert await unauthorized.wait()
    finally:
        await session.close()
