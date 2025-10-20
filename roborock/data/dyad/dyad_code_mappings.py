from ..code_mappings import RoborockEnum


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
