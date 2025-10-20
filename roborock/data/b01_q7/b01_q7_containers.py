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

    status: WorkStatusMapping
    fault: B01Fault
    wind: SCWindMapping
    water: int
    mode: int
    quantity: int
    alarm: int
    volume: int
    hypa: int
    main_brush: int
    side_brush: int
    mop_life: int
    main_sensor: int
    net_status: NetStatus
    repeat_state: int
    tank_state: int
    sweep_type: int
    clean_path_preference: int
    cloth_state: int
    time_zone: int
    time_zone_info: str
    language: int
    cleaning_time: int
    real_clean_time: int
    cleaning_area: int
    custom_type: int
    sound: int
    work_mode: WorkModeMapping
    station_act: int
    charge_state: int
    current_map_id: int
    map_num: int
    dust_action: int
    quiet_is_open: int
    quiet_begin_time: int
    quiet_end_time: int
    clean_finish: int
    voice_type: int
    voice_type_version: int
    order_total: OrderTotal
    build_map: int
    privacy: Privacy
    dust_auto_state: int
    dust_frequency: int
    child_lock: int
    multi_floor: int
    map_save: int
    light_mode: int
    green_laser: int
    dust_bag_used: int
    order_save_mode: int
    manufacturer: str
    back_to_wash: int
    charge_station_type: int
    pv_cut_charge: int
    pv_charging: PvCharging
    serial_number: str
    recommend: Recommend
    add_sweep_status: int
