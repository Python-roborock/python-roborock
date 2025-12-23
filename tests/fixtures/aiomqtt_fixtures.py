"""Common code for MQTT tests."""

import asyncio
import datetime
from collections.abc import AsyncGenerator, Callable, Generator
from queue import Queue
from typing import Any
from unittest.mock import patch

import paho.mqtt.client as mqtt
import pytest

from .mqtt import FakeMqttSocketHandler


@pytest.fixture(name="mock_aiomqtt_client")
async def mock_aiomqtt_client_fixture() -> AsyncGenerator[None, None]:
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
def push_mqtt_response(
    mqtt_response_queue: Queue, fake_mqtt_socket_handler: FakeMqttSocketHandler
) -> Callable[[bytes], None]:
    """Fixture to push a response to the client."""

    def _push(data: bytes) -> None:
        mqtt_response_queue.put(data)
        fake_mqtt_socket_handler.push_response()

    return _push
