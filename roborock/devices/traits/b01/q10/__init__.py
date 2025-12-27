"""Traits for Q10 B01 devices."""

import asyncio
import logging
from typing import Any

from roborock import B01Props
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.b01_q10_channel import ParamsType, send_command, stream_decoded_responses
from roborock.devices.mqtt_channel import MqttChannel
from roborock.devices.traits import Trait

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "Q10PropertiesApi",
]


class Q10PropertiesApi(Trait):
    """API for interacting with B01 devices."""

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the B01Props API."""
        self._channel = channel
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start any necessary subscriptions for the trait."""
        self._task = asyncio.create_task(self._run_loop())

    async def close(self) -> None:
        """Close any resources held by the trait."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass  # ignore cancellation errors
            self._task = None

    async def start_clean(self) -> None:
        """Start cleaning."""
        await self.send(
            command=B01_Q10_DP.START_CLEAN,
            # TODO: figure out other commands
            # 1 = start cleaning
            # 2 = "electoral" clean, also has "clean_parameters"
            # 4 = fast create map
            params={"cmd": 1},
        )

    async def pause_clean(self) -> None:
        """Pause cleaning."""
        await self.send(
            command=B01_Q10_DP.PAUSE,
            params={},
        )

    async def resume_clean(self) -> None:
        """Resume cleaning."""
        await self.send(
            command=B01_Q10_DP.RESUME,
            params={},
        )

    async def stop_clean(self) -> None:
        """Stop cleaning."""
        await self.send(
            command=B01_Q10_DP.STOP,
            params={},
        )

    async def return_to_dock(self) -> None:
        """Return to dock."""
        await self.send(
            command=B01_Q10_DP.START_DOCK_TASK,
            params={},
        )

    async def send(self, command: B01_Q10_DP, params: ParamsType) -> None:
        """Send a command to the device."""
        await send_command(
            self._channel,
            command=command,
            params=params,
        )

    async def _run_loop(self) -> None:
        """Run the main loop for processing incoming messages."""
        async for decoded_dps in stream_decoded_responses(self._channel):
            _LOGGER.debug("Received B01 Q10 decoded DPS: %s", decoded_dps)

            # Temporary debugging: Log all common values
            if B01_Q10_DP.COMMON not in decoded_dps:
                continue
            common_values = decoded_dps[B01_Q10_DP.COMMON]
            for key, value in common_values.items():
                _LOGGER.debug("%s: %s", key, value)


def create(channel: MqttChannel) -> Q10PropertiesApi:
    """Create traits for B01 devices."""
    return Q10PropertiesApi(channel)
