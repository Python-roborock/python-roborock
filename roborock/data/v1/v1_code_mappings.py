from ..code_mappings import RoborockEnum, RoborockModeEnum


class RoborockFinishReason(RoborockModeEnum):
    MANUAL_INTERRUPT = ("manual_interrupt", 21)  # Cleaning interrupted by user
    CLEANUP_INTERRUPTED = ("cleanup_interrupted", 24)  # Cleanup interrupted
    MANUAL_INTERRUPT_12 = ("manual_interrupt", 29)
    BREAKPOINT = ("breakpoint", 32)  # Could not continue cleaning
    BREAKPOINT_2 = ("breakpoint", 33)
    CLEANUP_INTERRUPTED_2 = ("cleanup_interrupted", 34)
    MANUAL_INTERRUPT_3 = ("manual_interrupt", 35)
    MANUAL_INTERRUPT_4 = ("manual_interrupt", 36)
    MANUAL_INTERRUPT_5 = ("manual_interrupt", 37)
    MANUAL_INTERRUPT_6 = ("manual_interrupt", 43)
    LOCATE_FAIL = ("locate_fail", 45)  # Positioning Failed
    CLEANUP_INTERRUPTED_3 = ("cleanup_interrupted", 64)
    LOCATE_FAIL_2 = ("locate_fail", 65)
    MANUAL_INTERRUPT_7 = ("manual_interrupt", 48)
    MANUAL_INTERRUPT_8 = ("manual_interrupt", 49)
    MANUAL_INTERRUPT_9 = ("manual_interrupt", 50)
    CLEANUP_INTERRUPTED_4 = ("cleanup_interrupted", 51)
    FINISHED_CLEANING = ("finished_cleaning", 52)  # Finished cleaning
    FINISHED_CLEANING_2 = ("finished_cleaning", 54)
    FINISHED_CLEANING_3 = ("finished_cleaning", 55)
    FINISHED_CLEANING_4 = ("finished_cleaning", 56)
    FINISHED_CLEANING_5 = ("finished_cleaning", 57)
    MANUAL_INTERRUPT_10 = ("manual_interrupt", 60)
    AREA_UNREACHABLE = ("area_unreachable", 61)  # Area unreachable
    AREA_UNREACHABLE_2 = ("area_unreachable", 62)
    WASHING_ERROR = ("washing_error", 67)  # Washing error
    BACK_TO_WASH_FAILURE = ("back_to_wash_failure", 68)  # Failed to return to the dock
    CHECK_SAVED_PET_FURNITURES = ("check_saved_pet_furnitures", 78)
    GET_SAVED_PET_FURNITURES = ("get_saved_pet_furnitures", 79)
    CLEANUP_INTERRUPTED_5 = ("cleanup_interrupted", 101)
    BREAKPOINT_4 = ("breakpoint", 102)
    MANUAL_INTERRUPT_11 = ("manual_interrupt", 103)
    CLEANUP_INTERRUPTED_6 = ("cleanup_interrupted", 104)
    CLEANUP_INTERRUPTED_7 = ("cleanup_interrupted", 105)
    CLEANUP_INTERRUPTED_8 = ("cleanup_interrupted", 106)
    CLEANUP_INTERRUPTED_9 = ("cleanup_interrupted", 107)
    CLEANUP_INTERRUPTED_10 = ("cleanup_interrupted", 109)
    CLEANUP_INTERRUPTED_11 = ("cleanup_interrupted", 110)
    PATROL_SUCCESS = ("patrol_success", 114)  # Cruise completed
    PATROL_FAIL = ("patrol_fail", 115)  # Cruise failed
    PET_PATROL_SUCCESS = ("pet_patrol_success", 116)  # Pet found
    PET_PATROL_FAIL = ("pet_patrol_fail", 117)  # Pet found failed


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


class RoborockDssCodes(RoborockEnum):
    @classmethod
    def _missing_(cls: type[RoborockEnum], key) -> RoborockEnum:
        # If the calculated value is not provided, then it should be viewed as okay.
        # As the math will sometimes result in you getting numbers that don't matter.
        return cls.okay  # type: ignore


class ClearWaterBoxStatus(RoborockDssCodes):
    """Status of the clear water box."""

    okay = 0
    out_of_water = 1
    out_of_water_2 = 38
    refill_error = 48


class DirtyWaterBoxStatus(RoborockDssCodes):
    """Status of the dirty water box."""

    okay = 0
    full_not_installed = 1
    full_not_installed_2 = 39
    drain_error = 49


class DustBagStatus(RoborockDssCodes):
    """Status of the dust bag."""

    okay = 0
    not_installed = 1
    full = 34


class CleanFluidStatus(RoborockDssCodes):
    """Status of the cleaning fluid container."""

    empty_not_installed = 1
    okay = 2


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
