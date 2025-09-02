"""Module for communicating with Roborock devices over a local network."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from roborock.callbacks import CallbackList, decoder_callback
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
        self._subscribers: CallbackList[RoborockMessage] = CallbackList(_LOGGER)
        self._is_connected = False

        self._decoder: Decoder = create_local_decoder(local_key)
        self._encoder: Encoder = create_local_encoder(local_key)
        # Callback to decode messages and dispatch to subscribers
        self._data_received: Callable[[bytes], None] = decoder_callback(self._decoder, self._subscribers, _LOGGER)

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

    def _connection_lost(self, exc: Exception | None) -> None:
        """Handle connection loss."""
        _LOGGER.warning("Connection lost to %s", self._host, exc_info=exc)
        self._transport = None
        self._is_connected = False

    async def subscribe(self, callback: Callable[[RoborockMessage], None]) -> Callable[[], None]:
        """Subscribe to all messages from the device."""
        return self._subscribers.add_callback(callback)

    async def publish(self, message: RoborockMessage) -> None:
        """Send a command message.

        The caller is responsible for associating the message with its response.
        """
        if not self._transport or not self._is_connected:
            raise RoborockConnectionException("Not connected to device")

        try:
            encoded_msg = self._encoder(message)
        except Exception as err:
            _LOGGER.exception("Error encoding MQTT message: %s", err)
            raise RoborockException(f"Failed to encode MQTT message: {err}") from err
        try:
            self._transport.write(encoded_msg)
        except Exception as err:
            logging.exception("Uncaught error sending command")
            raise RoborockException(f"Failed to send message: {message}") from err


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
