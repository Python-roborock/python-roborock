from __future__ import annotations

import logging
from collections import namedtuple
from enum import Enum, IntEnum, StrEnum

_LOGGER = logging.getLogger(__name__)
completed_warnings = set()


class RoborockEnum(IntEnum):
    """Roborock Enum for codes with int values"""

    @property
    def name(self) -> str:
        return super().name.lower()

    @classmethod
    def _missing_(cls: type[RoborockEnum], key) -> RoborockEnum:
        if hasattr(cls, "unknown"):
            warning = f"Missing {cls.__name__} code: {key} - defaulting to 'unknown'"
            if warning not in completed_warnings:
                completed_warnings.add(warning)
                _LOGGER.warning(warning)
            return cls.unknown  # type: ignore
        default_value = next(item for item in cls)
        warning = f"Missing {cls.__name__} code: {key} - defaulting to {default_value}"
        if warning not in completed_warnings:
            completed_warnings.add(warning)
            _LOGGER.warning(warning)
        return default_value

    @classmethod
    def as_dict(cls: type[RoborockEnum]):
        return {i.name: i.value for i in cls if i.name != "missing"}

    @classmethod
    def as_enum_dict(cls: type[RoborockEnum]):
        return {i.value: i for i in cls if i.name != "missing"}

    @classmethod
    def values(cls: type[RoborockEnum]) -> list[int]:
        return list(cls.as_dict().values())

    @classmethod
    def keys(cls: type[RoborockEnum]) -> list[str]:
        return list(cls.as_dict().keys())

    @classmethod
    def items(cls: type[RoborockEnum]):
        return cls.as_dict().items()


class RoborockModeEnum(StrEnum):
    """A custom StrEnum that also stores an integer code for each member."""

    code: int

    def __new__(cls, value: str, code: int) -> RoborockModeEnum:
        """Creates a new enum member."""
        member = str.__new__(cls, value)
        member._value_ = value
        member.code = code
        return member

    @classmethod
    def from_code(cls, code: int):
        for member in cls:
            if member.code == code:
                return member
        raise ValueError(f"{code} is not a valid code for {cls.__name__}")


ProductInfo = namedtuple("ProductInfo", ["nickname", "short_models"])


