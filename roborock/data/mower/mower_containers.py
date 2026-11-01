"""Data containers for Roborock mower devices."""

from dataclasses import dataclass, field, fields
from typing import Any, Self

from roborock.data.containers import RoborockBase
from roborock.roborock_message import RoborockMowerDataProtocol

from .mower_code_mappings import (
    MowerAfsStatus,
    MowerChargeState,
    MowerChargeType,
    MowerConfMode,
    MowerDetailState,
    MowerDockState,
    MowerEffMode,
    MowerErrorCode,
    MowerFcState,
    MowerMappingState,
    MowerMappingType,
    MowerMowType,
    MowerNetworkChannel,
    MowerOffDockNoTaskStatus,
    MowerOfflineStatus,
    MowerOtaState,
    MowerPattern,
    MowerPendType,
    MowerRemoteState,
    MowerStartType,
)

__all__ = [
    "MowerGpsCoordinate",
    "MowerStatus",
]


@dataclass
class MowerGpsCoordinate(RoborockBase):
    """Mower GPS position."""

    latitude: float | None = None
    longitude: float | None = None


@dataclass
class MowerStatus(RoborockBase):
    """Core mower status backed by mower DPS updates (data points 120-145)."""

    error_code: MowerErrorCode | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.ERROR_CODE})
    battery: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.BATTERY})
    mow_type: MowerMowType | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_TYPE})
    mow_state: MowerDetailState | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_STATE})
    mapping_type: MowerMappingType | None = field(
        default=None, metadata={"dps": RoborockMowerDataProtocol.MAPPING_TYPE}
    )
    mapping_state: MowerMappingState | None = field(
        default=None, metadata={"dps": RoborockMowerDataProtocol.MAPPING_STATE}
    )
    ota_state: MowerOtaState | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.OTA_STATE})
    charge_state: MowerChargeState | None = field(
        default=None, metadata={"dps": RoborockMowerDataProtocol.CHARGE_STATE}
    )
    dock_state: MowerDockState | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.DOCK_STATE})
    charge_type: MowerChargeType | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.CHARGE_TYPE})
    pend_type: MowerPendType | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.PEND_TYPE})
    remote_state: MowerRemoteState | None = field(
        default=None, metadata={"dps": RoborockMowerDataProtocol.REMOTE_STATE}
    )
    mow_start_type: MowerStartType | None = field(
        default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_START_TYPE}
    )
    mow_eff_mode: MowerEffMode | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_EFF_MODE})
    mow_height: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_HEIGHT})
    mow_direction_angle: int | None = field(
        default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_DIRECTION_ANGLE}
    )
    mow_pattern: MowerPattern | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_PATTERN})
    mow_conf_mode: MowerConfMode | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_CONF_MODE})
    offline_status: MowerOfflineStatus | None = field(
        default=None, metadata={"dps": RoborockMowerDataProtocol.OFFLINE_STATUS}
    )
    mow_progress: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_PROGRESS})
    blade_lifespan: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.BLADE_LIFESPAN})
    fc_state: MowerFcState | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.FC_STATE})
    gps_coordinate: MowerGpsCoordinate | None = field(
        default=None, metadata={"dps": RoborockMowerDataProtocol.GPS_COORDINATE}
    )
    off_dock_no_task_status: MowerOffDockNoTaskStatus | None = field(
        default=None, metadata={"dps": RoborockMowerDataProtocol.OFF_DOCK_NO_TASK_STATUS}
    )
    afs_status: MowerAfsStatus | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.AFS_STATUS})
    network_channel: MowerNetworkChannel | None = field(
        default=None, metadata={"dps": RoborockMowerDataProtocol.NETWORK_CHANNEL}
    )

    @classmethod
    def from_dps(cls, dps: dict[int | str, Any] | None) -> Self:
        """Create typed status from integer or string DPS keys."""
        field_by_dps = {
            int(field_info.metadata["dps"]): field_info.name
            for field_info in fields(cls)
            if "dps" in field_info.metadata
        }
        values: dict[str, Any] = {}
        for key, value in (dps or {}).items():
            try:
                dps_id = int(key)
            except (TypeError, ValueError):
                continue
            if field_name := field_by_dps.get(dps_id):
                values[field_name] = value
        return cls.from_dict(values)
