"""Common code for MQTT tests."""

import asyncio
import datetime
from collections.abc import AsyncGenerator, Callable, Generator
from queue import Queue
from typing import Any
from unittest.mock import patch

import paho.mqtt.client as mqtt
import pytest

from roborock.mqtt.session import MqttParams
from tests.conftest import FakeSocketHandler

FAKE_PARAMS = MqttParams(
    host="localhost",
    port=1883,
    tls=False,
    username="username",
    password="password",
    timeout=10.0,
)


class Subscriber:
    """Mock subscriber class.

    We use this to hold on to received messages for verification.
    """

    def __init__(self) -> None:
        self.messages: list[bytes] = []
        self._event = asyncio.Event()

    def append(self, message: bytes) -> None:
        self.messages.append(message)
        self._event.set()

    async def wait(self) -> None:
        await asyncio.wait_for(self._event.wait(), timeout=1.0)
        self._event.clear()


@pytest.fixture
async def mock_mqtt_client_fixture() -> AsyncGenerator[None, None]:
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
            await asyncio.sleep(0.01)

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
def fast_backoff_fixture() -> Generator[None, None, None]:
    """Fixture to speed up backoff."""
    with patch(
        "roborock.mqtt.roborock_session.MIN_BACKOFF_INTERVAL",
        datetime.timedelta(seconds=0.01),
    ):
        yield


@pytest.fixture
def push_response(response_queue: Queue, fake_socket_handler: FakeSocketHandler) -> Callable[[bytes], None]:
    """Fixture to push a response to the client."""

    def _push(data: bytes) -> None:
        response_queue.put(data)
        fake_socket_handler.push_response()

    return _push
