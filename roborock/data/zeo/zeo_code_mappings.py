"""Zeo (washing machine) device enums.

Member-level comments show the manufacturer's official identifiers
extracted from the React Native app plugin bundle.

For enums that map between protocol-level positions and physical units
(e.g. spin speed, temperature), the comment format is
``# L<N>, <physical-value>`` where ``L<N>`` is the protocol position
and ``<physical-value>`` is the user-facing display value
(RPM, degrees Celsius, minutes, etc.).

Enums commented out at the bottom of this file are App-internal lookup
tables and UI state machines — they are not DP protocol enums and are
never sent to the device.
"""

from ..code_mappings import RoborockEnum


class ZeoFeatureBits(RoborockEnum):
    """Bit positions in DP 237 (FEATURE_BITS).

    Extracted from the official Roborock Washer app plugin bundle
    (index.ios.bundle, module 726).  Each member's integer value
    is the exact bit offset the device reports at DP 237.
    """

    smart_hosting = 0
    silent_mode = 1
    new_custom_program = 2
    dry_care = 3
    set_uvc_in_appointment = 4
    detect_door_status = 5
    expand_softener = 6
    set_params_in_working = 7
    thirty_min_soak = 8
    smile_light = 9
    set_uvc_in_pause = 10
    concentrated_detergent = 11
    wool_detergent = 12
    voice_assistant = 13
    adapted_custom_program = 14
    voice_assistant_record = 15
    fluff_clean_notification = 16
    power_button_indicator_light = 17
    dirt_detection = 18
    deep_self_clean = 19
    save_panel_program_params = 20
    steam_care = 21
    wash_dry_linkage = 22
    ion_deodorization = 23


class ZeoMode(RoborockEnum):
    null = 0  # (not found in app bundle)
    wash = 1
    wash_and_dry = 2
    dry = 3
    treatment = 4


class ZeoState(RoborockEnum):
    standby = 1
    weighing = 2  # Checking
    soaking = 3
    washing = 4
    rinsing = 5
    spinning = 6  # Dewatering
    drying = 7
    cooling = 8
    under_delay_start = 9  # Appointment
    done = 10  # Complete
    updating = 11
    aftercare = 12  # SmartHosting
    waiting_for_aftercare = 13  # SmartHostingWaiting
    steam_caring = 14
    descaling = 15
    cloth_ready = 16
    waiting_for_drying = 17
    pre_heating = 18
    pre_heat_complete = 19
    in_care = 20


class ZeoProgram(RoborockEnum):
    null = 0  # (not found in app bundle)
    standard = 1  # Mixed
    quick = 2
    sanitize = 3  # Sterilization
    wool = 4
    air_refresh = 5  # Air
    custom = 6  # CloudProgram
    bedding = 7  # HomeTextile
    down = 8
    silk = 9
    rinse_and_spin = 10  # RinseAndDehydrate
    spin = 11  # Dehydrate
    down_clean = 12  # SelfClean
    baby_care = 13  # Baby
    anti_allergen = 14  # MitesRemoval
    sportswear = 15  # Sports
    night = 16
    new_clothes = 17  # New
    shirts = 18  # Shirt
    synthetics = 19  # ChemicalFiber
    underwear = 20
    gentle = 21  # Soft
    intensive = 22  # Strong
    cotton_linen = 23  # CottonOrLinen
    season = 24
    warming = 25  # Warm
    bra = 26
    panties = 27  # Underpants
    boiling_wash = 28  # Boiling
    soaking = 29
    socks = 30
    towels = 31  # Towel
    anti_mite = 32  # MitesRemoval2
    exo_40_60 = 33  # Eco
    twenty_c = 34  # TwentyDegrees
    t_shirts = 35  # TShirt
    stain_removal = 36  # Dirt
    small_things = 37
    mixing = 39
    bath_towel = 40
    jeans = 41
    outdoors = 42
    timed_drying = 43
    outdoor_jackets = 44
    yoga = 45
    quilt_drying = 46
    flax = 47
    suit = 48
    sport_shoes = 49
    rack_drying = 50
    summer_quilt = 51
    wind_breaker = 52
    steam_care = 53
    descaling = 54
    deep_self_clean = 55
    pet_care = 56
    small_things_drying = 57


class ZeoSoak(RoborockEnum):
    normal = 0  # L0, 0min
    low = 1  # L1, 5min
    medium = 2  # L2, 10min
    high = 3  # L3, 15min
    max = 4  # L4, 20min
    very_max = 5  # L5, 30min


class ZeoTemperature(RoborockEnum):
    normal = 1  # L1, 0 C
    low = 2  # L2, 30 C
    medium = 3  # L3, 40 C
    high = 4  # L4, 60 C
    max = 5  # L5, 90 C
    twenty_c = 6  # L6, 20 C
    ninety_c = 7  # L7, 95 C


