from __future__ import annotations

import logging
from typing import Any

from roborock.roborock_message import RoborockZeoProtocol

from ..a01_channel import send_decoded_command
from ..mqtt_channel import MqttChannel
from .trait import Trait

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "ZeoApi",
]


class ZeoApi(Trait):
    """API for interacting with Zeo devices."""

    name = "zeo"

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the Zeo API."""
        self._channel = channel

    async def query_values(self, protocols: list[RoborockZeoProtocol]) -> dict[RoborockZeoProtocol, Any]:
        """Query the device for the values of the given protocols."""
        params = {RoborockZeoProtocol.ID_QUERY: [int(p) for p in protocols]}
        return await send_decoded_command(self._channel, params)

    async def set_value(self, protocol: RoborockZeoProtocol, value: Any) -> dict[RoborockZeoProtocol, Any]:
        """Set a value for a specific protocol on the device."""
        params = {protocol: value}
        return await send_decoded_command(self._channel, params)
