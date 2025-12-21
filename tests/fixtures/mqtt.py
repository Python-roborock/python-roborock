"""Common code for MQTT tests."""

import asyncio
import io
import logging
from collections.abc import Callable
from queue import Queue

from roborock.mqtt.session import MqttParams
from roborock.roborock_message import RoborockMessage

from .logging import CapturedRequestLog

_LOGGER = logging.getLogger(__name__)

# Used by fixtures to handle incoming requests and prepare responses
MqttRequestHandler = Callable[[bytes], bytes | None]


class FakeMqttSocketHandler:
    """Fake socket used by the test to simulate a connection to the broker.

    The socket handler is used to intercept the socket send and recv calls and
    populate the response buffer with data to be sent back to the client. The
    handle request callback handles the incoming requests and prepares the responses.
    """

    def __init__(
        self, handle_request: MqttRequestHandler, response_queue: Queue[bytes], log: CapturedRequestLog
    ) -> None:
        self.response_buf = io.BytesIO()
        self.handle_request = handle_request
        self.response_queue = response_queue
        self.log = log

    def pending(self) -> int:
        """Return the number of bytes in the response buffer."""
        return len(self.response_buf.getvalue())

    def handle_socket_recv(self, read_size: int) -> bytes:
        """Intercept a client recv() and populate the buffer."""
        if self.pending() == 0:
            raise BlockingIOError("No response queued")

        self.response_buf.seek(0)
        data = self.response_buf.read(read_size)
        _LOGGER.debug("Response: 0x%s", data.hex())
        # Consume the rest of the data in the buffer
        remaining_data = self.response_buf.read()
        self.response_buf = io.BytesIO(remaining_data)
        return data

    def handle_socket_send(self, client_request: bytes) -> int:
        """Receive an incoming request from the client."""
        _LOGGER.debug("Request: 0x%s", client_request.hex())
        self.log.add_log_entry("[mqtt >]", client_request)
        if (response := self.handle_request(client_request)) is not None:
            # Enqueue a response to be sent back to the client in the buffer.
            # The buffer will be emptied when the client calls recv() on the socket
            _LOGGER.debug("Queued: 0x%s", response.hex())
            self.log.add_log_entry("[mqtt <]", response)
            self.response_buf.write(response)
        return len(client_request)

    def push_response(self) -> None:
        """Push a response to the client."""
        if not self.response_queue.empty():
            response = self.response_queue.get()
            # Enqueue a response to be sent back to the client in the buffer.
            # The buffer will be emptied when the client calls recv() on the socket
            _LOGGER.debug("Queued: 0x%s", response.hex())
            self.log.add_log_entry("[mqtt <]", response)
            self.response_buf.write(response)


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
        self.messages: list[RoborockMessage | bytes] = []
        self._event = asyncio.Event()

    def append(self, message: RoborockMessage | bytes) -> None:
        self.messages.append(message)
        self._event.set()

    async def wait(self) -> None:
        await asyncio.wait_for(self._event.wait(), timeout=1.0)
        self._event.clear()
