from dataclasses import dataclass, field

from .code_mappings import RoborockModeEnum
from .containers import RoborockBase


class WorkStatusMapping(RoborockModeEnum):
    """Maps the general status of the robot."""

    SLEEPING = ("sleeping", 0)
    WAITING_FOR_ORDERS = ("waiting_for_orders", 1)
    PAUSED = ("paused", 2)
    DOCKING = ("docking", 3)
    CHARGING = ("charging", 4)
    SWEEP_MOPING = ("sweep_moping", 5)
    SWEEP_MOPING_2 = ("sweep_moping_2", 6)
    MOPING = ("moping", 7)
    UPDATING = ("updating", 8)
    MOP_CLEANING = ("mop_cleaning", 9)
    MOP_AIRDRYING = ("mop_airdrying", 10)


class SCWindMapping(RoborockModeEnum):
    """Maps suction power levels."""

    SILENCE = ("quiet", 0)
    STANDARD = ("balanced", 1)
    STRONG = ("turbo", 2)
    SUPER_STRONG = ("max", 3)
    MAX = ("max_plus", 4)


class WaterLevelMapping(RoborockModeEnum):
    """Maps water flow levels."""

    LOW = ("low", 0)
    MEDIUM = ("medium", 1)
    HIGH = ("high", 2)


class CleanTypeMapping(RoborockModeEnum):
    """Maps the type of cleaning (Vacuum, Mop, or both)."""

    VACUUM = ("vacuum", 0)
    VAC_AND_MOP = ("vac_and_mop", 1)
    MOP = ("mop", 2)


class CleanRepeatMapping(RoborockModeEnum):
    """Maps the cleaning repeat parameter."""

    ONCE = ("once", 0)
    TWICE = ("twice", 1)


class WorkModeMapping(RoborockModeEnum):
    """Maps the detailed work modes of the robot."""

    IDLE = ("idle", 0)
    AUTO = ("auto", 1)
    MANUAL = ("manual", 2)
    AREA = ("area", 3)
    AUTO_PAUSE = ("auto_pause", 4)
    BACK_CHARGE = ("back_charge", 5)
    POINT = ("point", 6)
    NAVI = ("navi", 7)
    AREA_PAUSE = ("area_pause", 8)
    NAVI_PAUSE = ("navi_pause", 9)
    GLOBAL_GO_HOME = ("global_go_home", 10)
    GLOBAL_BROKEN = ("global_broken", 11)
    NAVI_GO_HOME = ("navi_go_home", 12)
    POINT_GO_HOME = ("point_go_home", 13)
    NAVI_IDLE = ("navi_idle", 14)
    SCREW = ("screw", 20)
    SCREW_GO_HOME = ("screw_go_home", 21)
    POINT_IDLE = ("point_idle", 22)
    SCREW_IDLE = ("screw_idle", 23)
    BORDER = ("border", 25)
    BORDER_GO_HOME = ("border_go_home", 26)
    BORDER_PAUSE = ("border_pause", 27)
    BORDER_BROKEN = ("border_broken", 28)
    BORDER_IDLE = ("border_idle", 29)
    PLAN_AREA = ("plan_area", 30)
    PLAN_AREA_PAUSE = ("plan_area_pause", 31)
    PLAN_AREA_GO_HOME = ("plan_area_go_home", 32)
    PLAN_AREA_BROKEN = ("plan_area_broken", 33)
    PLAN_AREA_IDLE = ("plan_area_idle", 35)
    MOPPING = ("mopping", 36)
    MOPPING_PAUSE = ("mopping_pause", 37)
    MOPPING_GO_HOME = ("mopping_go_home", 38)
    MOPPING_BROKEN = ("mopping_broken", 39)
    MOPPING_IDLE = ("mopping_idle", 40)
    EXPLORING = ("exploring", 45)
    EXPLORE_PAUSE = ("explore_pause", 46)
    EXPLORE_GO_HOME = ("explore_go_home", 47)
    EXPLORE_BROKEN = ("explore_broken", 48)
    EXPLORE_IDLE = ("explore_idle", 49)


class StationActionMapping(RoborockModeEnum):
    """Maps actions for the cleaning/drying station."""

    STOP_CLEAN_OR_AIRDRY = ("stop_clean_or_airdry", 0)
    MOP_CLEAN = ("mop_clean", 1)
    MOP_AIRDRY = ("mop_airdry", 2)


