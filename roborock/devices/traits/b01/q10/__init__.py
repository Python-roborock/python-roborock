"""Traits for Q10 B01 devices."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.devices.b01_q10_channel import get_b01_q10_router
from roborock.devices.mqtt_channel import MqttChannel
from roborock.devices.traits import Trait
from roborock.roborock_message import RoborockMessage

from .child_lock import Q10ChildLockTrait
from .command import Q10CommandTrait
from .consumable import Q10ConsumableTrait
from .dnd import Q10DNDTrait
from .status import Q10StatusTrait
from .volume import Q10VolumeTrait

__all__ = [
    "Q10PropertiesApi",
]


@dataclass
class Q10PropertiesApi(Trait):
    """API for interacting with Q10 (B01) devices."""

    status: Q10StatusTrait
    consumables: Q10ConsumableTrait
    command: Q10CommandTrait
    volume: Q10VolumeTrait
    child_lock: Q10ChildLockTrait
    dnd: Q10DNDTrait

    def __init__(self, channel: MqttChannel) -> None:
        """Initialize the Q10 properties API."""
        self._channel = channel
        self._router = get_b01_q10_router(channel)
        self._remove_prop_cb: Callable[[], None] | None = self._router.add_prop_update_callback(self._on_prop_update)
        self.status = Q10StatusTrait()
        self.consumables = Q10ConsumableTrait()
        self.command = Q10CommandTrait()
        self.volume = Q10VolumeTrait()
        self.child_lock = Q10ChildLockTrait()
        self.dnd = Q10DNDTrait()

        # Set the channel on all traits
        for trait in [
            self.status,
            self.consumables,
            self.command,
            self.volume,
            self.child_lock,
            self.dnd,
        ]:
            trait.set_channel(channel)

    def on_message(self, message: RoborockMessage) -> None:
        """Receive inbound MQTT messages and route them asynchronously."""
        self._router.feed(message)

    def close(self) -> None:
        """Clean up background routing tasks and callbacks."""
        if self._remove_prop_cb:
            self._remove_prop_cb()
            self._remove_prop_cb = None
        self._router.close()

    async def refresh(self) -> None:
        """Request all DPs from the device (fire-and-forget).

        Q10 devices push DP updates asynchronously and often in multiple different payloads
        `B01Q10MessageRouter` will apply those updates via `_on_prop_update` as they arrive.
        """
        await self.command.send_dp(B01_Q10_DP.REQUETDPS, 1)

    def _on_prop_update(self, dps: dict[int, Any]) -> None:
        """Apply a prop update DP payload to all known traits."""
        self.status.update_from_dps(dps)
        self.consumables.update_from_dps(dps)
        self.volume.update_from_dps(dps)
        self.child_lock.update_from_dps(dps)
        self.dnd.update_from_dps(dps)


def create(channel: MqttChannel) -> Q10PropertiesApi:
    """Create traits for Q10 devices."""
    return Q10PropertiesApi(channel)
