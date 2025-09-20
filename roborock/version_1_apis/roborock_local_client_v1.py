import asyncio
import json
import logging
import math
import time
from asyncio import Lock, TimerHandle, Transport, get_running_loop
from collections.abc import Callable
from dataclasses import dataclass

import async_timeout

from .. import CommandVacuumError, DeviceData, RoborockCommand
from ..api import RoborockClient
from ..exceptions import RoborockConnectionException, RoborockException, VacuumError
from ..protocol import Decoder, Encoder, create_local_decoder, create_local_encoder
from ..protocols.v1_protocol import RequestMessage
from ..roborock_message import RoborockMessage, RoborockMessageProtocol
from ..util import RoborockLoggerAdapter, get_next_int
from .roborock_client_v1 import CLOUD_REQUIRED, RoborockClientV1

_LOGGER = logging.getLogger(__name__)


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

    def __init__(self, device_data: DeviceData, queue_timeout: int = 4, version: str | None = None):
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
        self._version = version
        self._connect_nonce: int | None = None
        self._ack_nonce: int | None = None
        if version == "L01":
            self._set_l01_encoder_decoder()
        else:
            self._encoder: Encoder = create_local_encoder(device_data.device.local_key)
            self._decoder: Decoder = create_local_decoder(device_data.device.local_key)
        self.queue_timeout = queue_timeout
        self._logger = RoborockLoggerAdapter(device_data.device.name, _LOGGER)

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

    def _set_l01_encoder_decoder(self):
        """Tell the system to use the L01 encoder/decoder."""
        self._encoder = create_local_encoder(self.device_info.device.local_key, self._connect_nonce, self._ack_nonce)
        self._decoder = create_local_decoder(self.device_info.device.local_key, self._connect_nonce, self._ack_nonce)

    async def _do_hello(self, version: str) -> bool:
        """Perform the initial handshaking."""
        self._logger.debug(f"Attempting to use the {version} protocol for client {self.device_info.device.duid}...")
        self._connect_nonce = get_next_int(10000, 32767)
        request = RoborockMessage(
            protocol=RoborockMessageProtocol.HELLO_REQUEST,
            version=version.encode(),
            random=self._connect_nonce,
            seq=1,
        )
        try:
            response = await self._send_message(
                roborock_message=request,
                request_id=request.seq,
                response_protocol=RoborockMessageProtocol.HELLO_RESPONSE,
            )
            if response.version.decode() == "L01":
                self._ack_nonce = response.random
                self._set_l01_encoder_decoder()
            self._version = version
            self._logger.debug(f"Client {self.device_info.device.duid} speaks the {version} protocol.")
            return True
        except RoborockException as e:
            self._logger.debug(
                f"Client {self.device_info.device.duid} did not respond or does not speak the {version} protocol. {e}"
            )
            return False

    async def hello(self):
        """Send hello to the device to negotiate protocol."""
        if self._version:
            # version is forced
            if not await self._do_hello(self._version):
                raise RoborockException(f"Failed to connect to device with protocol {self._version}")
        else:
            # try 1.0, then L01
            if not await self._do_hello("1.0"):
                if not await self._do_hello("L01"):
                    raise RoborockException("Failed to connect to device with any known protocol")

    async def ping(self) -> None:
        ping_message = RoborockMessage(
            protocol=RoborockMessageProtocol.PING_REQUEST,
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
        if self._version == "L01":
            request_id = get_next_int(10000, 999999)
            dps_payload = {
                "id": request_id,
                "method": method,
                "params": params,
            }
            ts = math.floor(time.time())
            payload = {
                "dps": {str(RoborockMessageProtocol.RPC_REQUEST.value): json.dumps(dps_payload, separators=(",", ":"))},
                "t": ts,
            }
            roborock_message = RoborockMessage(
                protocol=RoborockMessageProtocol.GENERAL_REQUEST,
                payload=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                version=self._version.encode(),
                timestamp=ts,
            )
            self._logger.debug("Building message id %s for method %s", request_id, method)
            return await self._send_message(
                roborock_message,
                request_id=request_id,
                response_protocol=RoborockMessageProtocol.GENERAL_REQUEST,
                method=method,
                params=params,
            )

        request_message = RequestMessage(method=method, params=params)
        roborock_message = request_message.encode_message(RoborockMessageProtocol.GENERAL_REQUEST)
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