class RoborockProductNickname(Enum):
    # Coral Series
    CORAL = ProductInfo(nickname="Coral", short_models=("a20", "a21"))
    CORALPRO = ProductInfo(nickname="CoralPro", short_models=("a143", "a144"))

    # Pearl Series
    PEARL = ProductInfo(nickname="Pearl", short_models=("a74", "a75"))
    PEARLC = ProductInfo(nickname="PearlC", short_models=("a103", "a104"))
    PEARLE = ProductInfo(nickname="PearlE", short_models=("a167", "a168"))
    PEARLELITE = ProductInfo(nickname="PearlELite", short_models=("a169", "a170"))
    PEARLPLUS = ProductInfo(nickname="PearlPlus", short_models=("a86", "a87"))
    PEARLPLUSS = ProductInfo(nickname="PearlPlusS", short_models=("a116", "a117", "a136"))
    PEARLS = ProductInfo(nickname="PearlS", short_models=("a100", "a101"))
    PEARLSLITE = ProductInfo(nickname="PearlSLite", short_models=("a122", "a123"))

    # Ruby Series
    RUBYPLUS = ProductInfo(nickname="RubyPlus", short_models=("t4", "s4"))
    RUBYSC = ProductInfo(nickname="RubySC", short_models=("p5", "a08"))
    RUBYSE = ProductInfo(nickname="RubySE", short_models=("a19",))
    RUBYSLITE = ProductInfo(nickname="RubySLite", short_models=("p6", "s5e", "a05"))

    # Tanos Series
    TANOS = ProductInfo(nickname="Tanos", short_models=("t6", "s6"))
    TANOSE = ProductInfo(nickname="TanosE", short_models=("t7", "a11"))
    TANOSS = ProductInfo(nickname="TanosS", short_models=("a14", "a15"))
    TANOSSC = ProductInfo(nickname="TanosSC", short_models=("a39", "a40"))
    TANOSSE = ProductInfo(nickname="TanosSE", short_models=("a33", "a34"))
    TANOSSMAX = ProductInfo(nickname="TanosSMax", short_models=("a52",))
    TANOSSLITE = ProductInfo(nickname="TanosSLite", short_models=("a37", "a38"))
    TANOSSPLUS = ProductInfo(nickname="TanosSPlus", short_models=("a23", "a24"))
    TANOSV = ProductInfo(nickname="TanosV", short_models=("t7p", "a09", "a10"))

    # Topaz Series
    TOPAZS = ProductInfo(nickname="TopazS", short_models=("a29", "a30", "a76"))
    TOPAZSC = ProductInfo(nickname="TopazSC", short_models=("a64", "a65"))
    TOPAZSPLUS = ProductInfo(nickname="TopazSPlus", short_models=("a46", "a47", "a66"))
    TOPAZSPOWER = ProductInfo(nickname="TopazSPower", short_models=("a62",))
    TOPAZSV = ProductInfo(nickname="TopazSV", short_models=("a26", "a27"))

    # Ultron Series
    ULTRON = ProductInfo(nickname="Ultron", short_models=("a50", "a51"))
    ULTRONE = ProductInfo(nickname="UltronE", short_models=("a72", "a84"))
    ULTRONLITE = ProductInfo(nickname="UltronLite", short_models=("a73", "a85"))
    ULTRONSC = ProductInfo(nickname="UltronSC", short_models=("a94", "a95"))
    ULTRONSE = ProductInfo(nickname="UltronSE", short_models=("a124", "a125", "a139", "a140"))
    ULTRONSPLUS = ProductInfo(nickname="UltronSPlus", short_models=("a68", "a69", "a70"))
    ULTRONSV = ProductInfo(nickname="UltronSV", short_models=("a96", "a97"))

    # Verdelite Series
    VERDELITE = ProductInfo(nickname="Verdelite", short_models=("a146", "a147"))

    # Vivian Series
    VIVIAN = ProductInfo(nickname="Vivian", short_models=("a134", "a135", "a155", "a156"))
    VIVIANC = ProductInfo(nickname="VivianC", short_models=("a158", "a159"))


SHORT_MODEL_TO_ENUM = {model: product for product in RoborockProductNickname for model in product.value.short_models}


class RoborockStateCode(RoborockEnum):
    unknown = 0
    starting = 1
    charger_disconnected = 2
    idle = 3
    remote_control_active = 4
    cleaning = 5
    returning_home = 6
    manual_mode = 7
    charging = 8
    charging_problem = 9
    paused = 10
    spot_cleaning = 11
    error = 12
    shutting_down = 13
    updating = 14
    docking = 15
    going_to_target = 16
    zoned_cleaning = 17
    segment_cleaning = 18
    emptying_the_bin = 22  # on s7+
    washing_the_mop = 23  # on a46
    washing_the_mop_2 = 25
    going_to_wash_the_mop = 26  # on a46
    in_call = 28
    mapping = 29
    egg_attack = 30
    patrol = 32
    attaching_the_mop = 33  # on g20s ultra
    detaching_the_mop = 34  # on g20s ultra
    charging_complete = 100
    device_offline = 101
    locked = 103
    air_drying_stopping = 202
    robot_status_mopping = 6301
    clean_mop_cleaning = 6302
    clean_mop_mopping = 6303
    segment_mopping = 6304
    segment_clean_mop_cleaning = 6305
    segment_clean_mop_mopping = 6306
    zoned_mopping = 6307
    zoned_clean_mop_cleaning = 6308
    zoned_clean_mop_mopping = 6309
    back_to_dock_washing_duster = 6310


