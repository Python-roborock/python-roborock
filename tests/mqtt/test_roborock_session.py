"""Tests for the MQTT session module."""

import asyncio
import datetime
from collections.abc import AsyncGenerator, Callable, Generator
from queue import Queue
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import aiomqtt
import paho.mqtt.client as mqtt
import pytest

from roborock.mqtt.roborock_session import RoborockMqttSession, create_mqtt_session
from roborock.mqtt.session import MqttParams, MqttSessionException
from tests import mqtt_packet
from tests.conftest import FakeSocketHandler

# We mock out the connection so these params are not used/verified
FAKE_PARAMS = MqttParams(
    host="localhost",
    port=1883,
    tls=False,
    username="username",
    password="password",
    timeout=10.0,
)


@pytest.fixture(autouse=True)
def mqtt_server_fixture(mock_create_connection: None, mock_select: None) -> None:
    """Fixture to prepare a fake MQTT server."""


@pytest.fixture(autouse=True)
async def mock_client_fixture() -> AsyncGenerator[None, None]:
    """Fixture to patch the MQTT underlying sync client.

    The tests use fake sockets, so this ensures that the async mqtt client does not
    attempt to listen on them directly. We instead just poll the socket for
    data ourselves.
    """

    event_loop = asyncio.get_running_loop()

    orig_class = mqtt.Client

    async def poll_sockets(client: mqtt.Client) -> None:
        """Poll the mqtt client sockets in a loop to pick up new data."""
        while True:
            event_loop.call_soon_threadsafe(client.loop_read)
            event_loop.call_soon_threadsafe(client.loop_write)
            await asyncio.sleep(0.1)

    task: asyncio.Task[None] | None = None

    def new_client(*args: Any, **kwargs: Any) -> mqtt.Client:
        """Create a new mqtt client and start the socket polling task."""
        nonlocal task
        client = orig_class(*args, **kwargs)
        task = event_loop.create_task(poll_sockets(client))
        return client

    with (
        patch("aiomqtt.client.Client._on_socket_open"),
        patch("aiomqtt.client.Client._on_socket_close"),
        patch("aiomqtt.client.Client._on_socket_register_write"),
        patch("aiomqtt.client.Client._on_socket_unregister_write"),
        patch("aiomqtt.client.mqtt.Client", side_effect=new_client),
    ):
        yield
        if task:
            task.cancel()


@pytest.fixture(autouse=True)
def fast_backoff_fixture() -> Generator[None, None, None]:
    """Fixture to make backoff intervals fast."""
    with patch("roborock.mqtt.roborock_session.MIN_BACKOFF_INTERVAL", datetime.timedelta(seconds=0.01)):
        yield


@pytest.fixture
def mock_mqtt_client() -> Generator[AsyncMock, None, None]:
    """Fixture to create a mock MQTT client with patched aiomqtt.Client."""
    mock_client = AsyncMock()
    mock_client.messages = FakeAsyncIterator()

    mock_aenter = AsyncMock()
    mock_aenter.return_value = mock_client

    mock_shim = Mock()
    mock_shim.return_value.__aenter__ = mock_aenter
    mock_shim.return_value.__aexit__ = AsyncMock()

    with patch("roborock.mqtt.roborock_session.aiomqtt.Client", mock_shim):
        yield mock_client


@pytest.fixture
def push_response(response_queue: Queue, fake_socket_handler: FakeSocketHandler) -> Callable[[bytes], None]:
    """Fixtures to push messages."""

    def push(message: bytes) -> None:
        response_queue.put(message)
        fake_socket_handler.push_response()

    return push


class Subscriber:
    """Mock subscriber class.

    This will capture messages published on the session so the tests can verify
    they were received.
    """

    def __init__(self) -> None:
        """Initialize the subscriber."""
        self.messages: list[bytes] = []
        self.event: asyncio.Event = asyncio.Event()

    def append(self, message: bytes) -> None:
        """Append a message to the subscriber."""
        self.messages.append(message)
        self.event.set()

    async def wait(self) -> None:
        """Wait for a message to be received."""
        await self.event.wait()
        self.event.clear()


async def test_session(push_response: Callable[[bytes], None]) -> None:
    """Test the MQTT session."""

    push_response(mqtt_packet.gen_connack(rc=0, flags=2))
    session = await create_mqtt_session(FAKE_PARAMS)
    assert session.connected

    push_response(mqtt_packet.gen_suback(mid=1))
    subscriber1 = Subscriber()
    unsub1 = await session.subscribe("topic-1", subscriber1.append)

    push_response(mqtt_packet.gen_suback(mid=2))
    subscriber2 = Subscriber()
    await session.subscribe("topic-2", subscriber2.append)

    push_response(mqtt_packet.gen_publish("topic-1", mid=3, payload=b"12345"))
    await subscriber1.wait()
    assert subscriber1.messages == [b"12345"]
    assert not subscriber2.messages

    push_response(mqtt_packet.gen_publish("topic-2", mid=4, payload=b"67890"))
    await subscriber2.wait()
    assert subscriber2.messages == [b"67890"]

    push_response(mqtt_packet.gen_publish("topic-1", mid=5, payload=b"ABC"))
    await subscriber1.wait()
    assert subscriber1.messages == [b"12345", b"ABC"]
    assert subscriber2.messages == [b"67890"]

    # Messages are no longer received after unsubscribing
    unsub1()
    push_response(mqtt_packet.gen_publish("topic-1", payload=b"ignored"))
    assert subscriber1.messages == [b"12345", b"ABC"]

    assert session.connected
    await session.close()
    assert not session.connected


