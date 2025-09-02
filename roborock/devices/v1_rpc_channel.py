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

from roborock.containers import RoborockBase
from roborock.exceptions import RoborockException
from roborock.protocols.v1_protocol import (
    CommandType,
    ParamsType,
    RequestMessage,
    SecurityData,
    decode_rpc_response,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

from .local_channel import LocalChannel
from .mqtt_channel import MqttChannel

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = 10.0


_T = TypeVar("_T", bound=RoborockBase)


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


class CombinedV1RpcChannel(BaseV1RpcChannel):
    """A V1 RPC channel that can use both local and MQTT channels, preferring local when available."""

    def __init__(
        self, local_channel: LocalChannel, local_rpc_channel: V1RpcChannel, mqtt_channel: V1RpcChannel
    ) -> None:
        """Initialize the combined channel with local and MQTT channels."""
        self._local_channel = local_channel
        self._local_rpc_channel = local_rpc_channel
        self._mqtt_rpc_channel = mqtt_channel

    async def _send_raw_command(
        self,
        method: CommandType,
        *,
        params: ParamsType = None,
    ) -> Any:
        """Send a command and return a parsed response RoborockBase type."""
        if self._local_channel.is_connected:
            return await self._local_rpc_channel.send_command(method, params=params)
        return await self._mqtt_rpc_channel.send_command(method, params=params)


class PayloadEncodedV1RpcChannel(BaseV1RpcChannel):
    """Protocol for V1 channels that send encoded commands."""

    def __init__(
        self,
        name: str,
        channel: MqttChannel | LocalChannel,
        payload_encoder: Callable[[RequestMessage], RoborockMessage],
    ) -> None:
        """Initialize the channel with a raw channel and an encoder function."""
        self._name = name
        self._channel = channel
        self._payload_encoder = payload_encoder

    async def _send_raw_command(
        self,
        method: CommandType,
        *,
        params: ParamsType = None,
    ) -> Any:
        """Send a command and return a parsed response RoborockBase type."""
        _LOGGER.debug("Sending command (%s): %s, params=%s", self._name, method, params)
        request_message = RequestMessage(method, params=params)
        message = self._payload_encoder(request_message)

        future: asyncio.Future[dict[str, Any]] = asyncio.Future()

        def find_response(response_message: RoborockMessage) -> None:
            try:
                decoded = decode_rpc_response(response_message)
            except RoborockException:
                return
            if decoded.request_id == request_message.request_id:
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
    )


def create_combined_rpc_channel(local_channel: LocalChannel, mqtt_rpc_channel: V1RpcChannel) -> V1RpcChannel:
    """Create a V1 RPC channel that combines local and MQTT channels."""
    local_rpc_channel = PayloadEncodedV1RpcChannel(
        "local",
        local_channel,
        lambda x: x.encode_message(RoborockMessageProtocol.GENERAL_REQUEST),
    )
    return CombinedV1RpcChannel(local_channel, local_rpc_channel, mqtt_rpc_channel)
