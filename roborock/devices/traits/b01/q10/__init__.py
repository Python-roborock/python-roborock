"""Traits for Q10 B01 devices."""

import asyncio
import logging
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.rpc.b01_q10_channel import stream_decoded_responses
from roborock.devices.traits import Trait
from roborock.devices.transport.mqtt_channel import MqttChannel

from .command import CommandTrait
from .status import StatusTrait
from .vacuum import VacuumTrait

__all__ = [
    "Q10PropertiesApi",
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

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the B01Props API."""
        self._channel = channel
        self.command = CommandTrait(channel)
        self.vacuum = VacuumTrait(self.command)
        self.status = StatusTrait()
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
        """Persistent loop to listen for status updates."""
        async for decoded_dps in stream_decoded_responses(self._channel):
            _LOGGER.debug("Received Q10 status update: %s", decoded_dps)

            # Notify all traits about a new message and each trait will
            # only update what fields that it is responsible for.
            # More traits can be added here below.
            self.status.update_from_dps(decoded_dps)


def create(channel: MqttChannel) -> Q10PropertiesApi:
    """Create traits for B01 devices."""
    return Q10PropertiesApi(channel)