class CleanTaskTypeMapping(RoborockModeEnum):
    """Maps the high-level type of cleaning task selected."""

    ALL = ("full", 0)
    ROOM = ("room", 1)
    AREA = ("zones", 4)
    ROOM_NORMAL = ("room_normal", 5)
    CUSTOM_MODE = ("customize", 6)
    ALL_CUSTOM = ("all_custom", 11)
    AREA_CUSTOM = ("area_custom", 99)


class CarpetModeMapping(RoborockModeEnum):
    """Maps carpet handling parameters."""

    FOLLOW_GLOBAL = ("follow_global", 0)
    ON = ("on", 1)
    OFF = ("off", 2)


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


class B01Fault(RoborockModeEnum):
    """B01 fault codes and their descriptions."""

    F_0 = ("fault_0", 0)
    F_407 = ("cleaning_in_progress", 407)  # Cleaning in progress. Scheduled cleanup ignored.
    F_500 = (
        "lidar_blocked",
        500,
    )  # LiDAR turret or laser blocked. Check for obstruction and retry. LiDAR sensor obstructed or stuck.
    # Remove foreign objects if any. If the problem persists, move the robot away and restart.
    F_501 = (
        "robot_suspended",
        501,
    )  # Robot suspended. Move the robot away and restart. Cliff sensors dirty. Wipe them clean.
    F_502 = (
        "low_battery",
        502,
    )  # Low battery. Recharge now. Battery low. Put the robot on the dock to charge it to 20% before starting.
    F_503 = (
        "dustbin_not_installed",
        503,
    )  # Check that the dustbin and filter are installed properly. Reinstall the dustbin and filter in place.
    # If the problem persists, replace the filter.
    F_504 = ("fault_504", 504)
    F_505 = ("fault_505", 505)
    F_506 = ("fault_506", 506)
    F_507 = ("fault_507", 507)
    F_508 = ("fault_508", 508)
    F_509 = ("cliff_sensor_error", 509)  # Cliff sensors error. Clean them, move the robot away from drops, and restart.
    F_510 = (
        "bumper_stuck",
        510,
    )  # Bumper stuck. Clean it and lightly tap to release it. Tap it repeatedly to release it. If no foreign object
    # exists, move the robot away and restart.
    F_511 = (
        "docking_error",
        511,
    )  # Docking error. Put the robot on the dock. Clear obstacles around the dock, clean charging contacts, and put
    # the robot on the dock.
    F_512 = (
        "docking_error",
        512,
    )  # Docking error. Put the robot on the dock. Clear obstacles around the dock, clean charging contacts, and put
    # the robot on the dock.
    F_513 = (
        "robot_trapped",
        513,
    )  # Robot trapped. Move the robot away and restart. Clear obstacles around robot or move robot away and restart.
    F_514 = (
        "robot_trapped",
        514,
    )  # Robot trapped. Move the robot away and restart. Clear obstacles around robot or move robot away and restart.
    F_515 = ("fault_515", 515)
    F_517 = ("fault_517", 517)
    F_518 = (
        "low_battery",
        518,
    )  # Low battery. Recharge now. Battery low. Put the robot on the dock to charge it to 20% before starting.
    F_519 = ("fault_519", 519)
    F_520 = ("fault_520", 520)
    F_521 = ("fault_521", 521)
    F_522 = ("mop_not_installed", 522)  # Check that the mop is properly installed. Mop not installed. Reinstall it.
    F_523 = ("fault_523", 523)
    F_525 = ("fault_525", 525)
    F_526 = ("fault_526", 526)
    F_527 = ("fault_527", 527)
    F_528 = ("fault_528", 528)
    F_529 = ("fault_529", 529)
    F_530 = ("fault_530", 530)
    F_531 = ("fault_531", 531)
    F_532 = ("fault_532", 532)
    F_533 = ("long_sleep", 533)  # About to shut down after a long time of sleep. Charge the robot.
    F_534 = (
        "low_battery_shutdown",
        534,
    )  # Low battery. Turning off. About to shut down due to low battery. Charge the robot.
    F_535 = ("fault_535", 535)
    F_536 = ("fault_536", 536)
    F_540 = ("fault_540", 540)
    F_541 = ("fault_541", 541)
    F_542 = ("fault_542", 542)
    F_550 = ("fault_550", 550)
    F_551 = ("fault_551", 551)
    F_559 = ("fault_559", 559)
    F_560 = ("side_brush_entangled", 560)  # Side brush entangled. Remove and clean it.
    F_561 = ("fault_561", 561)
    F_562 = ("fault_562", 562)
    F_563 = ("fault_563", 563)
    F_564 = ("fault_564", 564)
    F_565 = ("fault_565", 565)
    F_566 = ("fault_566", 566)
    F_567 = ("fault_567", 567)
    F_568 = ("main_wheels_entangled", 568)  # Clean main wheels, move the robot away and restart.
    F_569 = ("main_wheels_entangled", 569)  # Clean main wheels, move the robot away and restart.
    F_570 = ("main_brush_entangled", 570)  # Main brush entangled. Remove and clean it and its bearing.
    F_571 = ("fault_571", 571)
    F_572 = ("main_brush_entangled", 572)  # Main brush entangled. Remove and clean it and its bearing.
    F_573 = ("fault_573", 573)
    F_574 = ("fault_574", 574)
    F_580 = ("fault_580", 580)
    F_581 = ("fault_581", 581)
    F_582 = ("fault_582", 582)
    F_583 = ("fault_583", 583)
    F_584 = ("fault_584", 584)
    F_585 = ("fault_585", 585)
    F_586 = ("fault_586", 586)
    F_587 = ("fault_587", 587)
    F_588 = ("fault_588", 588)
    F_589 = ("fault_589", 589)
    F_590 = ("fault_590", 590)
    F_591 = ("fault_591", 591)
    F_592 = ("fault_592", 592)
    F_593 = ("fault_593", 593)
    F_594 = (
        "dust_bag_not_installed",
        594,
    )  # Make sure the dust bag is properly installed. Dust bag not installed. Check that it is installed properly.
    F_601 = ("fault_601", 601)
    F_602 = ("fault_602", 602)
    F_603 = ("fault_603", 603)
    F_604 = ("fault_604", 604)
    F_605 = ("fault_605", 605)
    F_611 = ("positioning_failed", 611)  # Positioning failed. Move the robot back to the dock and remap.
    F_612 = (
        "map_changed",
        612,
    )  # Map changed. Positioning failed. Try again. New environment detected. Map changed. Positioning failed.
    # Try again after remapping.
    F_629 = ("mop_mount_fell_off", 629)  # Mop cloth mount fell off. Reinstall it to resume working.
    F_668 = (
        "system_error",
        668,
    )  # Robot error. Reset the system. Fan error. Reset the system. If the problem persists, contact customer service.
    F_2000 = ("fault_2000", 2000)
    F_2003 = ("low_battery_schedule_canceled", 2003)  # Battery level below 20%. Scheduled task canceled.
    F_2007 = (
        "cannot_reach_target",
        2007,
    )  # Unable to reach the target. Cleaning ended. Ensure the door to the target area is open or unobstructed.
    F_2012 = (
        "cannot_reach_target",
        2012,
    )  # Unable to reach the target. Cleaning ended. Ensure the door to the target area is open or unobstructed.
    F_2013 = ("fault_2013", 2013)
    F_2015 = ("fault_2015", 2015)
    F_2017 = ("fault_2017", 2017)
    F_2100 = (
        "low_battery_resume_later",
        2100,
    )  # Low battery. Resume cleaning after recharging. Low battery. Starting to recharge. Resume cleaning after
    # charging.
    F_2101 = ("fault_2101", 2101)
    F_2102 = ("cleaning_complete", 2102)  # Cleaning completed. Returning to the dock.
    F_2103 = ("fault_2103", 2103)
    F_2104 = ("fault_2104", 2104)
    F_2105 = ("fault_2105", 2105)
    F_2108 = ("fault_2108", 2108)
    F_2109 = ("fault_2109", 2109)
    F_2110 = ("fault_2110", 2110)
    F_2111 = ("fault_2111", 2111)
    F_2112 = ("fault_2112", 2112)
    F_2113 = ("fault_2113", 2113)
    F_2114 = ("fault_2114", 2114)
    F_2115 = ("fault_2115", 2115)


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
