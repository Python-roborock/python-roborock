"""Data container classes for Q10 B01 devices.

Many of these classes use the `field(metadata={"dps": ...})` convention to map
dataclass fields to device Data Points (DPS). This metadata is utilized by the
`UpdatableTrait` helper in `roborock.devices.traits.b01.q10.common` to
automatically update objects from raw device responses.
"""

import base64
from dataclasses import dataclass, field

from ..containers import RoborockBase
from .b01_q10_code_mappings import (
    B01_Q10_DP,
    YXAreaUnit,
    YXBackType,
    YXCarpetCleanType,
    YXCleanLine,
    YXCleanType,
    YXDeviceCleanTask,
    YXDeviceDustCollectionFrequency,
    YXDeviceState,
    YXFanLevel,
    YXWaterLevel,
)

_Q10_CUSTOMER_CLEAN_COUNT_SIZE = 1
_Q10_CUSTOMER_CLEAN_ROOM_BLOCK_SIZE = 26
_Q10_CUSTOMER_CLEAN_NAME_BLOCK_SIZE = 20
_Q10_CUSTOMER_CLEAN_VERTEX_SIZE = 4
_Q10_CUSTOMER_CLEAN_NAME_MAX_LENGTH = _Q10_CUSTOMER_CLEAN_NAME_BLOCK_SIZE - 1
_Q10_SENTINEL_U8 = 0xFF
_Q10_SENTINEL_U16 = 0xFFFF


@dataclass
class dpCleanRecord(RoborockBase):
    op: str
    result: int
    id: str
    data: list


@dataclass
class dpMultiMap(RoborockBase):
    op: str
    result: int
    data: list


@dataclass
class dpGetCarpet(RoborockBase):
    op: str
    result: int
    data: str


@dataclass
class dpSelfIdentifyingCarpet(RoborockBase):
    op: str
    result: int
    data: str


@dataclass
class dpNetInfo(RoborockBase):
    wifi_name: str | None = None
    # "ip_adress" intentionally mirrors the device's "ipAdress" key (sic).
    ip_adress: str | None = None
    mac: str | None = None
    signal: int | None = None

    @property
    def ip_address(self) -> str | None:
        """Correctly-spelled alias for :attr:`ip_adress`."""
        return self.ip_adress


@dataclass
class dpNotDisturbExpand(RoborockBase):
    disturb_dust_enable: int | None = None
    disturb_light: int | None = None
    disturb_resume_clean: int | None = None
    disturb_voice: int | None = None


@dataclass
class dpCurrentCleanRoomIds(RoborockBase):
    room_id_list: list


@dataclass
class dpVoiceVersion(RoborockBase):
    version: int


@dataclass
class dpTimeZone(RoborockBase):
    time_zone_city: str | None = None
    time_zone_sec: int | None = None


@dataclass
class Q10RoomVertex(RoborockBase):
    x_raw: int
    y_raw: int
    x: float
    y: float


@dataclass
class Q10RoomConfig(RoborockBase):
    index: int
    room_id: int
    room_type: int
    clean_order: int | None
    clean_count: int
    clean_type: int | None
    fan_level: int | None
    water_level: int | None
    material: int | None
    clean_line: int | None
    raw_room_name: str
    vertices_num: int
    vertices: list[Q10RoomVertex] = field(default_factory=list)

    @property
    def room_name(self) -> str:
        """Return a normalized user-facing room name."""
        return normalize_q10_room_name(self.raw_room_name)


@dataclass
class Q10RoomsConfig(RoborockBase):
    raw_length: int = 0
    declared_count: int = 0
    rooms: list[Q10RoomConfig] = field(default_factory=list)

    @property
    def parsed_count(self) -> int:
        return len(self.rooms)