class RoborockDyadStateCode(RoborockEnum):
    unknown = -999
    fetching = -998  # Obtaining Status
    fetch_failed = -997  # Failed to obtain device status. Try again later.
    updating = -996
    washing = 1
    ready = 2
    charging = 3
    mop_washing = 4
    self_clean_cleaning = 5
    self_clean_deep_cleaning = 6
    self_clean_rinsing = 7
    self_clean_dehydrating = 8
    drying = 9
    ventilating = 10  # drying
    reserving = 12
    mop_washing_paused = 13
    dusting_mode = 14


class RoborockErrorCode(RoborockEnum):
    none = 0
    lidar_blocked = 1
    bumper_stuck = 2
    wheels_suspended = 3
    cliff_sensor_error = 4
    main_brush_jammed = 5
    side_brush_jammed = 6
    wheels_jammed = 7
    robot_trapped = 8
    no_dustbin = 9
    strainer_error = 10  # Filter is wet or blocked
    compass_error = 11  # Strong magnetic field detected
    low_battery = 12
    charging_error = 13
    battery_error = 14
    wall_sensor_dirty = 15
    robot_tilted = 16
    side_brush_error = 17
    fan_error = 18
    dock = 19  # Dock not connected to power
    optical_flow_sensor_dirt = 20
    vertical_bumper_pressed = 21
    dock_locator_error = 22
    return_to_dock_fail = 23
    nogo_zone_detected = 24
    visual_sensor = 25  # Camera error
    light_touch = 26  # Wall sensor error
    vibrarise_jammed = 27
    robot_on_carpet = 28
    filter_blocked = 29
    invisible_wall_detected = 30
    cannot_cross_carpet = 31
    internal_error = 32
    collect_dust_error_3 = 34  # Clean auto-empty dock
    collect_dust_error_4 = 35  # Auto empty dock voltage error
    mopping_roller_1 = 36  # Wash roller may be jammed
    mopping_roller_error_2 = 37  # wash roller not lowered properly
    clear_water_box_hoare = 38  # Check the clean water tank
    dirty_water_box_hoare = 39  # Check the dirty water tank
    sink_strainer_hoare = 40  # Reinstall the water filter
    clear_water_box_exception = 41  # Clean water tank empty
    clear_brush_exception = 42  # Check that the water filter has been correctly installed
    clear_brush_exception_2 = 43  # Positioning button error
    filter_screen_exception = 44  # Clean the dock water filter
    mopping_roller_2 = 45  # Wash roller may be jammed
    up_water_exception = 48
    drain_water_exception = 49
    temperature_protection = 51  # Unit temperature protection
    clean_carousel_exception = 52
    clean_carousel_water_full = 53
    water_carriage_drop = 54
    check_clean_carouse = 55
    audio_error = 56


class RoborockFanPowerCode(RoborockEnum):
    """Describes the fan power of the vacuum cleaner."""

    # Fan speeds should have the first letter capitalized - as there is no way to change the name in translations as
    # far as I am aware


class RoborockFanSpeedV1(RoborockFanPowerCode):
    silent = 38
    standard = 60
    medium = 77
    turbo = 90


class RoborockFanSpeedV2(RoborockFanPowerCode):
    silent = 101
    balanced = 102
    turbo = 103
    max = 104
    gentle = 105
    auto = 106


class RoborockFanSpeedV3(RoborockFanPowerCode):
    silent = 38
    standard = 60
    medium = 75
    turbo = 100


class RoborockFanSpeedE2(RoborockFanPowerCode):
    gentle = 41
    silent = 50
    standard = 68
    medium = 79
    turbo = 100


class RoborockFanSpeedS7(RoborockFanPowerCode):
    off = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    custom = 106


class RoborockFanSpeedS7MaxV(RoborockFanPowerCode):
    off = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    custom = 106
    max_plus = 108


class RoborockFanSpeedS6Pure(RoborockFanPowerCode):
    gentle = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    custom = 106


class RoborockFanSpeedQ7Max(RoborockFanPowerCode):
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104


