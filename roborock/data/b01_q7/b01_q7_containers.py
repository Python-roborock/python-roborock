import datetime
from dataclasses import dataclass, field

from ..containers import RoborockBase
from .b01_q7_code_mappings import (
    B01Fault,
    SCWindMapping,
    WorkModeMapping,
    WorkStatusMapping,
)


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

    @property
    def main_brush_time_left(self) -> int | None:
        """
        Returns estimated remaining life of the main brush in minutes.
        Total life is 300 hours (18000 minutes).
        """
        if self.main_brush is None:
            return None
        return max(0, 18000 - self.main_brush)

    @property
    def side_brush_time_left(self) -> int | None:
        """
        Returns estimated remaining life of the side brush in minutes.
        Total life is 200 hours (12000 minutes).
        """
        if self.side_brush is None:
            return None
        return max(0, 12000 - self.side_brush)

    @property
    def filter_time_left(self) -> int | None:
        """
        Returns estimated remaining life of the filter (hypa) in minutes.
        Total life is 150 hours (9000 minutes).
        """
        if self.hypa is None:
            return None
        return max(0, 9000 - self.hypa)

    @property
    def mop_life_time_left(self) -> int | None:
        """
        Returns estimated remaining life of the mop in minutes.
        Total life is 180 hours (10800 minutes).
        """
        if self.mop_life is None:
            return None
        return max(0, 10800 - self.mop_life)

    @property
    def sensor_dirty_time_left(self) -> int | None:
        """
        Returns estimated time until sensors need cleaning in minutes.
        Maintenance interval is typically 30 hours (1800 minutes).
        """
        if self.main_sensor is None:
            return None
        return max(0, 1800 - self.main_sensor)

    @property
    def status_name(self) -> str | None:
        """Returns the name of the current status."""
        return self.status.value if self.status is not None else None

    @property
    def fault_name(self) -> str | None:
        """Returns the name of the current fault."""
        return self.fault.value if self.fault is not None else None

    @property
    def wind_name(self) -> str | None:
        """Returns the name of the current fan speed (wind)."""
        return self.wind.value if self.wind is not None else None

    @property
    def work_mode_name(self) -> str | None:
        """Returns the name of the current work mode."""
        return self.work_mode.value if self.work_mode is not None else None


@dataclass
class CleanRecordDetail(RoborockBase):
    """Represents a single clean record detail (from `record_list[].detail`)."""

    record_start_time: int | None = None
    method: int | None = None
    record_use_time: int | None = None
    clean_count: int | None = None
    # This is seemingly returned in meters (non-squared)
    record_clean_area: int | None = None
    record_clean_mode: int | None = None
    record_clean_way: int | None = None
    record_task_status: int | None = None
    record_faultcode: int | None = None
    record_dust_num: int | None = None
    clean_current_map: int | None = None
    record_map_url: str | None = None

    @property
    def start_datetime(self) -> datetime.datetime | None:
        """Convert the start datetime into a datetime object."""
        if self.record_start_time is not None:
            return datetime.datetime.fromtimestamp(self.record_start_time).astimezone(datetime.UTC)
        return None

    @property
    def square_meters_area_cleaned(self) -> float | None:
        """Returns the area cleaned in square meters."""
        if self.record_clean_area is not None:
            return self.record_clean_area / 100
        return None


@dataclass
class CleanRecordListItem(RoborockBase):
    """Represents an entry in the clean record list returned by `service.get_record_list`."""

    url: str | None = None
    detail: str | None = None


@dataclass
class CleanRecordList(RoborockBase):
    """Represents the clean record list response from `service.get_record_list`."""

    total_area: int | None = None
    total_time: int | None = None  # stored in seconds
    total_count: int | None = None
    record_list: list[CleanRecordListItem] = field(default_factory=list)

    @property
    def square_meters_area_cleaned(self) -> float | None:
        """Returns the area cleaned in square meters."""
        if self.total_area is not None:
            return self.total_area / 100
        return None


@dataclass
class CleanRecordSummary(RoborockBase):
    """Represents clean record totals for B01/Q7 devices."""

    total_time: int | None = None
    total_area: int | None = None
    total_count: int | None = None
    last_record_detail: CleanRecordDetail | None = None
