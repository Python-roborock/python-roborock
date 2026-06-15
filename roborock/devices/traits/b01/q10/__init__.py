"""Traits for Q10 B01 devices."""

import asyncio
import logging

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.traits import Trait
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q10_protocol import decode_rpc_response
from roborock.roborock_message import RoborockMessage

from .command import CommandTrait
from .map import MapContentTrait
from .remote import RemoteTrait
from .status import StatusTrait
from .vacuum import VacuumTrait

__all__ = [
    "Q10PropertiesApi",
    "MapContentTrait",
]

_LOGGER = logging.getLogger(__name__)


class Q10PropertiesApi(Trait):
    """API for interacting with B01 devices."""

    command: CommandTrait
    """Trait for sending commands to Q10 devices."""

    status: StatusTrait
    """Trait for managing the status of Q10 devices."""

    vacuum: VacuumTrait
    """Trait for sending vacuum related commands to Q10 devices."""

    remote: RemoteTrait
    """Trait for sending remote control related commands to Q10 devices."""

    map: MapContentTrait
    """Trait for fetching the current parsed map (image + rooms)."""

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the B01Props API."""
        self._channel = channel
        self.command = CommandTrait(channel)
        self.vacuum = VacuumTrait(self.command)
        self.remote = RemoteTrait(self.command)
        self.status = StatusTrait()
        self.map = MapContentTrait()
        self._subscribe_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start any necessary subscriptions for the trait."""
        self._subscribe_task = asyncio.create_task(self._subscribe_loop())

    async def close(self) -> None:
        """Close any resources held by the trait."""
        if self._subscribe_task is not None:
            self._subscribe_task.cancel()
            try:
                await self._subscribe_task
            except asyncio.CancelledError:
                pass  # ignore cancellation errors
            self._subscribe_task = None

    async def refresh(self) -> None:
        """Refresh all traits."""
        # Sending the REQUEST_DPS will cause the device to send all DPS values
        # to the device. Updates will be received by the subscribe loop below.
        await self.command.send(B01_Q10_DP.REQUEST_DPS, params={})

    async def _subscribe_loop(self) -> None:
        """Persistent loop dispatching pushed messages to the read-model traits."""
        async for message in self._channel.subscribe_stream():
            self._handle_message(message)

    def _handle_message(self, message: RoborockMessage) -> None:
        """Route a single pushed message to the trait responsible for it.

        Map/trace pushes arrive as protocol-301 ``MAP_RESPONSE`` messages (not
        DPS), so they are handled separately from the status DPS stream. The Q10
        is entirely push-driven: there is no synchronous get-map request, the
        device just publishes its current map (a ``dpRequestDps`` nudges it to).
        """
        if self.map.update_from_map_response(message):
            return

        try:
            decoded_dps = decode_rpc_response(message)
        except RoborockException as ex:
            _LOGGER.debug("Failed to decode Q10 RPC response: %s: %s", message, ex)
            return

        _LOGGER.debug("Received Q10 status update: %s", decoded_dps)
        # Notify all traits about a new message and each trait will
        # only update what fields that it is responsible for.
        # More traits can be added here below.
        self.status.update_from_dps(decoded_dps)


def create(channel: MqttChannel) -> Q10PropertiesApi:
    """Create traits for B01 devices."""
    return Q10PropertiesApi(channel)
