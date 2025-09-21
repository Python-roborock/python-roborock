import asyncio
import logging
from asyncio import Lock, TimerHandle, Transport, get_running_loop
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

import async_timeout

from .. import CommandVacuumError, DeviceData, RoborockCommand
from ..api import RoborockClient
from ..exceptions import RoborockConnectionException, RoborockException, VacuumError
from ..protocol import create_local_decoder, create_local_encoder
from ..protocols.v1_protocol import RequestMessage
from ..roborock_message import RoborockMessage, RoborockMessageProtocol
from ..util import RoborockLoggerAdapter, get_next_int
from .roborock_client_v1 import CLOUD_REQUIRED, RoborockClientV1

_LOGGER = logging.getLogger(__name__)


class LocalProtocolVersion(StrEnum):
    """Supported local protocol versions. Different from vacuum protocol versions."""

    L01 = "L01"
    V1 = "1.0"


@dataclass
class _LocalProtocol(asyncio.Protocol):
    """Callbacks for the Roborock local client transport."""

    messages_cb: Callable[[bytes], None]
    connection_lost_cb: Callable[[Exception | None], None]

    def data_received(self, bytes) -> None:
        """Called when data is received from the transport."""
        self.messages_cb(bytes)

    def connection_lost(self, exc: Exception | None) -> None:
        """Called when the transport connection is lost."""
        self.connection_lost_cb(exc)


