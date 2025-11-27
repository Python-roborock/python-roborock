"""Module for Roborock devices.

This interface is experimental and subject to breaking changes without notice
until the API is stable.
"""

import asyncio
import datetime
import logging
from abc import ABC
from collections.abc import Callable, Mapping
from typing import Any, TypeVar, cast

from roborock.data import HomeDataDevice, HomeDataProduct
from roborock.exceptions import RoborockException
from roborock.roborock_message import RoborockMessage

from .channel import Channel
from .traits import Trait
from .traits.traits_mixin import TraitsMixin

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "RoborockDevice",
]

# Exponential backoff parameters
MIN_BACKOFF_INTERVAL = datetime.timedelta(seconds=10)
MAX_BACKOFF_INTERVAL = datetime.timedelta(minutes=30)
BACKOFF_MULTIPLIER = 1.5


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
        self._connect_task: asyncio.Task[None] | None = None
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

    def start_connect(self) -> None:
        """Start a background task to connect to the device.

        This will attempt to connect to the device using the appropriate protocol
        channel. If the connection fails, it will retry with exponential backoff.

        Once connected, the device will remain connected until `close()` is
        called. The device will automatically attempt to reconnect if the connection
        is lost.
        """

        async def connect_loop() -> None:
            backoff = MIN_BACKOFF_INTERVAL
            try:
                while True:
                    try:
                        await self.connect()
                        return
                    except RoborockException as e:
                        _LOGGER.info("Failed to connect to device %s: %s", self.name, e)
                        _LOGGER.info(
                            "Retrying connection to device %s in %s seconds", self.name, backoff.total_seconds()
                        )
                        await asyncio.sleep(backoff.total_seconds())
                        backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF_INTERVAL)
            except asyncio.CancelledError:
                _LOGGER.info("connect_loop for device %s was cancelled", self.name)
                # Clean exit on cancellation
                return

        self._connect_task = asyncio.create_task(connect_loop())

    async def connect(self) -> None:
        """Connect to the device using the appropriate protocol channel."""
        if self._unsub:
            raise ValueError("Already connected to the device")
        unsub = await self._channel.subscribe(self._on_message)
        _LOGGER.info("Connected to V1 device %s", self.name)
        if self.v1_properties is not None:
            try:
                await self.v1_properties.discover_features()
            except RoborockException:
                unsub()
                raise
        self._unsub = unsub

    async def close(self) -> None:
        """Close all connections to the device."""
        if self._connect_task:
            self._connect_task.cancel()
            try:
                await self._connect_task
            except asyncio.CancelledError:
                pass
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

REDACT_KEYS = {"duid", "localKey", "mac", "bssid", "sn", "ip"}
REDACTED = "**REDACTED**"


def _redact_data(data: T) -> T | dict[str, Any]:
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