def parse_customer_clean_payload(payload_b64: str) -> Q10RoomsConfig:
    """Parse CUSTOMER_CLEAN payload.

    Layout:
    - 1 byte: room count
    - For each room:
      - 26-byte room metadata block
      - 20-byte room name block
      - 1 byte vertex count followed by 4 bytes per vertex (x, y as u16)

    Example room bytes:
    - metadata starts with room id and room type (e.g. ``00 2A 07`` for room id 42)
    - name block starts with length, then UTF-8 bytes (e.g. ``0E rr_living_room``)
    - each vertex is ``x_hi x_lo y_hi y_lo``
    """
    raw = base64.b64decode(payload_b64)
    if not raw:
        return Q10RoomsConfig()

    count = raw[0]
    if not _validate_customer_clean_layout(raw, count):
        return Q10RoomsConfig(raw_length=len(raw), declared_count=count, rooms=[])

    offset = _Q10_CUSTOMER_CLEAN_COUNT_SIZE
    rooms: list[Q10RoomConfig] = []

    for index in range(count):
        room_block = raw[offset : offset + _Q10_CUSTOMER_CLEAN_ROOM_BLOCK_SIZE]
        room_id = int.from_bytes(room_block[0:2], "big", signed=False)
        room_type = room_block[2]
        clean_order = _u16_to_optional(int.from_bytes(room_block[3:5], "big", signed=False))
        clean_count = int.from_bytes(room_block[5:7], "big", signed=False)
        clean_type = _u8_to_optional(room_block[7])
        fan_level = _u8_to_optional(room_block[8])
        water_level = _u8_to_optional(room_block[9])
        material = _u8_to_optional(room_block[10])
        clean_line = _u8_to_optional(room_block[11])
        offset += _Q10_CUSTOMER_CLEAN_ROOM_BLOCK_SIZE

        room_name_bytes = raw[offset : offset + _Q10_CUSTOMER_CLEAN_NAME_BLOCK_SIZE]
        raw_room_name = _decode_q10_room_name(room_name_bytes)
        offset += _Q10_CUSTOMER_CLEAN_NAME_BLOCK_SIZE

        vertices_num = raw[offset]
        offset += 1

        vertices: list[Q10RoomVertex] = []
        for _ in range(vertices_num):
            x_raw = int.from_bytes(raw[offset : offset + 2], "big", signed=False)
            offset += 2
            y_raw = int.from_bytes(raw[offset : offset + 2], "big", signed=False)
            offset += 2
            vertices.append(Q10RoomVertex(x_raw=x_raw, y_raw=y_raw, x=x_raw / 10.0, y=y_raw / 10.0))

        rooms.append(
            Q10RoomConfig(
                index=index,
                room_id=room_id,
                room_type=room_type,
                clean_order=clean_order,
                clean_count=clean_count,
                clean_type=clean_type,
                fan_level=fan_level,
                water_level=water_level,
                material=material,
                clean_line=clean_line,
                raw_room_name=raw_room_name,
                vertices_num=vertices_num,
                vertices=vertices,
            )
        )

    return Q10RoomsConfig(raw_length=len(raw), declared_count=count, rooms=rooms)


def normalize_q10_room_name(room_name: str) -> str:
    """Normalize room names reported by the Q10 firmware.

    Strips leading/trailing whitespace, then converts firmware-prefixed names
    (``rr_<slug>``) into title-cased human-readable strings.

    Examples::

        normalize_q10_room_name("rr_living_room")   # "Living Room"
        normalize_q10_room_name("rr_entrance_hall") # "Entrance Hall"
        normalize_q10_room_name("Kitchen")          # "Kitchen"
        normalize_q10_room_name("rr_")              # "rr_"  (no slug after prefix)
    """
    raw_name = room_name.strip()
    if not raw_name:
        return raw_name
    if raw_name.startswith("rr_"):
        normalized = raw_name[3:].replace("_", " ").strip()
        if not normalized:
            return raw_name
        return " ".join(part.capitalize() for part in normalized.split())
    return raw_name


