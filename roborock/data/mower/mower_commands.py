"""Typed request and reply payloads for the mower remote_pb protocol.

Fields may be absent from partial replies. ``as_dict()`` uses the normal
RoborockBase representation; it is not a remote_pb wire serializer.
An absent scalar or enum field stays ``None`` here, even when protobuf may
have omitted its default value. This records payload presence, not whether a setting is unset;
the protocol/consumer layer must interpret defaults for each message type.
"""

from dataclasses import dataclass
from typing import Any, ClassVar

from roborock.data.containers import RoborockBase

from .mower_code_mappings import (
    MowerAckResult,
    MowerAppButton,
    MowerBoundaryPerception,
    MowerDetailState,
    MowerDirectionType,
    MowerDriveMode,
    MowerFsmEvent,
    MowerFsmState,
    MowerMcuType,
    MowerMobile4GMode,
    MowerNavSolution,
    MowerPlanStatus,
    MowerPlanType,
    MowerPreferenceEffective,
    MowerPreferenceMode,
    MowerRainType,
    MowerRemoteMsgType,
    MowerRobotMsgType,
    MowerRtkMode,
    MowerSkuRegion,
    MowerWeekday,
)

__all__ = [
    "MowerAck",
    "MowerPose",
    "MowerBoundaryRef",
    "MowerMapSelection",
    "MowerTimePoint",
    "MowerTimeSlot",
    "MowerNotDisturbConfig",
    "MowerRainfallConfig",
    "MowerAudioConfig",
    "MowerPreference",
    "MowerPreferenceConfig",
    "MowerPlanDay",
    "MowerMowingPlan",
    "MowerMowSchedule",
    "MowerHeightMotorParameter",
    "MowerRobotTask",
    "MowerMowContinue",
    "MowerFeatureSet",
    "MowerMainCutterHeight",
    "MowerSkuInfo",
    "MowerCutterFeature",
    "MowerNavFeature",
    "MowerDriveFeature",
    "MowerMobile4GFeature",
    "MowerFeatureInfo",
    "MowerMcuVersionItem",
    "MowerMcuVersion",
    "MowerBattery",
    "MowerAppResponseError",
    "MowerUserModeConfig",
    "MowerRemoteMsg",
    "MowerRobotMsg",
    "MowerRobotInfo",
    "MowerDeviceInfo",
]


@dataclass
class MowerAck(RoborockBase):
    """Request acceptance (``rock.common.Ack``)."""

    result: MowerAckResult | None = None
    id: str | None = None
    """Echo of the 64-bit request id, carried as a decimal string like ``RemoteMsg.id``."""


@dataclass
class MowerPose(RoborockBase):
    """Local map pose (``rock.common.Pose``)."""

    x: float | None = None
    y: float | None = None
    yaw: float | None = None


@dataclass
class MowerBoundaryRef(RoborockBase):
    """Reference to a saved boundary by ID, optionally by name on older firmware."""

    id: int | None = None
    name: str | None = None


@dataclass
class MowerMapSelection(RoborockBase):
    """The subset of ``rock.common.Map`` carried in ``RemoteMsg.modify_map``.

    Selected mowing uses ``boundaries``; map file requests use ``name``.
    """

    name: str | None = None
    boundaries: list[MowerBoundaryRef] | None = None


@dataclass
class MowerTimePoint(RoborockBase):
    """Hour and minute of day (``rock.common.TimePoint``)."""

    hour: int | None = None
    minute: int | None = None


@dataclass
class MowerTimeSlot(RoborockBase):
    """Start and end time of day (``rock.common.TimeSlot``)."""

    start: MowerTimePoint | None = None
    end: MowerTimePoint | None = None


@dataclass
class MowerNotDisturbConfig(RoborockBase):
    """Animal-protection hours (``rock.common.NotDisturb``).

    Protected mower-local periods can cause a return to charge and later
    continuation.
    """

    enable: bool | None = None
    time: list[MowerTimeSlot] | None = None


@dataclass
class MowerRainfallConfig(RoborockBase):
    """Rain protection (``rock.common.RainFall``).

    ``delay_time`` is the resume delay in hours after rain; the app offers 0,
    3 and 8. ``type`` is the reported rain intensity and is read-only.
    """

    type: MowerRainType | None = None
    enable: bool | None = None
    delay_time: float | None = None


@dataclass
class MowerAudioConfig(RoborockBase):
    """Voice volume (``rock.common.AudioConfig``)."""

    volume: int | None = None


@dataclass
class MowerPreference(RoborockBase):
    """Mowing preference for the whole lawn or one area (``MowPreference``)."""

    mow_times: int | None = None
    effective: MowerPreferenceEffective | None = None
    direction: int | None = None
    """Mowing direction angle in degrees."""
    height: int | None = None
    """Cutting height in device units, within the height motor limits."""
    keep_edge: int | None = None
    """Boundary trimming passes: 0 none, 1 one pass, 2 two passes."""
    area_name: str | None = None
    area_id: int | None = None
    mode: MowerPreferenceMode | None = None
    direction_type: MowerDirectionType | None = None
    custom_zig_zag: int | None = None
    custom_enable_cutter: bool | None = None
    total_times: int | None = None
    height_bound_trim: bool | None = None
    boundary_perception: MowerBoundaryPerception | None = None