class RoborockFanSpeedQRevoMaster(RoborockFanPowerCode):
    off = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    custom = 106
    max_plus = 108
    smart_mode = 110


class RoborockFanSpeedQRevoCurv(RoborockFanPowerCode):
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    off = 105
    custom = 106
    max_plus = 108
    smart_mode = 110


class RoborockFanSpeedQRevoMaxV(RoborockFanPowerCode):
    off = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    custom = 106
    max_plus = 108
    smart_mode = 110


class RoborockFanSpeedP10(RoborockFanPowerCode):
    off = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    custom = 106
    max_plus = 108
    smart_mode = 110


class RoborockFanSpeedS8MaxVUltra(RoborockFanPowerCode):
    off = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    custom = 106
    max_plus = 108
    smart_mode = 110


class RoborockFanSpeedSaros10(RoborockFanPowerCode):
    off = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    custom = 106
    max_plus = 108
    smart_mode = 110


class RoborockFanSpeedSaros10R(RoborockFanPowerCode):
    off = 105
    quiet = 101
    balanced = 102
    turbo = 103
    max = 104
    custom = 106
    max_plus = 108
    smart_mode = 110


class RoborockMopModeCode(RoborockEnum):
    """Describes the mop mode of the vacuum cleaner."""


class RoborockMopModeQRevoCurv(RoborockMopModeCode):
    standard = 300
    deep = 301
    custom = 302
    deep_plus = 303
    fast = 304
    smart_mode = 306


class RoborockMopModeS7(RoborockMopModeCode):
    """Describes the mop mode of the vacuum cleaner."""

    standard = 300
    deep = 301
    custom = 302
    deep_plus = 303


class RoborockMopModeS8ProUltra(RoborockMopModeCode):
    standard = 300
    deep = 301
    deep_plus = 303
    fast = 304
    custom = 302
    smart_mode = 306


class RoborockMopModeS8MaxVUltra(RoborockMopModeCode):
    standard = 300
    deep = 301
    custom = 302
    deep_plus = 303
    fast = 304
    deep_plus_pearl = 305
    smart_mode = 306


class RoborockMopModeSaros10R(RoborockMopModeCode):
    standard = 300
    deep = 301
    custom = 302
    deep_plus = 303
    fast = 304
    smart_mode = 306


class RoborockMopModeQRevoMaster(RoborockMopModeCode):
    standard = 300
    deep = 301
    custom = 302
    deep_plus = 303
    fast = 304
    smart_mode = 306


class RoborockMopModeQRevoMaxV(RoborockMopModeCode):
    standard = 300
    deep = 301
    custom = 302
    deep_plus = 303
    fast = 304
    smart_mode = 306


class RoborockMopModeSaros10(RoborockMopModeCode):
    standard = 300
    deep = 301
    custom = 302
    deep_plus = 303
    fast = 304
    smart_mode = 306


class RoborockMopIntensityCode(RoborockEnum):
    """Describes the mop intensity of the vacuum cleaner."""


class RoborockMopIntensityS7(RoborockMopIntensityCode):
    """Describes the mop intensity of the vacuum cleaner."""

    off = 200
    mild = 201
    moderate = 202
    intense = 203
    custom = 204


class RoborockMopIntensityV2(RoborockMopIntensityCode):
    """Describes the mop intensity of the vacuum cleaner."""

    off = 200
    low = 201
    medium = 202
    high = 203
    custom = 207


class RoborockMopIntensityQRevoMaster(RoborockMopIntensityCode):
    """Describes the mop intensity of the vacuum cleaner."""

    off = 200
    low = 201
    medium = 202
    high = 203
    custom = 204
    custom_water_flow = 207
    smart_mode = 209


class RoborockMopIntensityQRevoCurv(RoborockMopIntensityCode):
    off = 200
    low = 201
    medium = 202
    high = 203
    custom = 204
    custom_water_flow = 207
    smart_mode = 209


