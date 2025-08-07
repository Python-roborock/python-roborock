"""Module for Roborock devices.

This interface is experimental and subject to breaking changes without notice
until the API is stable.
"""

import logging
from abc import ABC
from collections.abc import Callable, Mapping
from types import MappingProxyType

from roborock.containers import HomeDataDevice
from roborock.roborock_message import RoborockMessage

from .channel import Channel
from .traits.trait import Trait

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "RoborockDevice",
]


class RoborockDevice(ABC):
    """A generic channel for establishing a connection with a Roborock device.

    Individual channel implementations have their own methods for speaking to
    the device that hide some of the protocol specific complexity, but they
    are still specialized for the device type and protocol.
    """

    def __init__(
        self,
        device_info: HomeDataDevice,
        channel: Channel,
        traits: list[Trait],
    ) -> None:
        """Initialize the RoborockDevice.

        The device takes ownership of the channel for communication with the device.
        Use `connect()` to establish the connection, which will set up the appropriate
        protocol channel. Use `close()` to clean up all connections.
        """
        self._duid = device_info.duid
        self._name = device_info.name
        self._channel = channel
        self._unsub: Callable[[], None] | None = None
        self._trait_map = {trait.name: trait for trait in traits}
        if len(self._trait_map) != len(traits):
            raise ValueError("Duplicate trait names found in traits list")

    @property
    def duid(self) -> str:
        """Return the device unique identifier (DUID)."""
        return self._duid

    @property
    def name(self) -> str:
        """Return the device name."""
        return self._name

    @property
    def is_connected(self) -> bool:
        """Return whether the device is connected."""
        return self._channel.is_connected

    async def connect(self) -> None:
        """Connect to the device using the appropriate protocol channel."""
        if self._unsub:
            raise ValueError("Already connected to the device")
        self._unsub = await self._channel.subscribe(self._on_message)
        _LOGGER.info("Connected to V1 device %s", self.name)

    async def close(self) -> None:
        """Close all connections to the device."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    def _on_message(self, message: RoborockMessage) -> None:
        """Handle incoming messages from the device."""
        _LOGGER.debug("Received message from device: %s", message)

    @property
    def traits(self) -> Mapping[str, Trait]:
        """Return the traits of the device."""
        return MappingProxyType(self._trait_map)
