"""Module for communicating with Roborock devices over a local network."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from roborock.callbacks import CallbackList, decoder_callback
from roborock.exceptions import RoborockConnectionException, RoborockException
from roborock.protocol import create_local_decoder, create_local_encoder
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

from ..protocols.v1_protocol import LocalProtocolVersion
from ..util import get_next_int
from .channel import Channel

_LOGGER = logging.getLogger(__name__)
_PORT = 58867
_TIMEOUT = 10.0


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

    def __init__(self, host: str, local_key: str, local_protocol_version: LocalProtocolVersion | None = None):
        self._host = host
        self._transport: asyncio.Transport | None = None
        self._protocol: _LocalProtocol | None = None
        self._subscribers: CallbackList[RoborockMessage] = CallbackList(_LOGGER)
        self._is_connected = False
        self._local_key = local_key
        self._local_protocol_version = local_protocol_version
        self._connect_nonce = get_next_int(10000, 32767)
        self._ack_nonce: int | None = None
        self._update_encoder_decoder()

    def _update_encoder_decoder(self):
        self._encoder = create_local_encoder(
            local_key=self._local_key, connect_nonce=self._connect_nonce, ack_nonce=self._ack_nonce
        )
        self._decoder = create_local_decoder(
            local_key=self._local_key, connect_nonce=self._connect_nonce, ack_nonce=self._ack_nonce
        )
        # Callback to decode messages and dispatch to subscribers
        self._data_received: Callable[[bytes], None] = decoder_callback(self._decoder, self._subscribers, _LOGGER)

    async def _do_hello(self, local_protocol_version: LocalProtocolVersion) -> bool:
        """Perform the initial handshaking."""
        _LOGGER.debug(
            "Attempting to use the %s protocol for client %s...",
            local_protocol_version,
            self._host,
        )
        request = RoborockMessage(
            protocol=RoborockMessageProtocol.HELLO_REQUEST,
            version=local_protocol_version.encode(),
            random=self._connect_nonce,
            seq=1,
        )
        try:
            response = await self.send_message(
                roborock_message=request,
                request_id=request.seq,
                response_protocol=RoborockMessageProtocol.HELLO_RESPONSE,
            )
            self._ack_nonce = response.random
            self._local_protocol_version = local_protocol_version
            self._update_encoder_decoder()

            _LOGGER.debug(
                "Client %s speaks the %s protocol.",
                self._host,
                local_protocol_version,
            )
            return True
        except RoborockException as e:
            _LOGGER.debug(
                "Client %s did not respond or does not speak the %s protocol. %s",
                self._host,
                local_protocol_version,
                e,
            )
            return False

    async def hello(self):
        """Send hello to the device to negotiate protocol."""
        if self._local_protocol_version:
            # version is forced - try it first, if it fails, try the opposite
            if not await self._do_hello(self._local_protocol_version):
                if not await self._do_hello(
                    LocalProtocolVersion.V1
                    if self._local_protocol_version is not LocalProtocolVersion.V1
                    else LocalProtocolVersion.L01
                ):
                    raise RoborockException("Failed to connect to device with any known protocol")
        else:
            # try 1.0, then L01
            if not await self._do_hello(LocalProtocolVersion.V1):
                if not await self._do_hello(LocalProtocolVersion.L01):
                    raise RoborockException("Failed to connect to device with any known protocol")

    @property
    def is_connected(self) -> bool:
        """Check if the channel is currently connected."""
        return self._is_connected

    @property
    def is_local_connected(self) -> bool:
        """Check if the channel is currently connected locally."""
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

    async def send_message(
        self,
        roborock_message: RoborockMessage,
        request_id: int,
        response_protocol: int,
    ) -> RoborockMessage:
        """Send a raw message and wait for a raw response."""
        future: asyncio.Future[RoborockMessage] = asyncio.Future()

        def find_response(response_message: RoborockMessage) -> None:
            if response_message.protocol == response_protocol and response_message.seq == request_id:
                future.set_result(response_message)

        unsub = await self.subscribe(find_response)
        try:
            await self.publish(roborock_message)
            return await asyncio.wait_for(future, timeout=_TIMEOUT)
        except TimeoutError as ex:
            future.cancel()
            raise RoborockException(f"Command timed out after {_TIMEOUT}s") from ex
        finally:
            unsub()


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