class RoborockMopIntensityQRevoMaxV(RoborockMopIntensityCode):
    off = 200
    low = 201
    medium = 202
    high = 203
    custom = 204
    custom_water_flow = 207
    smart_mode = 209


class RoborockMopIntensityP10(RoborockMopIntensityCode):
    """Describes the mop intensity of the vacuum cleaner."""

    off = 200
    low = 201
    medium = 202
    high = 203
    custom = 204
    custom_water_flow = 207
    smart_mode = 209


class RoborockMopIntensityS8MaxVUltra(RoborockMopIntensityCode):
    off = 200
    low = 201
    medium = 202
    high = 203
    custom = 204
    max = 208
    smart_mode = 209
    custom_water_flow = 207


class RoborockMopIntensitySaros10(RoborockMopIntensityCode):
    off = 200
    mild = 201
    standard = 202
    intense = 203
    extreme = 208
    custom = 204
    smart_mode = 209


class RoborockMopIntensitySaros10R(RoborockMopIntensityCode):
    off = 200
    low = 201
    medium = 202
    high = 203
    custom = 204
    extreme = 250
    vac_followed_by_mop = 235
    smart_mode = 209


class RoborockMopIntensityS5Max(RoborockMopIntensityCode):
    """Describes the mop intensity of the vacuum cleaner."""

    off = 200
    low = 201
    medium = 202
    high = 203
    custom = 204
    custom_water_flow = 207


class RoborockMopIntensityS6MaxV(RoborockMopIntensityCode):
    """Describes the mop intensity of the vacuum cleaner."""

    off = 200
    low = 201
    medium = 202
    high = 203
    custom = 204
    custom_water_flow = 207


class RoborockMopIntensityQ7Max(RoborockMopIntensityCode):
    """Describes the mop intensity of the vacuum cleaner."""

    off = 200
    low = 201
    medium = 202
    high = 203
    custom_water_flow = 207


class RoborockDockErrorCode(RoborockEnum):
    """Describes the error code of the dock."""

    ok = 0
    duct_blockage = 34
    water_empty = 38
    waste_water_tank_full = 39
    maintenance_brush_jammed = 42
    dirty_tank_latch_open = 44
    no_dustbin = 46
    cleaning_tank_full_or_blocked = 53


class RoborockDockTypeCode(RoborockEnum):
    unknown = -9999
    no_dock = 0
    auto_empty_dock = 1
    empty_wash_fill_dock = 3
    auto_empty_dock_pure = 5
    s7_max_ultra_dock = 6
    s8_dock = 7
    p10_dock = 8
    p10_pro_dock = 9
    s8_maxv_ultra_dock = 10
    qrevo_master_dock = 14
    qrevo_s_dock = 15
    saros_r10_dock = 16
    qrevo_curv_dock = 17
    saros_10_dock = 18


class RoborockDockDustCollectionModeCode(RoborockEnum):
    """Describes the dust collection mode of the vacuum cleaner."""

    # TODO: Get the correct values for various different docks
    unknown = -9999
    smart = 0
    light = 1
    balanced = 2
    max = 4


class RoborockDockWashTowelModeCode(RoborockEnum):
    """Describes the wash towel mode of the vacuum cleaner."""

    # TODO: Get the correct values for various different docks
    unknown = -9999
    light = 0
    balanced = 1
    deep = 2
    smart = 10


class RoborockCategory(Enum):
    """Describes the category of the device."""

    WET_DRY_VAC = "roborock.wetdryvac"
    VACUUM = "robot.vacuum.cleaner"
    WASHING_MACHINE = "roborock.wm"
    UNKNOWN = "UNKNOWN"

    def __missing__(self, key):
        _LOGGER.warning("Missing key %s from category", key)
        return RoborockCategory.UNKNOWN


