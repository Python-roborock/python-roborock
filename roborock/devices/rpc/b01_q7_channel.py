"""Thin wrapper around the MQTT channel for Roborock B01 Q7 devices."""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Protocol, TypeAlias, TypeVar

from roborock.data import HomeDataDevice, HomeDataProduct
from roborock.devices.transport.channel import Channel
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q7_protocol import (
    B01_Q7_DPS,
    B01_VERSION,
    CommandType,
    MapKey,
    ParamsType,
    Q7RequestMessage,
    create_map_key,
    decode_map_payload,
    decode_rpc_response,
    encode_mqtt_payload,
)
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = 10.0
_T = TypeVar("_T")
DecodedB01Response: TypeAlias = dict[str, object] | str


class Q7RpcChannel(Protocol):
    """Protocol for Q7 RPC channels."""

    async def send_command(
        self,
        command: CommandType,
        params: ParamsType = None,
    ) -> DecodedB01Response:
        """Send a command and get a decoded response."""
        ...


class Q7MapRpcChannel(Protocol):
    """Protocol for Q7 map RPC channels."""

    async def send_map_command(
        self,
        command: CommandType,
        params: ParamsType = None,
    ) -> bytes:
        """Send a map command and get decoded bytes."""
        ...


def _matches_map_response(response_message: RoborockMessage, *, version: bytes | None) -> bytes | None:
    """Return raw map payload bytes for matching MAP_RESPONSE messages."""
    if (
        response_message.protocol == RoborockMessageProtocol.MAP_RESPONSE
        and response_message.payload
        and response_message.version == version
    ):
        return response_message.payload
    return None


async def _send_command(
    mqtt_channel: MqttChannel,
    request_message: Q7RequestMessage,
    *,
    response_matcher: Callable[[RoborockMessage], _T | None],
) -> _T:
    """Publish a B01 command and resolve on the first matching response."""
    roborock_message = encode_mqtt_payload(request_message)
    future: asyncio.Future[_T] = asyncio.get_running_loop().create_future()

    def on_message(response_message: RoborockMessage) -> None:
        if future.done():
            return
        try:
            response = response_matcher(response_message)
        except Exception as ex:
            future.set_exception(ex)
            return
        if response is not None:
            future.set_result(response)

    unsub = await mqtt_channel.subscribe(on_message)
    try:
        await mqtt_channel.publish(roborock_message)
        return await asyncio.wait_for(future, timeout=_TIMEOUT)
    finally:
        unsub()


async def send_decoded_command(
    mqtt_channel: MqttChannel,
    request_message: Q7RequestMessage,
) -> DecodedB01Response:
    """Send a command on the MQTT channel and get a decoded response."""
    _LOGGER.debug("Sending B01 MQTT command: %s", request_message)

    def find_response(response_message: RoborockMessage) -> DecodedB01Response | None:
        """Handle incoming messages and resolve the future."""
        try:
            decoded_dps = decode_rpc_response(response_message)
        except RoborockException as ex:
            _LOGGER.debug(
                "Failed to decode B01 RPC response (expecting method=%s msg_id=%s): %s: %s",
                request_message.command,
                request_message.msg_id,
                response_message,
                ex,
            )
            return None
        for dps_value in decoded_dps.values():
            # valid responses are JSON strings wrapped in the dps value
            if not isinstance(dps_value, str):
                _LOGGER.debug("Received unexpected response: %s", dps_value)
                continue

            try:
                inner = json.loads(dps_value)
            except (json.JSONDecodeError, TypeError):
                _LOGGER.debug("Received unexpected response: %s", dps_value)
                continue
            if isinstance(inner, dict) and inner.get("msgId") == str(request_message.msg_id):
                _LOGGER.debug("Received query response: %s", inner)
                code = inner.get("code", 0)
                if code != 0:
                    error_msg = f"B01 command failed with code {code} ({request_message})"
                    _LOGGER.debug("B01 error response: %s", error_msg)
                    raise RoborockException(error_msg)
                data = inner.get("data")
                if request_message.command == "prop.get" and not isinstance(data, dict):
                    raise RoborockException(f"Unexpected data type for response {data} ({request_message})")
                return data
        return None

    try:
        return await _send_command(
            mqtt_channel,
            request_message,
            response_matcher=find_response,
        )
    except TimeoutError as ex:
        raise RoborockException(f"B01 command timed out after {_TIMEOUT}s ({request_message})") from ex
    except RoborockException as ex:
        _LOGGER.warning(
            "Error sending B01 decoded command (%s): %s",
            request_message,
            ex,
        )
        raise
    except Exception as ex:
        _LOGGER.exception(
            "Error sending B01 decoded command (%s): %s",
            request_message,
            ex,
        )
        raise


class B01Q7Channel(Channel, Q7RpcChannel, Q7MapRpcChannel):
    """Unified B01 Q7 channel wrapping MQTT transport."""

    def __init__(self, mqtt_channel: MqttChannel, map_key: MapKey) -> None:
        self._mqtt_channel = mqtt_channel
        self._map_key = map_key

    @property
    def is_connected(self) -> bool:
        return self._mqtt_channel.is_connected

    @property
    def is_local_connected(self) -> bool:
        return False

    async def subscribe(self, callback: Callable[[RoborockMessage], None]) -> Callable[[], None]:
        return await self._mqtt_channel.subscribe(callback)

    async def send_command(
        self,
        command: CommandType,
        params: ParamsType = None,
    ) -> DecodedB01Response:
        return await send_decoded_command(
            self._mqtt_channel,
            Q7RequestMessage(dps=B01_Q7_DPS, command=command, params=params),
        )

    async def send_map_command(
        self,
        command: CommandType,
        params: ParamsType = None,
    ) -> bytes:
        """Send a map upload command and return decoded SCMap bytes."""
        request_message = Q7RequestMessage(dps=B01_Q7_DPS, command=command, params=params)
        try:
            raw_payload = await _send_command(
                self._mqtt_channel,
                request_message,
                response_matcher=lambda response_message: _matches_map_response(response_message, version=B01_VERSION),
            )
        except TimeoutError as ex:
            raise RoborockException(f"B01 map command timed out after {_TIMEOUT}s ({request_message})") from ex

        return decode_map_payload(raw_payload, map_key=self._map_key)


def create_b01_q7_channel(
    device: HomeDataDevice,
    product: HomeDataProduct,
    mqtt_channel: MqttChannel,
) -> B01Q7Channel:
    """Create a B01Q7Channel for the given device."""
    if device.sn is None or product.model is None:
        raise RoborockException(
            f"Device serial number and product model are required (sn: {device.sn}, model: {product.model})"
        )
    map_key = create_map_key(serial=device.sn, model=product.model)
    return B01Q7Channel(mqtt_channel, map_key)
