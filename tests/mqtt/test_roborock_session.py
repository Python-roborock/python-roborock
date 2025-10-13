"""Tests for the MQTT session module."""

import asyncio
from collections.abc import AsyncGenerator, Callable
from queue import Queue
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import aiomqtt
import paho.mqtt.client as mqtt
import pytest

from roborock.mqtt.roborock_session import create_mqtt_session
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


async def test_publish_failure() -> None:
    """Test an MQTT error is received when publishing a message."""

    mock_client = AsyncMock()
    mock_client.messages = FakeAsyncIterator()

    mock_aenter = AsyncMock()
    mock_aenter.return_value = mock_client

    with patch("roborock.mqtt.roborock_session.aiomqtt.Client.__aenter__", mock_aenter):
        session = await create_mqtt_session(FAKE_PARAMS)
        assert session.connected

        mock_client.publish.side_effect = aiomqtt.MqttError

        with pytest.raises(MqttSessionException, match="Error publishing message"):
            await session.publish("topic-1", message=b"payload")


async def test_subscribe_failure() -> None:
    """Test an MQTT error while subscribing."""

    mock_client = AsyncMock()
    mock_client.messages = FakeAsyncIterator()

    mock_aenter = AsyncMock()
    mock_aenter.return_value = mock_client

    mock_shim = Mock()
    mock_shim.return_value.__aenter__ = mock_aenter
    mock_shim.return_value.__aexit__ = AsyncMock()

    with patch("roborock.mqtt.roborock_session.aiomqtt.Client", mock_shim):
        session = await create_mqtt_session(FAKE_PARAMS)
        assert session.connected

        mock_client.subscribe.side_effect = aiomqtt.MqttError

        subscriber1 = Subscriber()
        with pytest.raises(MqttSessionException, match="Error subscribing to topic"):
            await session.subscribe("topic-1", subscriber1.append)

        assert not subscriber1.messages
        await session.close()
