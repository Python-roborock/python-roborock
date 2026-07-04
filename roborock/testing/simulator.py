"""Base stateful device firmware simulator for python-roborock testing.

This module defines `RoborockDeviceSimulator` which intercepts plaintext JSON RPC messages
sent over simulated channels, process them through a local state engine, update internal
variables, and write responses back to client subscribers.
"""

import logging

from roborock.data import HomeDataDevice, HomeDataProduct, RoborockCategory
from roborock.roborock_message import RoborockMessage
from roborock.testing.channel import FakeChannel

_LOGGER = logging.getLogger(__name__)

# Shared authentication key constants
DEFAULT_LOCAL_KEY = "fake_localkey_16bytes"
DEFAULT_KEY_T = "qiCNieZa"
DEFAULT_PRODUCT_ID = "product-id-123"


class RoborockDeviceSimulator:
    """Base class for stateful device firmware simulators.

    It sets up an MQTT fake transport channel (and optionally a local channel),
    intercepts published requests, and routes them to `_handle_publish` to
    simulate real device response.

    Not all protocols support local connections. V1 devices use both MQTT and
    local channels, while A01/B01 devices use MQTT only. Subclasses that need
    a local channel should set ``has_local_channel=True`` (the default for
    backward compatibility with V1 simulators).

    Caller API
    ----------
    Subclasses (like ``RoborockVacuumSimulator``) provide the high-level
    interface (state attributes, ``trigger_push_update()``, etc.), but callers
    can also reach into the underlying channels for low-level inspection:

    - **Inspect published messages**: ``simulator.mqtt_channel.published_messages``
      (and ``simulator.local_channel.published_messages`` for V1) contain every
      ``RoborockMessage`` that the client sent through each transport.
    - **Inject transport failures**: Set
      ``simulator.mqtt_channel.publish_side_effect = RoborockException(...)``
      to make the next publish raise, simulating a network error.
    - **Modify device identity**: Override ``simulator.device_info`` or
      ``simulator.product`` before registering with ``FakeRoborockCloud`` to
      control the device metadata returned during discovery.
    """

    def __init__(
        self,
        duid: str = "fake_duid",
        device_info: HomeDataDevice | None = None,
        product: HomeDataProduct | None = None,
        has_local_channel: bool = True,
    ):
        self.duid = duid
        self.product = product or HomeDataProduct(
            id=DEFAULT_PRODUCT_ID,
            name="Roborock Vacuum",
            model="roborock.vacuum.s7",
            category=RoborockCategory.VACUUM,
        )
        self.device_info = device_info or HomeDataDevice(
            duid=self.duid,
            name=f"Vacuum {self.duid}",
            local_key=DEFAULT_LOCAL_KEY,
            product_id=self.product.id,
            sn="fake_serial_number",
            pv="1.0",
        )

        # MQTT channel is always present — all protocols use it.
        self.mqtt_channel = FakeChannel(is_local=False)
        self.mqtt_channel.publish.side_effect = self._handle_mqtt_publish

        # Local channel is only used by V1 devices. A01/B01 (MQTT-only)
        # simulators should pass has_local_channel=False.
        self.local_channel: FakeChannel | None = None
        if has_local_channel:
            self.local_channel = FakeChannel(is_local=True)
            self.local_channel.publish.side_effect = self._handle_local_publish

    async def _handle_local_publish(self, message: RoborockMessage) -> None:
        assert self.local_channel is not None
        self.local_channel.published_messages.append(message)
        if self.local_channel.publish_side_effect:
            raise self.local_channel.publish_side_effect
        await self._handle_publish(message, self.local_channel)

    async def _handle_mqtt_publish(self, message: RoborockMessage) -> None:
        self.mqtt_channel.published_messages.append(message)
        if self.mqtt_channel.publish_side_effect:
            raise self.mqtt_channel.publish_side_effect
        await self._handle_publish(message, self.mqtt_channel)

    async def _handle_publish(self, message: RoborockMessage, channel: FakeChannel) -> None:
        """To be overridden by subclasses to route commands."""
        raise NotImplementedError("Subclasses must implement _handle_publish")

    def connect(self) -> None:
        if self.local_channel is not None:
            self.local_channel._is_connected = True
        self.mqtt_channel._is_connected = True

    def close(self) -> None:
        if self.local_channel is not None:
            self.local_channel._is_connected = False
        self.mqtt_channel._is_connected = False
