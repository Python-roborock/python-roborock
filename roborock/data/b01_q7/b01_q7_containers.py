from dataclasses import dataclass, field

from ..containers import RoborockBase
from .b01_q7_code_mappings import B01Fault, SCWindMapping, WorkModeMapping, WorkStatusMapping


@dataclass
class NetStatus(RoborockBase):
    """Represents the network status of the device."""

    rssi: str
    loss: int
    ping: int
    ip: str
    mac: str
    ssid: str
    frequency: int
    bssid: str


@dataclass
class OrderTotal(RoborockBase):
    """Represents the order total information."""

    total: int
    enable: int


@dataclass
class Privacy(RoborockBase):
    """Represents the privacy settings of the device."""

    ai_recognize: int
    dirt_recognize: int
    pet_recognize: int
    carpet_turbo: int
    carpet_avoid: int
    carpet_show: int
    map_uploads: int
    ai_agent: int
    ai_avoidance: int
    record_uploads: int
    along_floor: int
    auto_upgrade: int


@dataclass
class PvCharging(RoborockBase):
    """Represents the photovoltaic charging status."""

    status: int
    begin_time: int
    end_time: int


@dataclass
class Recommend(RoborockBase):
    """Represents cleaning recommendations."""

    sill: int
    wall: int
    room_id: list[int] = field(default_factory=list)


@dataclass
class B01Props(RoborockBase):
    """
    Represents the complete properties and status for a Roborock B01 model.
    This dataclass is generated based on the device's status JSON object.
    """

    status: WorkStatusMapping | None = None
    fault: B01Fault | None = None
    wind: SCWindMapping | None = None
    water: int | None = None
    mode: int | None = None
    quantity: int | None = None
    alarm: int | None = None
    volume: int | None = None
    hypa: int | None = None
    main_brush: int | None = None
    side_brush: int | None = None
    mop_life: int | None = None
    main_sensor: int | None = None
    net_status: NetStatus | None = None
    repeat_state: int | None = None
    tank_state: int | None = None
    sweep_type: int | None = None
    clean_path_preference: int | None = None
    cloth_state: int | None = None
    time_zone: int | None = None
    time_zone_info: str | None = None
    language: int | None = None
    cleaning_time: int | None = None
    real_clean_time: int | None = None
    cleaning_area: int | None = None
    custom_type: int | None = None
    sound: int | None = None
    work_mode: WorkModeMapping | None = None
    station_act: int | None = None
    charge_state: int | None = None
    current_map_id: int | None = None
    map_num: int | None = None
    dust_action: int | None = None
    quiet_is_open: int | None = None
    quiet_begin_time: int | None = None
    quiet_end_time: int | None = None
    clean_finish: int | None = None
    voice_type: int | None = None
    voice_type_version: int | None = None
    order_total: OrderTotal | None = None
    build_map: int | None = None
    privacy: Privacy | None = None
    dust_auto_state: int | None = None
    dust_frequency: int | None = None
    child_lock: int | None = None
    multi_floor: int | None = None
    map_save: int | None = None
    light_mode: int | None = None
    green_laser: int | None = None
    dust_bag_used: int | None = None
    order_save_mode: int | None = None
    manufacturer: str | None = None
    back_to_wash: int | None = None
    charge_station_type: int | None = None
    pv_cut_charge: int | None = None
    pv_charging: PvCharging | None = None
    serial_number: str | None = None
    recommend: Recommend | None = None
    add_sweep_status: int | None = None
