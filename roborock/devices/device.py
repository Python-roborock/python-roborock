"""Module for Roborock devices.

This interface is experimental and subject to breaking changes without notice
until the API is stable.
"""

import enum
import logging
from functools import cached_property

from roborock.containers import HomeDataDevice, HomeDataProduct, UserData

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

    def __init__(self, user_data: UserData, device_info: HomeDataDevice, product_info: HomeDataProduct) -> None:
        """Initialize the RoborockDevice with device info, user data, and capabilities."""
        self._user_data = user_data
        self._device_info = device_info
        self._product_info = product_info

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
        if self._device_info.pv == "1.0":
            return DeviceVersion.V1
        elif self._device_info.pv in ["A1", "A01"]:
            return DeviceVersion.A01
        _LOGGER.warning(
            "Unknown device version %s for device %s, using default UNKNOWN",
            self._device_info.pv,
            self._device_info.name,
        )
        return DeviceVersion.UNKNOWN
