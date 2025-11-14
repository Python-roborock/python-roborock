"""V1 Rpc Channel for Roborock devices.

This is a wrapper around the V1 channel that provides a higher level interface
for sending typed commands and receiving typed responses. This also provides
a simple interface for sending commands and receiving responses over both MQTT
and local connections, preferring local when available.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any, Protocol, TypeVar, overload

from roborock.data import RoborockBase
from roborock.exceptions import RoborockException
from roborock.protocols.v1_protocol import (
    CommandType,
    MapResponse,
    ParamsType,
    RequestMessage,
    ResponseData,
    ResponseMessage,
    SecurityData,
    create_map_response_decoder,
    decode_rpc_response,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

from .local_channel import LocalChannel
from .mqtt_channel import MqttChannel

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = 10.0


_T = TypeVar("_T", bound=RoborockBase)
_V = TypeVar("_V")


class V1RpcChannel(Protocol):
    """Protocol for V1 RPC channels.

    This is a wrapper around a raw channel that provides a high-level interface
    for sending commands and receiving responses.
    """

    @overload
    async def send_command(
        self,
        method: CommandType,
        *,
        params: ParamsType = None,
    ) -> Any:
        """Send a command and return a decoded response."""
        ...

    @overload
    async def send_command(
        self,
        method: CommandType,
        *,
        response_type: type[_T],
        params: ParamsType = None,
    ) -> _T:
        """Send a command and return a parsed response RoborockBase type."""
        ...


class BaseV1RpcChannel(V1RpcChannel):
    """Base implementation that provides the typed response logic."""

    async def send_command(
        self,
        method: CommandType,
        *,
        response_type: type[_T] | None = None,
        params: ParamsType = None,
    ) -> _T | Any:
        """Send a command and return either a decoded or parsed response."""
        decoded_response = await self._send_raw_command(method, params=params)

        if response_type is not None:
            return response_type.from_dict(decoded_response)
        return decoded_response

    async def _send_raw_command(
        self,
        method: CommandType,
        *,
        params: ParamsType = None,
    ) -> Any:
        """Send a raw command and return the decoded response. Must be implemented by subclasses."""
        raise NotImplementedError


class PickFirstAvailable(BaseV1RpcChannel):
    """A V1 RPC channel that tries multiple channels and picks the first that works."""

    def __init__(
        self,
        channel_cbs: list[Callable[[], V1RpcChannel | None]],
    ) -> None:
        """Initialize the pick-first-available channel."""
        self._channel_cbs = channel_cbs

    async def _send_raw_command(
        self,
        method: CommandType,
        *,
        params: ParamsType = None,
    ) -> Any:
        """Send a command and return a parsed response RoborockBase type."""
        for channel_cb in self._channel_cbs:
            if channel := channel_cb():
                return await channel.send_command(method, params=params)
        raise RoborockException("No available connection to send command")


class PayloadEncodedV1RpcChannel(BaseV1RpcChannel):
    """Protocol for V1 channels that send encoded commands."""

    def __init__(
        self,
        name: str,
        channel: MqttChannel | LocalChannel,
        payload_encoder: Callable[[RequestMessage], RoborockMessage],
        decoder: Callable[[RoborockMessage], ResponseMessage] | Callable[[RoborockMessage], MapResponse | None],
    ) -> None:
        """Initialize the channel with a raw channel and an encoder function."""
        self._name = name
        self._channel = channel
        self._payload_encoder = payload_encoder
        self._decoder = decoder

    async def _send_raw_command(
        self,
        method: CommandType,
        *,
        params: ParamsType = None,
    ) -> ResponseData | bytes:
        """Send a command and return a parsed response RoborockBase type."""
        request_message = RequestMessage(method, params=params)
        _LOGGER.debug(
            "Sending command (%s, request_id=%s): %s, params=%s", self._name, request_message.request_id, method, params
        )
        message = self._payload_encoder(request_message)

        future: asyncio.Future[ResponseData | bytes] = asyncio.Future()

        def find_response(response_message: RoborockMessage) -> None:
            try:
                decoded = self._decoder(response_message)
            except RoborockException as ex:
                _LOGGER.debug("Exception while decoding message (%s): %s", response_message, ex)
                return
            if decoded is None:
                return
            _LOGGER.debug("Received response (%s, request_id=%s)", self._name, decoded.request_id)
            if decoded.request_id == request_message.request_id:
                if isinstance(decoded, ResponseMessage) and decoded.api_error:
                    future.set_exception(decoded.api_error)
                else:
                    future.set_result(decoded.data)

        unsub = await self._channel.subscribe(find_response)
        try:
            await self._channel.publish(message)
            return await asyncio.wait_for(future, timeout=_TIMEOUT)
        except TimeoutError as ex:
            future.cancel()
            raise RoborockException(f"Command timed out after {_TIMEOUT}s") from ex
        finally:
            unsub()


def create_mqtt_rpc_channel(mqtt_channel: MqttChannel, security_data: SecurityData) -> V1RpcChannel:
    """Create a V1 RPC channel using an MQTT channel."""
    return PayloadEncodedV1RpcChannel(
        "mqtt",
        mqtt_channel,
        lambda x: x.encode_message(RoborockMessageProtocol.RPC_REQUEST, security_data=security_data),
        decode_rpc_response,
    )


def create_local_rpc_channel(local_channel: LocalChannel) -> V1RpcChannel:
    """Create a V1 RPC channel using a local channel."""
    return PayloadEncodedV1RpcChannel(
        "local",
        local_channel,
        lambda x: x.encode_message(RoborockMessageProtocol.GENERAL_REQUEST, version=local_channel.protocol_version),
        decode_rpc_response,
    )


def create_map_rpc_channel(
    mqtt_channel: MqttChannel,
    security_data: SecurityData,
) -> V1RpcChannel:
    """Create a V1 RPC channel that fetches map data.

    This will prefer local channels when available, falling back to MQTT
    channels if not. If neither is available, an exception will be raised
    when trying to send a command.
    """
    return PayloadEncodedV1RpcChannel(
        "map",
        mqtt_channel,
        lambda x: x.encode_message(RoborockMessageProtocol.RPC_REQUEST, security_data=security_data),
        create_map_response_decoder(security_data=security_data),
    )