def _validate_customer_clean_layout(raw: bytes, count: int) -> bool:
    """Ensure the full payload can be parsed before building room objects."""
    offset = _Q10_CUSTOMER_CLEAN_COUNT_SIZE
    for _ in range(count):
        minimum_bytes = (
            _Q10_CUSTOMER_CLEAN_ROOM_BLOCK_SIZE + _Q10_CUSTOMER_CLEAN_NAME_BLOCK_SIZE + _Q10_CUSTOMER_CLEAN_COUNT_SIZE
        )
        if offset + minimum_bytes > len(raw):
            return False

        vertices_num = raw[offset + _Q10_CUSTOMER_CLEAN_ROOM_BLOCK_SIZE + _Q10_CUSTOMER_CLEAN_NAME_BLOCK_SIZE]
        offset += minimum_bytes
        vertex_bytes = vertices_num * _Q10_CUSTOMER_CLEAN_VERTEX_SIZE
        if offset + vertex_bytes > len(raw):
            return False
        offset += vertex_bytes

    return True


def _u8_to_optional(value: int) -> int | None:
    if value == _Q10_SENTINEL_U8:
        return None
    return value


def _u16_to_optional(value: int) -> int | None:
    if value == _Q10_SENTINEL_U16:
        return None
    return value


def _decode_q10_room_name(room_name_bytes: bytes) -> str:
    name_len = room_name_bytes[0]
    if 0 < name_len <= _Q10_CUSTOMER_CLEAN_NAME_MAX_LENGTH:
        return room_name_bytes[1 : 1 + name_len].decode("utf-8", errors="replace")
    return room_name_bytes[1:].split(b"\x00", 1)[0].decode("utf-8", errors="replace")


@dataclass
class Q10Status(RoborockBase):
    """Core vacuum status for Q10 devices.

    Fields are mapped to DPS values using metadata. Objects of this class can be
    automatically updated using the `UpdatableTrait` helper. Settings that have
    their own trait (volume, child lock, do-not-disturb, dust collection,
    network info, consumables) live on those traits instead of here.
    """

    clean_time: int | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_TIME})
    clean_area: int | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_AREA})
    battery: int | None = field(default=None, metadata={"dps": B01_Q10_DP.BATTERY})
    status: YXDeviceState | None = field(default=None, metadata={"dps": B01_Q10_DP.STATUS})
    fan_level: YXFanLevel | None = field(default=None, metadata={"dps": B01_Q10_DP.FAN_LEVEL})
    water_level: YXWaterLevel | None = field(default=None, metadata={"dps": B01_Q10_DP.WATER_LEVEL})
    clean_count: int | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_COUNT})
    total_clean_area: int | None = field(default=None, metadata={"dps": B01_Q10_DP.TOTAL_CLEAN_AREA})
    total_clean_count: int | None = field(default=None, metadata={"dps": B01_Q10_DP.TOTAL_CLEAN_COUNT})
    total_clean_time: int | None = field(default=None, metadata={"dps": B01_Q10_DP.TOTAL_CLEAN_TIME})
    clean_mode: YXCleanType | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_MODE})
    clean_task_type: YXDeviceCleanTask | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_TASK_TYPE})
    back_type: YXBackType | None = field(default=None, metadata={"dps": B01_Q10_DP.BACK_TYPE})
    cleaning_progress: int | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_PROGRESS})
    fault: int | None = field(default=None, metadata={"dps": B01_Q10_DP.FAULT})

    # Additional state reported in the device's full status dump.
    clean_line: YXCleanLine | None = field(default=None, metadata={"dps": B01_Q10_DP.CLEAN_LINE})
    carpet_clean_type: YXCarpetCleanType | None = field(default=None, metadata={"dps": B01_Q10_DP.CARPET_CLEAN_TYPE})
    area_unit: YXAreaUnit | None = field(default=None, metadata={"dps": B01_Q10_DP.AREA_UNIT})
    auto_boost: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.AUTO_BOOST})
    multi_map_switch: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.MULTI_MAP_SWITCH})
    map_save_switch: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.MAP_SAVE_SWITCH})
    recent_clean_record: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.RECENT_CLEAN_RECORD})
    valley_point_charging: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.VALLEY_POINT_CHARGING})
    line_laser_obstacle_avoidance: bool | None = field(
        default=None, metadata={"dps": B01_Q10_DP.LINE_LASER_OBSTACLE_AVOIDANCE}
    )
    # Whether a mop module is attached, and whether "clean along floor direction" is on.
    mop_state: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.MOP_STATE})
    ground_clean: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.GROUND_CLEAN})
    # True while an "add area" / re-clean (the app's draw-a-rectangle "re cleaning")
    # request is in progress; pulses back to False once the robot has the area.
    add_clean_state: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.ADD_CLEAN_STATE})
    robot_country_code: str | None = field(default=None, metadata={"dps": B01_Q10_DP.ROBOT_COUNTRY_CODE})
    time_zone: dpTimeZone | None = field(default=None, metadata={"dps": B01_Q10_DP.TIME_ZONE})

    # TODO(#846): value mappings for these ints are not yet decoded (no app
    # control found / internal / constant); keep as int until reverse-engineered.
    breakpoint_clean: int | None = field(default=None, metadata={"dps": B01_Q10_DP.BREAKPOINT_CLEAN})
    timer_type: int | None = field(default=None, metadata={"dps": B01_Q10_DP.TIMER_TYPE})
    user_plan: int | None = field(default=None, metadata={"dps": B01_Q10_DP.USER_PLAN})
    robot_type: int | None = field(default=None, metadata={"dps": B01_Q10_DP.ROBOT_TYPE})

    # DEPRECATED: consumable/accessory remaining-life now lives on the
    # ``Q10Consumable`` trait. These aliases are kept here for backwards
    # compatibility and will be removed in a follow-up release. See PR #846.
    main_brush_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.MAIN_BRUSH_LIFE})
    side_brush_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.SIDE_BRUSH_LIFE})
    filter_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.FILTER_LIFE})
    sensor_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.SENSOR_LIFE})


