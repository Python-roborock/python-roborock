"""Common code for MQTT tests."""

import logging
import warnings
from collections.abc import Callable, Generator
from queue import Queue
from typing import Any
from unittest.mock import Mock, patch

import pytest

from .logging import CapturedRequestLog
from .mqtt import FakeMqttSocketHandler

pytest_plugins = [
    "tests.fixtures.logging_fixtures",
]

_LOGGER = logging.getLogger(__name__)

# Used by fixtures to handle incoming requests and prepare responses
MqttRequestHandler = Callable[[bytes], bytes | None]


@pytest.fixture(name="mock_paho_mqtt_create_connection")
def create_connection_fixture(mock_sock: Mock) -> Generator[None, None, None]:
    """Fixture that overrides the MQTT socket creation to wire it up to the mock socket."""
    with patch("paho.mqtt.client.socket.create_connection", return_value=mock_sock):
        yield


@pytest.fixture(name="mock_paho_mqtt_select")
def select_fixture(mock_sock: Mock, fake_mqtt_socket_handler: FakeMqttSocketHandler) -> Generator[None, None, None]:
    """Fixture that overrides the MQTT client select calls to make select work on the mock socket.

    This patch select to activate our mock socket when ready with data. Internal mqtt sockets are
    always ready since they are used internally to wake the select loop. Ours is ready if there
    is data in the buffer.
    """

    def is_ready(sock: Any) -> bool:
        return sock is not mock_sock or (fake_mqtt_socket_handler.pending() > 0)

    def handle_select(rlist: list, wlist: list, *args: Any) -> list:
        return [list(filter(is_ready, rlist)), list(filter(is_ready, wlist))]

    with patch("paho.mqtt.client.select.select", side_effect=handle_select):
        yield


@pytest.fixture(name="fake_mqtt_socket_handler")
def fake_mqtt_socket_handler_fixture(
    mqtt_request_handler: MqttRequestHandler, mqtt_response_queue: Queue[bytes], log: CapturedRequestLog
) -> Generator[FakeMqttSocketHandler, None, None]:
    """Fixture that creates a fake MQTT broker."""
    socket_handler = FakeMqttSocketHandler(mqtt_request_handler, mqtt_response_queue, log)
    yield socket_handler
    if len(socket_handler.response_buf.getvalue()) > 0:
        warnings.warn("Some enqueued MQTT responses were not consumed during the test")


@pytest.fixture(name="mock_sock")
def mock_sock_fixture(fake_mqtt_socket_handler: FakeMqttSocketHandler) -> Mock:
    """Fixture that creates a mock socket connection and wires it to the handler."""
    mock_sock = Mock()
    mock_sock.recv = fake_mqtt_socket_handler.handle_socket_recv
    mock_sock.send = fake_mqtt_socket_handler.handle_socket_send
    mock_sock.pending = fake_mqtt_socket_handler.pending
    return mock_sock


@pytest.fixture(name="mqtt_received_requests")
def received_requests_fixture() -> Queue[bytes]:
    """Fixture that provides access to the received requests."""
    return Queue()


@pytest.fixture(name="mqtt_response_queue")
def response_queue_fixture() -> Generator[Queue[bytes], None, None]:
    """Fixture that provides a queue for enqueueing responses to be sent to the client under test."""
    response_queue: Queue[bytes] = Queue()
    yield response_queue
    if not response_queue.empty():
        warnings.warn("Some enqueued MQTT responses were not consumed during the test")


@pytest.fixture(name="mqtt_request_handler")
def mqtt_request_handler_fixture(
    mqtt_received_requests: Queue[bytes], mqtt_response_queue: Queue[bytes]
) -> MqttRequestHandler:
    """Fixture records incoming requests and replies with responses from the queue."""

    def handle_request(client_request: bytes) -> bytes | None:
        """Handle an incoming request from the client."""
        mqtt_received_requests.put(client_request)

        # Insert a prepared response into the response buffer
        if not mqtt_response_queue.empty():
            return mqtt_response_queue.get()
        return None

    return handle_request
