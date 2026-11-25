"""Traits for the collision avoidance setting."""

from roborock.data import CollisionAvoidanceMode, CollisionAvoidStatus
from roborock.devices.traits.v1 import common
from roborock.exceptions import RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand

_STATUS_PARAM = "status"


class CollisionAvoidanceTrait(CollisionAvoidStatus, common.V1TraitMixin, common.RoborockSwitchBase):
    """Trait for turning collision avoidance on or off.

    Not created for devices with two-level collision avoidance, which get
    ``CollisionAvoidanceModeTrait`` instead. The same value is also reported
    as ``collision_avoid_status`` on the device status.
    """

    command = RoborockCommand.GET_COLLISION_AVOID_STATUS
    converter = common.DefaultConverter(CollisionAvoidStatus)
    requires_feature = "is_avoid_collision_supported"

    @property
    def is_on(self) -> bool:
        """Return whether collision avoidance is enabled."""
        return self.status == 1

    async def enable(self) -> None:
        """Enable collision avoidance."""
        await self.rpc_channel.send_command(RoborockCommand.SET_COLLISION_AVOID_STATUS, params={_STATUS_PARAM: 1})
        # Optimistic update to avoid an extra refresh
        self.status = 1

    async def disable(self) -> None:
        """Disable collision avoidance."""
        await self.rpc_channel.send_command(RoborockCommand.SET_COLLISION_AVOID_STATUS, params={_STATUS_PARAM: 0})
        # Optimistic update to avoid an extra refresh
        self.status = 0


class CollisionAvoidanceModeTrait(CollisionAvoidStatus, common.V1TraitMixin):
    """Trait for the two-level collision avoidance mode.

    The raw value is kept in ``status``; values without a named mode are
    reported as ``CollisionAvoidanceMode.unknown``.
    """

    command = RoborockCommand.GET_COLLISION_AVOID_STATUS
    converter = common.DefaultConverter(CollisionAvoidStatus)
    requires_feature = "is_two_gears_no_collision_supported"

    @property
    def mode(self) -> CollisionAvoidanceMode | None:
        """Return the current collision avoidance mode."""
        if self.status is None:
            return None
        return CollisionAvoidanceMode(self.status)

    async def set_collision_avoidance_mode(self, mode: CollisionAvoidanceMode) -> None:
        """Set the collision avoidance mode."""
        if mode is CollisionAvoidanceMode.unknown:
            raise RoborockUnsupportedFeature(f"Collision avoidance mode {mode.name!r} is not supported")
        await self.rpc_channel.send_command(
            RoborockCommand.SET_COLLISION_AVOID_STATUS, params={_STATUS_PARAM: mode.value}
        )
        # Optimistic update to avoid an extra refresh
        self.status = mode.value
