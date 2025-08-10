"""Module for communicating with Roborock devices over a local network."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from json import JSONDecodeError

from roborock.exceptions import RoborockConnectionException, RoborockException
from roborock.protocol import Decoder, Encoder, create_local_decoder, create_local_encoder
from roborock.roborock_message import RoborockMessage

from .channel import Channel

_LOGGER = logging.getLogger(__name__)
_PORT = 58867


@dataclass
class _LocalProtocol(asyncio.Protocol):
    """Callbacks for the Roborock local client transport."""

    messages_cb: Callable[[bytes], None]
    connection_lost_cb: Callable[[Exception | None], None]

    def data_received(self, data: bytes) -> None:
        """Called when data is received from the transport."""
        self.messages_cb(data)

    def connection_lost(self, exc: Exception | None) -> None:
        """Called when the transport connection is lost."""
        self.connection_lost_cb(exc)


class LocalChannel(Channel):
    """Simple RPC-style channel for communicating with a device over a local network.

    Handles request/response correlation and timeouts, but leaves message
    format most parsing to higher-level components.
    """

    def __init__(self, host: str, local_key: str):
        self._host = host
        self._transport: asyncio.Transport | None = None
        self._protocol: _LocalProtocol | None = None
        self._subscribers: list[Callable[[RoborockMessage], None]] = []
        self._is_connected = False

        # RPC support
        self._waiting_queue: dict[int, asyncio.Future[RoborockMessage]] = {}
        self._decoder: Decoder = create_local_decoder(local_key)
        self._encoder: Encoder = create_local_encoder(local_key)
        self._queue_lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        """Check if the channel is currently connected."""
        return self._is_connected

    async def connect(self) -> None:
        """Connect to the device."""
        if self._is_connected:
            _LOGGER.warning("Already connected")
            return
        _LOGGER.debug("Connecting to %s:%s", self._host, _PORT)
        loop = asyncio.get_running_loop()
        protocol = _LocalProtocol(self._data_received, self._connection_lost)
        try:
            self._transport, self._protocol = await loop.create_connection(lambda: protocol, self._host, _PORT)
            self._is_connected = True
        except OSError as e:
            raise RoborockConnectionException(f"Failed to connect to {self._host}:{_PORT}") from e

    def close(self) -> None:
        """Disconnect from the device."""
        if self._transport:
            self._transport.close()
        else:
            _LOGGER.warning("Close called but transport is already None")
        self._transport = None
        self._is_connected = False

    def _data_received(self, data: bytes) -> None:
        """Handle incoming data from the transport."""
        if not (messages := self._decoder(data)):
            _LOGGER.warning("Failed to decode local message: %s", data)
            return
        for message in messages:
            _LOGGER.debug("Received message: %s", message)
            asyncio.create_task(self._resolve_future_with_lock(message))
            for callback in self._subscribers:
                try:
                    callback(message)
                except Exception as e:
                    _LOGGER.exception("Uncaught error in message handler callback: %s", e)

    def _connection_lost(self, exc: Exception | None) -> None:
        """Handle connection loss."""
        _LOGGER.warning("Connection lost to %s", self._host, exc_info=exc)
        self._transport = None
        self._is_connected = False

    async def subscribe(self, callback: Callable[[RoborockMessage], None]) -> Callable[[], None]:
        """Subscribe to all messages from the device."""
        self._subscribers.append(callback)

        def unsubscribe() -> None:
            self._subscribers.remove(callback)

        return unsubscribe

    async def _resolve_future_with_lock(self, message: RoborockMessage) -> None:
        """Resolve waiting future with proper locking."""
        if (request_id := message.get_request_id()) is None:
            _LOGGER.debug("Received message with no request_id")
            return
        async with self._queue_lock:
            if (future := self._waiting_queue.pop(request_id, None)) is not None:
                future.set_result(message)
            else:
                _LOGGER.debug("Received message with no waiting handler: request_id=%s", request_id)

    async def send_message(self, message: RoborockMessage, timeout: float = 10.0) -> RoborockMessage:
        """Send a command message and wait for the response message."""
        if not self._transport or not self._is_connected:
            raise RoborockConnectionException("Not connected to device")

        try:
            if (request_id := message.get_request_id()) is None:
                raise RoborockException("Message must have a request_id for RPC calls")
        except (ValueError, JSONDecodeError) as err:
            _LOGGER.exception("Error getting request_id from message: %s", err)
            raise RoborockException(f"Invalid message format, Message must have a request_id: {err}") from err

        future: asyncio.Future[RoborockMessage] = asyncio.Future()
        async with self._queue_lock:
            if request_id in self._waiting_queue:
                raise RoborockException(f"Request ID {request_id} already pending, cannot send command")
            self._waiting_queue[request_id] = future

        try:
            encoded_msg = self._encoder(message)
            self._transport.write(encoded_msg)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError as ex:
            async with self._queue_lock:
                self._waiting_queue.pop(request_id, None)
            raise RoborockException(f"Command timed out after {timeout}s") from ex
        except Exception:
            logging.exception("Uncaught error sending command")
            async with self._queue_lock:
                self._waiting_queue.pop(request_id, None)
            raise


# This module provides a factory function to create LocalChannel instances.
#
# TODO: Make a separate LocalSession and use it to manage retries with the host,
# similar to how MqttSession works. For now this is a simple factory function
# for creating channels.
LocalSession = Callable[[str], LocalChannel]


def create_local_session(local_key: str) -> LocalSession:
    """Creates a local session which can create local channels.

    This plays a role similar to the MqttSession but is really just a factory
    for creating LocalChannel instances with the same local key.
    """

    def create_local_channel(host: str) -> LocalChannel:
        """Create a LocalChannel instance for the given host."""
        return LocalChannel(host, local_key)

    return create_local_channel