async def test_session_no_subscribers(push_response: Callable[[bytes], None]) -> None:
    """Test the MQTT session."""

    push_response(mqtt_packet.gen_connack(rc=0, flags=2))
    push_response(mqtt_packet.gen_publish("topic-1", mid=3, payload=b"12345"))
    push_response(mqtt_packet.gen_publish("topic-2", mid=4, payload=b"67890"))
    session = await create_mqtt_session(FAKE_PARAMS)
    assert session.connected

    await session.close()
    assert not session.connected


async def test_publish_command(push_response: Callable[[bytes], None]) -> None:
    """Test publishing during an MQTT session."""

    push_response(mqtt_packet.gen_connack(rc=0, flags=2))
    session = await create_mqtt_session(FAKE_PARAMS)

    push_response(mqtt_packet.gen_publish("topic-1", mid=3, payload=b"12345"))
    await session.publish("topic-1", message=b"payload")

    assert session.connected
    await session.close()
    assert not session.connected


class FakeAsyncIterator:
    """Fake async iterator that waits for messages to arrive, but they never do.

    This is used for testing exceptions in other client functions.
    """

    def __aiter__(self):
        return self

    async def __anext__(self) -> None:
        """Iterator that does not generate any messages."""
        while True:
            await asyncio.sleep(1)


async def test_publish_failure(mock_mqtt_client: AsyncMock) -> None:
    """Test an MQTT error is received when publishing a message."""

    session = await create_mqtt_session(FAKE_PARAMS)
    assert session.connected

    mock_mqtt_client.publish.side_effect = aiomqtt.MqttError

    with pytest.raises(MqttSessionException, match="Error publishing message"):
        await session.publish("topic-1", message=b"payload")

    await session.close()


async def test_subscribe_failure(mock_mqtt_client: AsyncMock) -> None:
    """Test an MQTT error while subscribing."""

    session = await create_mqtt_session(FAKE_PARAMS)
    assert session.connected

    mock_mqtt_client.subscribe.side_effect = aiomqtt.MqttError

    subscriber1 = Subscriber()
    with pytest.raises(MqttSessionException, match="Error subscribing to topic"):
        await session.subscribe("topic-1", subscriber1.append)

    assert not subscriber1.messages
    await session.close()


async def test_restart(push_response: Callable[[bytes], None]) -> None:
    """Test restarting the MQTT session."""

    push_response(mqtt_packet.gen_connack(rc=0, flags=2))
    session = await create_mqtt_session(FAKE_PARAMS)
    assert session.connected

    # Subscribe to a topic
    push_response(mqtt_packet.gen_suback(mid=1))
    subscriber = Subscriber()
    await session.subscribe("topic-1", subscriber.append)

    # Verify we can receive messages
    push_response(mqtt_packet.gen_publish("topic-1", mid=2, payload=b"12345"))
    await subscriber.wait()
    assert subscriber.messages == [b"12345"]

    # Restart the session.
    await session.restart()
    # This is a hack where we grab on to the client and wait for it to be
    # closed properly and restarted.
    while session._client:  # type: ignore[attr-defined]
        await asyncio.sleep(0.01)

    # We need to queue up a new connack for the reconnection
    push_response(mqtt_packet.gen_connack(rc=0, flags=2))

    # And a suback for the resubscription. Since we created a new client,
    # the message ID resets to 1.
    push_response(mqtt_packet.gen_suback(mid=1))

    push_response(mqtt_packet.gen_publish("topic-1", mid=4, payload=b"67890"))
    await subscriber.wait()
    assert subscriber.messages == [b"12345", b"67890"]

    await session.close()


async def test_idle_timeout_resubscribe(mock_mqtt_client: AsyncMock) -> None:
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
    mock_mqtt_client.unsubscribe.assert_not_called()

    await session.close()


async def test_idle_timeout_unsubscribe(mock_mqtt_client: AsyncMock) -> None:
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
    mock_mqtt_client.unsubscribe.assert_called_once_with(topic)

    await session.close()


async def test_idle_timeout_multiple_callbacks(mock_mqtt_client: AsyncMock) -> None:
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
    mock_mqtt_client.unsubscribe.assert_not_called()

    # Unsubscribe second callback (NOW timer should start)
    unsub2()

    # Wait for idle timeout plus a small buffer
    await asyncio.sleep(0.1)

    # Now unsubscribe should have been called
    mock_mqtt_client.unsubscribe.assert_called_once_with(topic)

    await session.close()
