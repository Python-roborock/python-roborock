"""Code mappings for Roborock mower devices."""

from roborock.data.code_mappings import RoborockEnum


class RoborockMowerStateCode(RoborockEnum):
    """Detailed mower operating state reported by DPS 123."""

    unknown = -999
    idle = 0

    map_initializing = 1
    map_undocking = 2
    map_undock_fault = 3
    map_locating = 4
    map_prepare_boundary = 5
    map_prepare_island = 6
    map_prepare_path = 7
    map_boundary = 8
    map_island = 9
    map_path = 10
    map_boundary_auto = 11
    map_erasing = 12
    map_save = 13
    map_wait = 14
    map_recoverable_fault = 15
    map_fault = 16
    map_emergency_stop = 17
    map_waiting_fault = 18

    mow_initializing = 51
    mow_undocking = 52
    mow_locating = 53
    mow_adjust_cutter = 54
    mow_zig_zag = 55
    mow_edge = 56
    mow_goto = 57
    mow_suspend = 58
    mow_recoverable_fault = 59
    mow_fault = 60
    mow_docked_rainfall = 61
    mow_docked_do_not_disturb = 62
    mow_docked_low_battery = 63
    mow_wait = 64
    mow_prepare_remote = 65
    mow_remote = 66
    mow_emergency_stop = 67
    mow_docked_manual = 68
    mow_dock_fault = 69
    mow_remote_undocking = 70
    mow_to_dock_initializing = 71
    mow_to_dock_locating = 72
    mow_to_dock_recoverable_fault = 73
    mow_to_dock_fault = 74
    mow_to_dock_emergency_stop = 75
    mow_to_dock_charging = 76
    mow_to_dock_charge_completed = 77

    free = 101
    free_initializing = 102
    free_locating = 103
    free_docked_manual = 104
    free_docked_mow_end = 105
    free_docked_plan_end = 106
    free_emergency_stop = 107
    free_recoverable_fault = 108
    free_fault = 109

    charge_charging = 151
    charge_completed = 152
    charge_waiting = 153
    charge_fault = 154
