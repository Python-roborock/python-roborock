from __future__ import annotations

import logging
from typing import Any

from roborock.roborock_message import RoborockDyadDataProtocol

from ..a01_channel import send_decoded_command
from ..mqtt_channel import MqttChannel
from .trait import Trait

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "DyadApi",
]


class DyadApi(Trait):
    """API for interacting with Dyad devices."""

    name = "dyad"

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the Dyad API."""
        self._channel = channel

    async def query_values(self, protocols: list[RoborockDyadDataProtocol]) -> dict[RoborockDyadDataProtocol, Any]:
        """Query the device for the values of the given Dyad protocols."""
        params = {RoborockDyadDataProtocol.ID_QUERY: [int(p) for p in protocols]}
        return await send_decoded_command(self._channel, params)

    async def set_value(self, protocol: RoborockDyadDataProtocol, value: Any) -> dict[RoborockDyadDataProtocol, Any]:
        """Set a value for a specific protocol on the device."""
        params = {protocol: value}
        return await send_decoded_command(self._channel, params)
