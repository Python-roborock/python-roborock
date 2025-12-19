"""B01 Q10 MQTT helpers (send + async inbound routing).

Q10 devices do not reliably correlate request/response via the message sequence
number. Additionally, DP updates ("prop updates") can arrive at any time.

To avoid race conditions, we route inbound messages through a single async
consumer and then dispatch:
- prop updates (DP changes) -> trait update callbacks + DP waiters
- other response types -> placeholders for future routing
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any, Final

from roborock.exceptions import RoborockException
from roborock.protocols.b01_protocol import decode_rpc_response, encode_b01_mqtt_payload
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol

from .mqtt_channel import MqttChannel

_LOGGER = logging.getLogger(__name__)


class B01Q10MessageRouter:
    """Async router for inbound B01 Q10 messages."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[RoborockMessage] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._prop_update_callbacks: list[Callable[[dict[int, Any]], None]] = []

    def add_prop_update_callback(self, callback: Callable[[dict[int, Any]], None]) -> Callable[[], None]:
        """Register a callback for prop updates (decoded DP dict)."""
        self._prop_update_callbacks.append(callback)

        def remove() -> None:
            try:
                self._prop_update_callbacks.remove(callback)
            except ValueError:
                pass

        return remove

    def feed(self, message: RoborockMessage) -> None:
        """Feed an inbound message into the router (non-async safe)."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="b01-q10-message-router")
        self._queue.put_nowait(message)

    def close(self) -> None:
        """Stop the router task."""
        if self._task and not self._task.done():
            self._task.cancel()

    async def _run(self) -> None:
        while True:
            message = await self._queue.get()
            try:
                self._handle_message(message)
            except Exception as ex:  # noqa: BLE001
                _LOGGER.debug("Unhandled error routing B01 Q10 message: %s", ex)

    def _handle_message(self, message: RoborockMessage) -> None:
        # Placeholder for additional response types.
        match message.protocol:
            case RoborockMessageProtocol.RPC_RESPONSE:
                self._handle_rpc_response(message)
            case RoborockMessageProtocol.MAP_RESPONSE:
                _LOGGER.debug("B01 Q10 map response received (unrouted placeholder)")
            case _:
                _LOGGER.debug("B01 Q10 message protocol %s received (unrouted placeholder)", message.protocol)

    def _handle_rpc_response(self, message: RoborockMessage) -> None:
        try:
            decoded = decode_rpc_response(message)
        except RoborockException as ex:
            _LOGGER.info("Failed to decode B01 Q10 message: %s: %s", message, ex)
            return

        # Identify response type and route accordingly.
        #
        # Based on Hermes Q10: DP changes are delivered as "deviceDpChanged" events.
        # Many DPs are delivered nested inside dpCommon (101), so we flatten that
        # envelope into regular DP keys for downstream trait updates.
        dps = _flatten_q10_dps(decoded)
        if not dps:
            return

        for cb in list(self._prop_update_callbacks):
            try:
                cb(dps)
            except Exception as ex:  # noqa: BLE001
                _LOGGER.debug("Error in B01 Q10 prop update callback: %s", ex)


_ROUTER_ATTR: Final[str] = "_b01_q10_router"


def get_b01_q10_router(mqtt_channel: MqttChannel) -> B01Q10MessageRouter:
    """Get (or create) the per-channel B01 Q10 router."""
    router = getattr(mqtt_channel, _ROUTER_ATTR, None)
    if router is None:
        router = B01Q10MessageRouter()
        setattr(mqtt_channel, _ROUTER_ATTR, router)
    return router


def _flatten_q10_dps(decoded: dict[int, Any]) -> dict[int, Any]:
    """Flatten Q10 dpCommon (101) payload into normal DP keys.

    Example input from device:
        {101: {"25": 1, "26": 54, "6": 876}, 122: 88, 123: 2, ...}

    Output:
        {25: 1, 26: 54, 6: 876, 122: 88, 123: 2, ...}
    """
    flat: dict[int, Any] = {}
    for dp, value in decoded.items():
        if dp == 101 and isinstance(value, dict):
            for inner_k, inner_v in value.items():
                try:
                    inner_dp = int(inner_k)
                except (TypeError, ValueError):
                    continue
                flat[inner_dp] = inner_v
            continue
        flat[dp] = value
    return flat


async def send_b01_dp_command(
    mqtt_channel: MqttChannel,
    dps: dict[int, Any],
) -> None:
    """Send a raw DP command on the MQTT channel.

    Q10 devices can emit DP updates at any time, and do not reliably correlate
    request/response via the message sequence number.

    For Q10 we treat **all** outbound messages as fire-and-forget:
    - We publish the DP command.
    - We do not wait for any response payload.
    - Traits are updated via async prop updates routed by `B01Q10MessageRouter`.

    """
    _LOGGER.debug("Sending MQTT DP command: %s", dps)
    msg = encode_b01_mqtt_payload(dps)

    _LOGGER.debug("Publishing B01 Q10 MQTT message: %s", msg)
    try:
        await mqtt_channel.publish(msg)
        await mqtt_channel.health_manager.on_success()
    except TimeoutError:
        await mqtt_channel.health_manager.on_timeout()
        _LOGGER.debug("B01 Q10 MQTT publish timed out for dps=%s", dps)
    except Exception as ex:  # noqa: BLE001
        # Fire-and-forget means callers never see errors; keep the task quiet.
        _LOGGER.debug("B01 Q10 MQTT publish failed for dps=%s: %s", dps, ex)

    return None