class RoborockFinishReason(RoborockEnum):
    manual_interrupt = 21  # Cleaning interrupted by user
    cleanup_interrupted = 24  # Cleanup interrupted
    manual_interrupt_2 = 21
    manual_interrupt_12 = 29
    breakpoint = 32  # Could not continue cleaning
    breakpoint_2 = 33
    cleanup_interrupted_2 = 34
    manual_interrupt_3 = 35
    manual_interrupt_4 = 36
    manual_interrupt_5 = 37
    manual_interrupt_6 = 43
    locate_fail = 45  # Positioning Failed
    cleanup_interrupted_3 = 64
    locate_fail_2 = 65
    manual_interrupt_7 = 48
    manual_interrupt_8 = 49
    manual_interrupt_9 = 50
    cleanup_interrupted_4 = 51
    finished_cleaning = 52  # Finished cleaning
    finished_cleaning_2 = 54
    finished_cleaning_3 = 55
    finished_cleaning_4 = 56
    finished_clenaing_5 = 57
    manual_interrupt_10 = 60
    area_unreachable = 61  # Area unreachable
    area_unreachable_2 = 62
    washing_error = 67  # Washing error
    back_to_wash_failure = 68  # Failed to return to the dock
    cleanup_interrupted_5 = 101
    breakpoint_4 = 102
    manual_interrupt_11 = 103
    cleanup_interrupted_6 = 104
    cleanup_interrupted_7 = 105
    cleanup_interrupted_8 = 106
    cleanup_interrupted_9 = 107
    cleanup_interrupted_10 = 109
    cleanup_interrupted_11 = 110
    patrol_success = 114  # Cruise completed
    patrol_fail = 115  # Cruise failed
    pet_patrol_success = 116  # Pet found
    pet_patrol_fail = 117  # Pet found failed


class RoborockInCleaning(RoborockEnum):
    complete = 0
    global_clean_not_complete = 1
    zone_clean_not_complete = 2
    segment_clean_not_complete = 3


class RoborockCleanType(RoborockEnum):
    all_zone = 1
    draw_zone = 2
    select_zone = 3
    quick_build = 4
    video_patrol = 5
    pet_patrol = 6


class RoborockStartType(RoborockEnum):
    button = 1
    app = 2
    schedule = 3
    mi_home = 4
    quick_start = 5
    voice_control = 13
    routines = 101
    alexa = 801
    google = 802
    ifttt = 803
    yandex = 804
    homekit = 805
    xiaoai = 806
    tmall_genie = 807
    duer = 808
    dingdong = 809
    siri = 810
    clova = 811
    wechat = 901
    alipay = 902
    aqara = 903
    hisense = 904
    huawei = 905
    widget_launch = 820
    smart_watch = 821


class DyadSelfCleanMode(RoborockEnum):
    self_clean = 1
    self_clean_and_dry = 2
    dry = 3
    ventilation = 4


class DyadSelfCleanLevel(RoborockEnum):
    normal = 1
    deep = 2


class DyadWarmLevel(RoborockEnum):
    normal = 1
    deep = 2


class DyadMode(RoborockEnum):
    wash = 1
    wash_and_dry = 2
    dry = 3


class DyadCleanMode(RoborockEnum):
    auto = 1
    max = 2
    dehydration = 3
    power_saving = 4


class DyadSuction(RoborockEnum):
    l1 = 1
    l2 = 2
    l3 = 3
    l4 = 4
    l5 = 5
    l6 = 6


class DyadWaterLevel(RoborockEnum):
    l1 = 1
    l2 = 2
    l3 = 3
    l4 = 4


class DyadBrushSpeed(RoborockEnum):
    l1 = 1
    l2 = 2


class DyadCleanser(RoborockEnum):
    none = 0
    normal = 1
    deep = 2
    max = 3


