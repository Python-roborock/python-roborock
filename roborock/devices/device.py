"""Module for Roborock devices.

This interface is experimental and subject to breaking changes without notice
until the API is stable.
"""

import logging
from abc import ABC
from collections.abc import Callable, Mapping
from typing import Any, TypeVar, cast

from roborock.data import HomeDataDevice, HomeDataProduct
from roborock.roborock_message import RoborockMessage

from .channel import Channel
from .traits import Trait
from .traits.traits_mixin import TraitsMixin

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "RoborockDevice",
]


class RoborockDevice(ABC, TraitsMixin):
    """A generic channel for establishing a connection with a Roborock device.

    Individual channel implementations have their own methods for speaking to
    the device that hide some of the protocol specific complexity, but they
    are still specialized for the device type and protocol.

    Attributes of the device are exposed through traits, which are mixed in
    through the TraitsMixin class. Traits are optional and may not be present
    on all devices.
    """

    def __init__(
        self,
        device_info: HomeDataDevice,
        product: HomeDataProduct,
        channel: Channel,
        trait: Trait,
    ) -> None:
        """Initialize the RoborockDevice.

        The device takes ownership of the channel for communication with the device.
        Use `connect()` to establish the connection, which will set up the appropriate
        protocol channel. Use `close()` to clean up all connections.
        """
        TraitsMixin.__init__(self, trait)
        self._duid = device_info.duid
        self._name = device_info.name
        self._device_info = device_info
        self._product = product
        self._channel = channel
        self._unsub: Callable[[], None] | None = None

    @property
    def duid(self) -> str:
        """Return the device unique identifier (DUID)."""
        return self._duid

    @property
    def name(self) -> str:
        """Return the device name."""
        return self._name

    @property
    def device_info(self) -> HomeDataDevice:
        """Return the device information.

        This includes information specific to the device like its identifier or
        firmware version.
        """
        return self._device_info

    @property
    def product(self) -> HomeDataProduct:
        """Return the device product name.

        This returns product level information such as the model name.
        """
        return self._product

    @property
    def is_connected(self) -> bool:
        """Return whether the device is connected."""
        return self._channel.is_connected

    @property
    def is_local_connected(self) -> bool:
        """Return whether the device is connected locally.

        This can be used to determine if the device is reachable over a local
        network connection, as opposed to a cloud connection. This is useful
        for adjusting behavior like polling frequency.
        """
        return self._channel.is_local_connected

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

    def diagnostic_data(self) -> dict[str, Any]:
        """Return diagnostics information about the device."""
        extra: dict[str, Any] = {}
        if self.v1_properties:
            extra["traits"] = _redact_data(self.v1_properties.as_dict())
        return {
            "device": _redact_data(self.device_info.as_dict()),
            "product": _redact_data(self.product.as_dict()),
            **extra,
        }


T = TypeVar("T")

REDACT_KEYS = {"duid", "localKey", "mac", "bssid"}
REDACTED = "**REDACTED**"


def _redact_data(data: T) -> T | dict[str, Any] | list[Any]:
    """Redact sensitive data in a dict."""
    if not isinstance(data, (Mapping, list)):
        return data

    if isinstance(data, list):
        return cast(T, [_redact_data(item) for item in data])

    redacted = {**data}

    for key, value in redacted.items():
        if key in REDACT_KEYS:
            redacted[key] = REDACTED
        elif isinstance(value, dict):
            redacted[key] = _redact_data(value)
        elif isinstance(value, list):
            redacted[key] = [_redact_data(item) for item in value]

    return redacted
