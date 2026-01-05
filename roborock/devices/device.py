"""Module for Roborock devices.

This interface is experimental and subject to breaking changes without notice
until the API is stable.
"""

import asyncio
import datetime
import json
import logging
from abc import ABC
from collections.abc import Callable
from typing import Any

from roborock.callbacks import CallbackList
from roborock.data import HomeDataDevice, HomeDataProduct, RoborockErrorCode, RoborockStateCode
from roborock.diagnostics import redact_device_data
from roborock.exceptions import RoborockException
from roborock.roborock_message import (
    ROBOROCK_DATA_STATUS_PROTOCOL,
    RoborockDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
)
from roborock.util import RoborockLoggerAdapter

from .traits import Trait
from .traits.traits_mixin import TraitsMixin
from .transport.channel import Channel

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "DeviceReadyCallback",
    "RoborockDevice",
]

# Exponential backoff parameters
MIN_BACKOFF_INTERVAL = datetime.timedelta(seconds=10)
MAX_BACKOFF_INTERVAL = datetime.timedelta(minutes=30)
BACKOFF_MULTIPLIER = 1.5
# Give time for the NETWORK_INFO fetch and V1 hello attempt
# and potential fallback to L01.
START_ATTEMPT_TIMEOUT = datetime.timedelta(seconds=15)


DeviceReadyCallback = Callable[["RoborockDevice"], None]


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
        self._logger = RoborockLoggerAdapter(duid=self._duid, logger=_LOGGER)
        self._name = device_info.name
        self._device_info = device_info
        self._product = product
        self._channel = channel
        self._connect_task: asyncio.Task[None] | None = None
        self._unsub: Callable[[], None] | None = None
        self._ready_callbacks = CallbackList["RoborockDevice"]()
        self._has_connected = False

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

    def add_ready_callback(self, callback: DeviceReadyCallback) -> Callable[[], None]:
        """Add a callback to be notified when the device is ready.

        A device is considered ready when it has successfully connected. It may go
        offline later, but this callback will only be called once when the device
        first connects.

        The callback will be called immediately if the device has already previously
        connected.
        """
        remove = self._ready_callbacks.add_callback(callback)
        if self._has_connected:
            callback(self)

        return remove

    async def start_connect(self) -> None:
        """Start a background task to connect to the device.

        This will give a moment for the first connection attempt to start so
        that the device will have connections established -- however, this will
        never directly fail.

        If the connection fails, it will retry in the background with
        exponential backoff.

        Once connected, the device will remain connected until `close()` is
        called. The device will automatically attempt to reconnect if the connection
        is lost.
        """
        # The future will be set to True if the first attempt succeeds, False if
        # it fails, or an exception if an unexpected error occurs.
        # We use this to wait a short time for the first attempt to complete. We
        # don't actually care about the result, just that we waited long enough.
        start_attempt: asyncio.Future[bool] = asyncio.Future()

        async def connect_loop() -> None:
            try:
                backoff = MIN_BACKOFF_INTERVAL
                while True:
                    try:
                        await self.connect()
                        if not start_attempt.done():
                            start_attempt.set_result(True)
                        self._has_connected = True
                        self._ready_callbacks(self)
                        return
                    except RoborockException as e:
                        if not start_attempt.done():
                            start_attempt.set_result(False)
                        self._logger.info("Failed to connect (retry %s): %s", backoff.total_seconds(), e)
                        await asyncio.sleep(backoff.total_seconds())
                        backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF_INTERVAL)
                    except Exception as e:  # pylint: disable=broad-except
                        if not start_attempt.done():
                            start_attempt.set_exception(e)
                        self._logger.exception("Uncaught error during connect: %s", e)
                        return
            except asyncio.CancelledError:
                self._logger.debug("connect_loop was cancelled for device %s", self.duid)
            finally:
                if not start_attempt.done():
                    start_attempt.set_result(False)

        self._connect_task = asyncio.create_task(connect_loop())

        try:
            async with asyncio.timeout(START_ATTEMPT_TIMEOUT.total_seconds()):
                await start_attempt
        except TimeoutError:
            self._logger.debug("Initial connection attempt took longer than expected, will keep trying in background")

    async def connect(self) -> None:
        """Connect to the device using the appropriate protocol channel."""
        if self._unsub:
            raise ValueError("Already connected to the device")
        unsub = await self._channel.subscribe(self._on_message)
        if self.v1_properties is not None:
            try:
                await self.v1_properties.discover_features()
            except RoborockException:
                unsub()
                raise
        self._logger.info("Connected to device")
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
        """Handle incoming messages from the device.

        Note: Protocol updates (data points) are only sent via cloud/MQTT, not local connection.
        """
        self._logger.debug("Received message from device: %s", message)
        if self.v1_properties is None:
            # Ensure we are only doing below logic for set-up V1 devices.
            return

        # Only process messages that can contain protocol updates
        # RPC_RESPONSE (102), GENERAL_REQUEST (4), and GENERAL_RESPONSE (5)
        if message.protocol not in {
            RoborockMessageProtocol.RPC_RESPONSE,
            RoborockMessageProtocol.GENERAL_RESPONSE,
        }:
            return

        if not message.payload:
            return

        try:
            payload = json.loads(message.payload.decode())
            dps = payload.get("dps", {})

            if not dps:
                return

            # Process each data point in the message
            for data_point_number, data_point in dps.items():
                # Skip RPC responses (102) as they're handled by the RPC channel
                if data_point_number == "102":
                    continue

                try:
                    data_protocol = RoborockDataProtocol(int(data_point_number))
                    self._logger.debug(f"Got device update for {data_protocol.name}: {data_point}")
                    self._handle_protocol_update(data_protocol, data_point)
                except ValueError:
                    # Unknown protocol number
                    self._logger.debug(
                        f"Got unknown data protocol {data_point_number}, data: {data_point}. "
                        f"This may allow for faster updates in the future."
                    )
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as ex:
            self._logger.debug(f"Failed to parse protocol message: {ex}")

    def _handle_protocol_update(self, protocol: RoborockDataProtocol, data_point: Any) -> None:
        """Handle a protocol update for a specific data protocol.

        Args:
            protocol: The data protocol number.
            data_point: The data value for this protocol.
        """
        # Handle status protocol updates
        if protocol in ROBOROCK_DATA_STATUS_PROTOCOL and self.v1_properties and self.v1_properties.status:
            # Update the specific field in the status trait
            match protocol:
                case RoborockDataProtocol.ERROR_CODE:
                    self.v1_properties.status.error_code = RoborockErrorCode(data_point)
                case RoborockDataProtocol.STATE:
                    self.v1_properties.status.state = RoborockStateCode(data_point)
                case RoborockDataProtocol.BATTERY:
                    self.v1_properties.status.battery = data_point
                case RoborockDataProtocol.CHARGE_STATUS:
                    self.v1_properties.status.charge_status = data_point
                case _:
                    # There is also fan power and water box mode, but for now those are skipped
                    return

            self._logger.debug("Updated status.%s to %s", protocol.name.lower(), data_point)
            self.v1_properties.status.notify_update()

    def diagnostic_data(self) -> dict[str, Any]:
        """Return diagnostics information about the device."""
        extra: dict[str, Any] = {}
        if self.v1_properties:
            extra["traits"] = redact_device_data(self.v1_properties.as_dict())
        return {
            "device": redact_device_data(self.device_info.as_dict()),
            "product": redact_device_data(self.product.as_dict()),
            **extra,
        }
