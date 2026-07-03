"""Data containers for Roborock mower devices."""

from dataclasses import dataclass, field
from typing import Any

from roborock.data.containers import RoborockBase
from roborock.roborock_message import RoborockMowerDataProtocol


@dataclass
class MowerStatus(RoborockBase):
    """Core mower status backed by mower DPS updates."""

    error_code: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.ERROR_CODE})
    battery: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.BATTERY})
    mow_type: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_TYPE})
    mow_state: int | None = field(default=None, metadata={"dps": RoborockMowerDataProtocol.MOW_STATE})
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