class RoborockLocalClientV1(RoborockClientV1, RoborockClient):
    """Roborock local client for v1 devices."""

    def __init__(
        self,
        device_data: DeviceData,
        queue_timeout: int = 4,
        local_protocol_version: LocalProtocolVersion | None = None,
    ):
        """Initialize the Roborock local client."""
        if device_data.host is None:
            raise RoborockException("Host is required")
        self.host = device_data.host
        self._batch_structs: list[RoborockMessage] = []
        self._executing = False
        self.transport: Transport | None = None
        self._mutex = Lock()
        self.keep_alive_task: TimerHandle | None = None
        RoborockClientV1.__init__(self, device_data, security_data=None)
        RoborockClient.__init__(self, device_data)
        self._local_protocol = _LocalProtocol(self._data_received, self._connection_lost)
        self._local_protocol_version = local_protocol_version
        self._connect_nonce = get_next_int(10000, 32767)
        self._ack_nonce: int | None = None
        self._set_encoder_decoder()
        self.queue_timeout = queue_timeout
        self._logger = RoborockLoggerAdapter(device_data.device.name, _LOGGER)

    @property
    def local_protocol_version(self) -> LocalProtocolVersion:
        return LocalProtocolVersion.V1 if self._local_protocol_version is None else self._local_protocol_version

    def _data_received(self, message):
        """Called when data is received from the transport."""
        parsed_msg = self._decoder(message)
        self.on_message_received(parsed_msg)

    def _connection_lost(self, exc: Exception | None):
        """Called when the transport connection is lost."""
        self._sync_disconnect()
        self.on_connection_lost(exc)

    def is_connected(self):
        return self.transport and self.transport.is_reading()

    async def keep_alive_func(self, _=None):
        try:
            await self.ping()
        except RoborockException:
            pass
        loop = asyncio.get_running_loop()
        self.keep_alive_task = loop.call_later(10, lambda: asyncio.create_task(self.keep_alive_func()))

    async def async_connect(self) -> None:
        should_ping = False
        async with self._mutex:
            try:
                if not self.is_connected():
                    self._sync_disconnect()
                    async with async_timeout.timeout(self.queue_timeout):
                        self._logger.debug(f"Connecting to {self.host}")
                        loop = get_running_loop()
                        self.transport, _ = await loop.create_connection(  # type: ignore
                            lambda: self._local_protocol, self.host, 58867
                        )
                        self._logger.info(f"Connected to {self.host}")
                        should_ping = True
            except BaseException as e:
                raise RoborockConnectionException(f"Failed connecting to {self.host}") from e
        if should_ping:
            await self.hello()
            await self.keep_alive_func()

    def _sync_disconnect(self) -> None:
        loop = asyncio.get_running_loop()
        if self.transport and loop.is_running():
            self._logger.debug(f"Disconnecting from {self.host}")
            self.transport.close()
        if self.keep_alive_task:
            self.keep_alive_task.cancel()

    async def async_disconnect(self) -> None:
        async with self._mutex:
            self._sync_disconnect()

    def _set_encoder_decoder(self):
        """Updates the encoder decoder. These are updated with nonces after the first hello.
        Only L01 uses the nonces."""
        self._encoder = create_local_encoder(self.device_info.device.local_key, self._connect_nonce, self._ack_nonce)
        self._decoder = create_local_decoder(self.device_info.device.local_key, self._connect_nonce, self._ack_nonce)

    async def _do_hello(self, local_protocol_version: LocalProtocolVersion) -> bool:
        """Perform the initial handshaking."""
        self._logger.debug(
            "Attempting to use the %s protocol for client %s...",
            local_protocol_version,
            self.device_info.device.duid,
        )
        request = RoborockMessage(
            protocol=RoborockMessageProtocol.HELLO_REQUEST,
            version=local_protocol_version.encode(),
            random=self._connect_nonce,
            seq=1,
        )
        try:
            response = await self._send_message(
                roborock_message=request,
                request_id=request.seq,
                response_protocol=RoborockMessageProtocol.HELLO_RESPONSE,
            )
            self._ack_nonce = response.random
            self._set_encoder_decoder()
            self._local_protocol_version = local_protocol_version

            self._logger.debug(
                "Client %s speaks the %s protocol.",
                self.device_info.device.duid,
                local_protocol_version,
            )
            return True
        except RoborockException as e:
            self._logger.debug(
                "Client %s did not respond or does not speak the %s protocol. %s",
                self.device_info.device.duid,
                local_protocol_version,
                e,
            )
            return False

    async def hello(self):
        """Send hello to the device to negotiate protocol."""
        if self._local_protocol_version:
            # version is forced
            if not await self._do_hello(self._local_protocol_version):
                raise RoborockException(f"Failed to connect to device with protocol {self._local_protocol_version}")
        else:
            # try 1.0, then L01
            if not await self._do_hello(LocalProtocolVersion.V1):
                if not await self._do_hello(LocalProtocolVersion.L01):
                    raise RoborockException("Failed to connect to device with any known protocol")

    async def ping(self) -> None:
        ping_message = RoborockMessage(
            protocol=RoborockMessageProtocol.PING_REQUEST, version=self.local_protocol_version.encode()
        )
        await self._send_message(
            roborock_message=ping_message,
            request_id=ping_message.seq,
            response_protocol=RoborockMessageProtocol.PING_RESPONSE,
        )

    def _send_msg_raw(self, data: bytes):
        try:
            if not self.transport:
                raise RoborockException("Can not send message without connection")
            self.transport.write(data)
        except Exception as e:
            raise RoborockException(e) from e

    async def _send_command(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
    ):
        if method in CLOUD_REQUIRED:
            raise RoborockException(f"Method {method} is not supported over local connection")
        request_message = RequestMessage(method=method, params=params)
        roborock_message = request_message.encode_message(
            RoborockMessageProtocol.GENERAL_REQUEST,
            version=self.local_protocol_version,
        )
        self._logger.debug("Building message id %s for method %s", request_message.request_id, method)
        return await self._send_message(
            roborock_message,
            request_id=request_message.request_id,
            response_protocol=RoborockMessageProtocol.GENERAL_REQUEST,
            method=method,
            params=params,
        )

    async def _send_message(
        self,
        roborock_message: RoborockMessage,
        request_id: int,
        response_protocol: int,
        method: str | None = None,
        params: list | dict | int | None = None,
    ) -> RoborockMessage:
        await self.validate_connection()
        msg = self._encoder(roborock_message)
        if method:
            self._logger.debug(f"id={request_id} Requesting method {method} with {params}")
        # Send the command to the Roborock device
        async_response = self._async_response(request_id, response_protocol)
        self._send_msg_raw(msg)
        diagnostic_key = method if method is not None else "unknown"
        try:
            response = await async_response
        except VacuumError as err:
            self._diagnostic_data[diagnostic_key] = {
                "params": params,
                "error": err,
            }
            raise CommandVacuumError(method, err) from err
        self._diagnostic_data[diagnostic_key] = {
            "params": params,
            "response": response,
        }
        if roborock_message.protocol == RoborockMessageProtocol.GENERAL_REQUEST:
            self._logger.debug(f"id={request_id} Response from method {method}: {response}")
        if response == "retry":
            raise RoborockException(f"Command {method} failed with 'retry' message; Device is busy, try again later")
        return response
