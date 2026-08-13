"""Data containers for Roborock mower devices."""

from dataclasses import dataclass, field, fields
from typing import Any, Self

from roborock.data.containers import RoborockBase
from roborock.roborock_message import RoborockMowerDataProtocol

from .mower_code_mappings import RoborockMowerStateCode


@dataclass
class MowerStatus(RoborockBase):
    """Core mower status backed by mower DPS updates."""

    error_code: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.ERROR_CODE})
    battery: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.BATTERY})
    mow_type: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_TYPE})
    mow_state: RoborockMowerStateCode | None = field(
        default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_STATE}
    )
    mapping_type: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MAPPING_TYPE})
    mapping_state: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MAPPING_STATE})
    ota_state: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.OTA_STATE})
    charge_state: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.CHARGE_STATE})
    dock_state: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.DOCK_STATE})
    charge_type: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.CHARGE_TYPE})
    pend_type: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.PEND_TYPE})
    remote_state: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.REMOTE_STATE})
    mow_start_type: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_START_TYPE})
    mow_eff_mode: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_EFF_MODE})
    mow_height: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_HEIGHT})
    mow_direction_angle: int | None = field(
        default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_DIRECTION_ANGLE}
    )
    mow_pattern: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_PATTERN})
    mow_conf_mode: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_CONF_MODE})
    offline_status: Any | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.OFFLINE_STATUS})
    mow_progress: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_PROGRESS})
    blade_lifespan: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.BLADE_LIFESPAN})
    fc_state: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.FC_STATE})
    gps_coordinate: Any | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.GPS_COORDINATE})
    off_dock_no_task_status: int | None = field(
        default=None, metadata={"dps": RoborockMowerDataProtocol.OFF_DOCK_NO_TASK_STATUS}
    )
    afs_status: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.AFS_STATUS})
    network_channel: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.NETWORK_CHANNEL})

    @classmethod
    def from_dps(cls, dps: dict[int | str, Any] | None) -> Self:
        """Create mower status from raw DPS data.

        Cloud snapshots use string DPS keys while decoded MQTT messages may use
        integer keys. Unknown and malformed keys are ignored.
        """
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