class DyadError(RoborockEnum):
    none = 0
    dirty_tank_full = 20000  # Dirty tank full. Empty it
    water_level_sensor_stuck = 20001  # Water level sensor is stuck. Clean it.
    clean_tank_empty = 20002  # Clean tank empty. Refill now
    clean_head_entangled = 20003  # Check if the cleaning head is entangled with foreign objects.
    clean_head_too_hot = 20004  # Cleaning head temperature protection. Wait for the temperature to return to normal.
    fan_protection_e5 = 10005  # Fan protection (E5). Restart the vacuum cleaner.
    cleaning_head_blocked = 20005  # Remove blockages from the cleaning head and pipes.
    temperature_protection = 20006  # Temperature protection. Wait for the temperature to return to normal
    fan_protection_e4 = 10004  # Fan protection (E4). Restart the vacuum cleaner.
    fan_protection_e9 = 10009  # Fan protection (E9). Restart the vacuum cleaner.
    battery_temperature_protection_e0 = 10000
    battery_temperature_protection = (
        20007  # Battery temperature protection. Wait for the temperature to return to a normal range.
    )
    battery_temperature_protection_2 = 20008
    power_adapter_error = 20009  # Check if the power adapter is working properly.
    dirty_charging_contacts = 10007  # Disconnection between the device and dock. Wipe charging contacts.
    low_battery = 20017  # Low battery level. Charge before starting self-cleaning.
    battery_under_10 = 20018  # Charge until the battery level exceeds 10% before manually starting self-cleaning.


class ZeoMode(RoborockEnum):
    wash = 1
    wash_and_dry = 2
    dry = 3


class ZeoState(RoborockEnum):
    standby = 1
    weighing = 2
    soaking = 3
    washing = 4
    rinsing = 5
    spinning = 6
    drying = 7
    cooling = 8
    under_delay_start = 9
    done = 10


class ZeoProgram(RoborockEnum):
    standard = 1
    quick = 2
    sanitize = 3
    wool = 4
    air_refresh = 5
    custom = 6
    bedding = 7
    down = 8
    silk = 9
    rinse_and_spin = 10
    spin = 11
    down_clean = 12
    baby_care = 13
    anti_allergen = 14
    sportswear = 15
    night = 16
    new_clothes = 17
    shirts = 18
    synthetics = 19
    underwear = 20
    gentle = 21
    intensive = 22
    cotton_linen = 23
    season = 24
    warming = 25
    bra = 26
    panties = 27
    boiling_wash = 28
    socks = 30
    towels = 31
    anti_mite = 32
    exo_40_60 = 33
    twenty_c = 34
    t_shirts = 35
    stain_removal = 36


class ZeoSoak(RoborockEnum):
    normal = 0
    low = 1
    medium = 2
    high = 3
    max = 4


class ZeoTemperature(RoborockEnum):
    normal = 1
    low = 2
    medium = 3
    high = 4
    max = 5
    twenty_c = 6


class ZeoRinse(RoborockEnum):
    none = 0
    min = 1
    low = 2
    mid = 3
    high = 4
    max = 5


class ZeoSpin(RoborockEnum):
    none = 1
    very_low = 2
    low = 3
    mid = 4
    high = 5
    very_high = 6
    max = 7


class ZeoDryingMode(RoborockEnum):
    none = 0
    quick = 1
    iron = 2
    store = 3


class ZeoDetergentType(RoborockEnum):
    empty = 0
    low = 1
    medium = 2
    high = 3


class ZeoSoftenerType(RoborockEnum):
    empty = 0
    low = 1
    medium = 2
    high = 3


class ZeoError(RoborockEnum):
    none = 0
    refill_error = 1
    drain_error = 2
    door_lock_error = 3
    water_level_error = 4
    inverter_error = 5
    heating_error = 6
    temperature_error = 7
    communication_error = 10
    drying_error = 11
    drying_error_e_12 = 12
    drying_error_e_13 = 13
    drying_error_e_14 = 14
    drying_error_e_15 = 15
    drying_error_e_16 = 16
    drying_error_water_flow = 17  # Check for normal water flow
    drying_error_restart = 18  # Restart the washer and try again
    spin_error = 19  # re-arrange clothes