class ZeoRinse(RoborockEnum):
    none = 0  # L0, None
    min = 1  # L1, Min
    low = 2  # L2, Low
    mid = 3  # L3, Mid
    high = 4  # L4, High
    max = 5  # L5, Max


class ZeoSpin(RoborockEnum):
    null = 0  # (not found in app bundle)
    none = 1  # L1, 0 RPM
    very_low = 2  # L2, 400 RPM
    low = 3  # L3, 600 RPM
    mid = 4  # L4, 800 RPM
    high = 5  # L5, 1000 RPM
    very_high = 6  # L6, 1200 RPM
    max = 7  # L7, 1400 RPM


class ZeoDryingMode(RoborockEnum):
    none = 0
    quick = 1  # Quick, Mid
    iron = 2  # Iron, Low
    store = 3  # Store, High


class ZeoDetergentType(RoborockEnum):
    empty = 0  # T0
    low = 1  # T1
    medium = 2  # T2
    high = 3  # T3


class ZeoSoftenerType(RoborockEnum):
    empty = 0  # T0
    low = 1  # T1
    medium = 2  # T2
    high = 3  # T3


class ZeoDetergentExpansionType(RoborockEnum):
    concentrated_detergent = 1
    detergent = 2


class ZeoSoftenerExpansionType(RoborockEnum):
    softener = 1
    softener_expansion = 2
    wool_detergent = 3


class ZeoDirtDetectionStatus(RoborockEnum):
    idle = 0
    detecting = 1
    detection_completed = 2


class ZeoError(RoborockEnum):
    none = 0  # No error
    refill_error = 1  # Refill error (E1). Check if the water tap is turned on.
    drain_error = 2  # Drain error (E2). Check the drain hose.
    door_lock_error = 3  # Door lock error (E3). Close the door properly.
    water_level_error = 4  # Drum water level error (E4).
    inverter_error = 5  # DD motor variable-frequency drive error (E5).
    heating_error = 6  # Water heater error (E6).
    temperature_error = 7  # Drum water temperature error (E7).
    communication_error = 10  # Communication error (E10).
    drying_error = 11  # Temperature error (E11).
    drying_error_e_12 = 12  # Temperature error (E12).
    drying_error_e_13 = 13  # Temperature error (E13).
    drying_error_e_14 = 14  # Temperature error (E14).
    drying_error_e_15 = 15  # Drying air heater error (E15).
    drying_error_e_16 = 16  # Fan RPM error (E16).
    drying_error_water_flow = 17  # Drying temperature protection (E17).
    drying_error_restart = 18  # Fan RPM error (E18).
    spin_error = 19  # Balance error (Unb).


class ZeoDryingMethod(RoborockEnum):
    l1 = 1  # L1, Saving
    l2 = 2  # L2, Standard
    l3 = 3  # L3, SuperFast


class ZeoSteamVolume(RoborockEnum):
    none = 0  # L0, None
    low = 1  # L1, Min
    medium = 2  # L2, Low
    high = 3  # L3, Mid
    max = 4  # L4, High


class ZeoDryAndCare(RoborockEnum):
    soft = 1
    normal = 2


class ZeoDryerStartError(RoborockEnum):
    dryer_running = 1  # Washer-Dryer Pairing cannot start: Dryer is running.
    dryer_error = 2  # Washer-Dryer Pairing cannot start: Dryer has an error.
    dryer_done = 3  # Dryer drying is complete, please remove the clothes first.
    dryer_waiting_hosting = 4  # Dryer is waiting for smart hosting.
    dryer_smart_hosting = 5  # Dryer is in smart hosting mode.
    dryer_countdown = 6  # Dryer is in preset countdown.
    dryer_network_fail = 7  # Please check the dryer network connection.


# The following are App-internal lookup tables extracted from the bundle.
# They are NOT DP protocol enums — the device never receives these values.
# They control how the official app adjusts recommended dosages or UI visibility.
#
# class Cleanser(RoborockEnum):
#     detergent = 0
#     additions = 1
#
# class Detergents(RoborockEnum):
#     concentrated = 1
#     regular = 2
#     baby = 3
#
# class Additions(RoborockEnum):
#     softener = 1
#     disinfectant = 2
#     fragrance = 3
#
# The following are App UI state enums — internal state machines used by the
# official app for page rendering and progress display.
#
# class HomePageStatus(RoborockEnum):
#     updating = 0
#     loading = 1
#     load_failed = 2
#     idle = 3
#     working = 4
#     smart_hosting = 5
#     preset = 6
#     descaling = 7
#     cloth_ready = 8
#     wait_to_dry = 9
#
# class Progress(RoborockEnum):
#     soak = 0
#     wash = 1
#     rinse = 2
#     spin = 3
#     dry = 4
#     steam_care = 5
#
# class ProgressStatus(RoborockEnum):
#     done = 0
#     doing = 1
#     will_do = 2
#
# class SmartHostStatus(RoborockEnum):
#     smart_host_waiting = 0
#     smart_hosting = 1