@dataclass
class MowerPreferenceConfig(RoborockBase):
    """Global and per-area preferences (``MowAreasConfig``).

    The wire field ``global`` is a Python keyword, so it is exposed as
    ``global_preference``; parsing accepts both names. ``as_dict`` keeps the
    canonical field name. Protocol serialization must apply ``WIRE_ALIASES``
    and serialize enum names separately from these domain values.
    """

    WIRE_ALIASES: ClassVar[dict[str, str]] = {"global_preference": "global"}
    """One-off field-to-wire-key rename applied by the protocol serializer."""

    global_preference: MowerPreference | None = None
    custom: list[MowerPreference] | None = None
    mode: MowerPreferenceMode | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        """Create the config, accepting the ``global`` wire key."""
        if isinstance(data, dict) and "global" in data:
            data = {("global_preference" if key == "global" else key): value for key, value in data.items()}
        return super().from_dict(data)


@dataclass
class MowerPlanDay(RoborockBase):
    """One weekday entry of a weekly plan (``rock.common.Week``)."""

    type: MowerWeekday | None = None


@dataclass
class MowerMowingPlan(RoborockBase):
    """A scheduled mowing plan (``MowingPlan``).

    Times are Unix seconds in the mower's time zone. ``fsm_state`` selects the
    scheduled task (``MOW_GLOBAL``, ``MOW_EDGE`` or ``MOW_SELECT``).
    """

    id: int | None = None
    type: MowerPlanType | None = None
    status: MowerPlanStatus | None = None
    start: int | None = None
    end: int | None = None
    days: list[MowerPlanDay] | None = None
    mode: MowerPreferenceMode | None = None
    config: MowerPreferenceConfig | None = None
    fsm_state: MowerFsmState | None = None


@dataclass
class MowerMowSchedule(RoborockBase):
    """All plans stored on the mower (``MowSchedule``)."""

    plans: list[MowerMowingPlan] | None = None
    time_zone: str | None = None
    update_time: int | None = None


@dataclass
class MowerHeightMotorParameter(RoborockBase):
    """Cutting height limits (``rock.common.HeightMotorParameter``).

    A valid height lies on a ``step`` multiple between ``min`` and ``max``.
    """

    max: int | None = None
    min: int | None = None
    step: int | None = None


@dataclass
class MowerRobotTask(RoborockBase):
    """Current task state (``rock.common.RobotTask``)."""

    working_state: MowerFsmState | None = None
    """The coarse task-machine state; the detailed state is separate."""
    robot_detail_state: MowerDetailState | None = None


@dataclass
class MowerMowContinue(RoborockBase):
    """Retained-task continuation state (``rock.common.MowContinue``)."""

    continue_state: int | None = None
    plan_mow: bool | None = None
    mow_dock_manual: bool | None = None
    plan_id: int | None = None
    plan_start: int | None = None
    plan_end: int | None = None


@dataclass
class MowerFeatureSet(RoborockBase):
    """Capability words (``rock.common.FeatureSet``).

    Each entry is an unsigned 64-bit word; bit numbering follows
    :class:`~roborock.data.mower.MowerFeature`.
    """

    details: list[int] | None = None


@dataclass
class MowerMainCutterHeight(RoborockBase):
    """SKU cutting height data (``rock.common.MainCutterHeight``)."""

    default_height: int | None = None
    calibrate_height: int | None = None
    min_height: int | None = None
    max_height: int | None = None
    step_height: int | None = None


@dataclass
class MowerSkuInfo(RoborockBase):
    """Market SKU data (``rock.common.SkuInfo``)."""

    market_name: str | None = None
    declare_cut_area: int | None = None
    charge_current: int | None = None
    battery_capacity: float | None = None
    region: MowerSkuRegion | None = None
    real_cut_area: int | None = None
    main_cutter_height: MowerMainCutterHeight | None = None


@dataclass
class MowerCutterFeature(RoborockBase):
    """Cutter hardware (``rock.common.CutterFeature``)."""

    main_cutter_radius: float | None = None
    main_cutter_diameter_mm: int | None = None


@dataclass
class MowerNavFeature(RoborockBase):
    """Positioning hardware (``rock.common.NavFeature``)."""

    solution: MowerNavSolution | None = None


@dataclass
class MowerDriveFeature(RoborockBase):
    """Drive train (``rock.common.DriveFeature``)."""

    mode: MowerDriveMode | None = None


@dataclass
class MowerMobile4GFeature(RoborockBase):
    """Cellular hardware (``rock.common.Mobile4GFeature``)."""

    mode: MowerMobile4GMode | None = None


