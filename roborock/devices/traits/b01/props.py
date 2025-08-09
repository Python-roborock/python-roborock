from __future__ import annotations

import logging
from typing import Any

from roborock import RoborockB01Methods
from roborock.roborock_message import RoborockB01Props, RoborockDyadDataProtocol

from ...b01_channel import send_decoded_command
from ...mqtt_channel import MqttChannel
from ..trait import Trait

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "B01PropsApi",
]


class B01PropsApi(Trait):
    """API for interacting with B01 devices."""

    name = "B01_props"

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the B01Props API."""
        self._channel = channel

    async def query_values(self, props: list[RoborockB01Props]) -> dict[RoborockDyadDataProtocol, Any]:
        """Query the device for the values of the given Dyad protocols."""
        return await send_decoded_command(self._channel, dps=10000, command=RoborockB01Methods.GET_PROP, params=props)
