"""Module for Roborock devices.

This interface is experimental and subject to breaking changes without notice
until the API is stable.
"""

import enum
import logging
from collections.abc import Callable
from functools import cached_property

from roborock.containers import (
    HomeDataDevice,
    HomeDataProduct,
    ModelStatus,
    S7MaxVStatus,
    Status,
    UserData,
)
from roborock.roborock_message import RoborockMessage
from roborock.roborock_typing import RoborockCommand

from .v1_channel import V1Channel

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "RoborockDevice",
    "DeviceVersion",
]


class DeviceVersion(enum.StrEnum):
    """Enum for device versions."""

    V1 = "1.0"
    A01 = "A01"
    UNKNOWN = "unknown"


class RoborockDevice:
    """Unified Roborock device class with automatic connection setup."""

    def __init__(
        self,
        user_data: UserData,
        device_info: HomeDataDevice,
        product_info: HomeDataProduct,
        v1_channel: V1Channel,
    ) -> None:
        """Initialize the RoborockDevice.

        The device takes ownership of the V1 channel for communication with the device.
        Use `connect()` to establish the connection, which will set up the appropriate
        protocol channel. Use `close()` to clean up all connections.
        """
        self._user_data = user_data
        self._device_info = device_info
        self._product_info = product_info
        self._v1_channel = v1_channel
        self._unsub: Callable[[], None] | None = None

    @property
    def duid(self) -> str:
        """Return the device unique identifier (DUID)."""
        return self._device_info.duid

    @property
    def name(self) -> str:
        """Return the device name."""
        return self._device_info.name

    @cached_property
    def device_version(self) -> str:
        """Return the device version.

        At the moment this is a simple check against the product version (pv) of the device
        and used as a placeholder for upcoming functionality for devices that will behave
        differently based on the version and capabilities.
        """
        if self._device_info.pv == DeviceVersion.V1.value:
            return DeviceVersion.V1
        elif self._device_info.pv == DeviceVersion.A01.value:
            return DeviceVersion.A01
        _LOGGER.warning(
            "Unknown device version %s for device %s, using default UNKNOWN",
            self._device_info.pv,
            self._device_info.name,
        )
        return DeviceVersion.UNKNOWN

    @property
    def is_connected(self) -> bool:
        """Return whether the device is connected."""
        return self._v1_channel.is_mqtt_connected or self._v1_channel.is_local_connected

    async def connect(self) -> None:
        """Connect to the device using the appropriate protocol channel."""
        if self._unsub:
            raise ValueError("Already connected to the device")
        self._unsub = await self._v1_channel.subscribe(self._on_message)
        _LOGGER.info("Connected to V1 device %s", self.name)

    async def close(self) -> None:
        """Close all connections to the device."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    def _on_message(self, message: RoborockMessage) -> None:
        """Handle incoming messages from the device."""
        _LOGGER.debug("Received message from device: %s", message)

    async def get_status(self) -> Status:
        """Get the current status of the device.

        This is a placeholder command and will likely be changed/moved in the future.
        """
        status_type: type[Status] = ModelStatus.get(self._product_info.model, S7MaxVStatus)
        return await self._v1_channel.rpc_channel.send_command(RoborockCommand.GET_STATUS, response_type=status_type)