@dataclass
class SoundVolume(RoborockBase):
    """Speaker volume read-model (0-100)."""

    volume: int | None = field(default=None, metadata={"dps": B01_Q10_DP.VOLUME})


@dataclass
class ChildLock(RoborockBase):
    """Child-lock read-model."""

    child_lock: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.CHILD_LOCK})


@dataclass
class DoNotDisturb(RoborockBase):
    """Do Not Disturb read-model."""

    not_disturb: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.NOT_DISTURB})
    not_disturb_expand: dpNotDisturbExpand | None = field(default=None, metadata={"dps": B01_Q10_DP.NOT_DISTURB_EXPAND})


@dataclass
class DustCollection(RoborockBase):
    """Dock auto-empty (dust collection) read-model."""

    dust_switch: bool | None = field(default=None, metadata={"dps": B01_Q10_DP.DUST_SWITCH})
    dust_setting: YXDeviceDustCollectionFrequency | None = field(
        default=None, metadata={"dps": B01_Q10_DP.DUST_SETTING}
    )


@dataclass
class Q10Consumable(RoborockBase):
    """Consumable / accessory remaining-life read-model.

    Named with a ``Q10`` prefix to avoid shadowing the v1 ``Consumable`` when both
    are star-imported into the ``roborock.data`` namespace.
    """

    main_brush_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.MAIN_BRUSH_LIFE})
    side_brush_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.SIDE_BRUSH_LIFE})
    filter_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.FILTER_LIFE})
    sensor_life: int | None = field(default=None, metadata={"dps": B01_Q10_DP.SENSOR_LIFE})


@dataclass
class Q10NetworkInfo(RoborockBase):
    """Network information read-model.

    Named with a ``Q10`` prefix to avoid shadowing the v1 ``NetworkInfo`` when both
    are star-imported into the ``roborock.data`` namespace.
    """

    net_info: dpNetInfo | None = field(default=None, metadata={"dps": B01_Q10_DP.NET_INFO})