@dataclass
class MowerFeatureInfo(RoborockBase):
    """Hardware descriptors (``rock.common.FeatureInfo``)."""

    cutter_feature: MowerCutterFeature | None = None
    nav_feature: MowerNavFeature | None = None
    drive_feature: MowerDriveFeature | None = None
    mobile_4g_feature: MowerMobile4GFeature | None = None
    sku_info: MowerSkuInfo | None = None


@dataclass
class MowerMcuVersionItem(RoborockBase):
    """One controller firmware version (``rock.common.McuVersionItem``)."""

    mcu_type: MowerMcuType | None = None
    version: str | None = None


@dataclass
class MowerMcuVersion(RoborockBase):
    """Controller firmware versions (``rock.common.McuVersion``)."""

    project: int | None = None
    mcu_versions: list[MowerMcuVersionItem] | None = None


@dataclass
class MowerBattery(RoborockBase):
    """Battery details (``rock.common.Battery``)."""

    charged: bool | None = None
    percent: int | None = None
    voltage: int | None = None
    current: int | None = None


@dataclass
class MowerAppResponseError(RoborockBase):
    """Error returned for a rejected request (``rock.common.AppResponseError``)."""

    error_code: int | None = None
    error_msg: str | None = None


@dataclass
class MowerUserModeConfig(RoborockBase):
    """User settings reported by ``GET_USER_MODE_CONFIG`` (``rock.common.UserModeConfig``).

    Only the consumer-facing settings are modelled; installation, network,
    anti-theft and video configuration are not yet exposed.
    """

    rainfall_config: MowerRainfallConfig | None = None
    not_disturb_config: MowerNotDisturbConfig | None = None
    audio_config: MowerAudioConfig | None = None
    rtk_mode_config: MowerRtkMode | None = None
    lift_alarm_enable: bool | None = None
    child_lock_enable: bool | None = None


@dataclass
class MowerRemoteMsg(RoborockBase):
    """A structured command (``rock.common.remote.RemoteMsg``).

    ``id`` is a 64-bit request identifier carried as a decimal string on the
    JSON route. Only the payload fields with dedicated support are modelled.
    """

    id: str | None = None
    type: MowerRemoteMsgType | None = None
    app_button: MowerAppButton | None = None
    modify_map: MowerMapSelection | None = None
    target: MowerPose | None = None
    start_index: int | None = None
    play_audio: int | None = None
    record_time_stamp: int | None = None
    mow_preference: MowerPreference | None = None
    mow_preference_config: MowerPreferenceConfig | None = None
    not_disturb_config: MowerNotDisturbConfig | None = None
    rainfall_config: MowerRainfallConfig | None = None
    audio_config: MowerAudioConfig | None = None
    mowing_plan: MowerMowingPlan | None = None
    region_ids: list[int] | None = None
    new_task: bool | None = None
    clear_user_code: int | None = None
    cache_fsm_event: int | None = None
    button_with_map_selfcheck_result: MowerFsmEvent | None = None
    lift_alarm_enable: bool | None = None
    child_lock_enable: bool | None = None


@dataclass
class MowerRobotMsg(RoborockBase):
    """A structured reply or event (``rock.common.RobotMsg``).

    Only the fields consumed by the library are modelled; a reply carries the
    subset relevant to its ``type``.
    """

    id: str | None = None
    type: MowerRobotMsgType | None = None
    ack: MowerAck | None = None
    app_response_error: MowerAppResponseError | None = None
    map_names: list[str] | None = None
    battery: MowerBattery | None = None
    preference_config: MowerPreferenceConfig | None = None
    user_mode_config: MowerUserModeConfig | None = None
    features: MowerFeatureSet | None = None
    height_motor_parameter: MowerHeightMotorParameter | None = None
    mow_schedule: MowerMowSchedule | None = None
    next_plan: MowerMowingPlan | None = None
    time_zone: str | None = None
    mow_working_state: MowerFsmState | None = None
    sku_info: MowerSkuInfo | None = None
    sw_version: str | None = None
    mcu_version: MowerMcuVersion | None = None
    project: int | None = None
    robot_task: MowerRobotTask | None = None
    mow_continue: MowerMowContinue | None = None
    feature_info: MowerFeatureInfo | None = None
    serial_number: str | None = None


@dataclass
class MowerRobotInfo(RoborockBase):
    """Task and battery state read with ``GET_ROBOT_INFO``."""

    robot_task: MowerRobotTask | None = None
    battery: MowerBattery | None = None
    mow_continue: MowerMowContinue | None = None
    mow_working_state: MowerFsmState | None = None

    @property
    def detail_state(self) -> MowerDetailState | None:
        """The detailed task state, if reported."""
        return self.robot_task.robot_detail_state if self.robot_task is not None else None


@dataclass
class MowerDeviceInfo(RoborockBase):
    """Identity and version information read from the mower."""

    sw_version: str | None = None
    mcu_version: MowerMcuVersion | None = None
    serial_number: str | None = None
    sku_info: MowerSkuInfo | None = None
    time_zone: str | None = None
