from ..code_mappings import RoborockEnum


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
    aftercare = 12
    waiting_for_aftercare = 13


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
