"""Tests for typed mower command and reply payloads."""

from roborock.data import (
    MowerAck,
    MowerAckResult,
    MowerAppButton,
    MowerAppResponseError,
    MowerAudioConfig,
    MowerBattery,
    MowerBoundaryRef,
    MowerCutterFeature,
    MowerDetailState,
    MowerDirectionType,
    MowerDriveFeature,
    MowerDriveMode,
    MowerFeatureSet,
    MowerFsmState,
    MowerMainCutterHeight,
    MowerMapSelection,
    MowerMcuType,
    MowerMcuVersion,
    MowerMcuVersionItem,
    MowerMobile4GFeature,
    MowerMobile4GMode,
    MowerMowContinue,
    MowerMowingPlan,
    MowerNavFeature,
    MowerNavSolution,
    MowerNotDisturbConfig,
    MowerPlanDay,
    MowerPlanStatus,
    MowerPlanType,
    MowerPreference,
    MowerPreferenceConfig,
    MowerPreferenceEffective,
    MowerPreferenceMode,
    MowerRainfallConfig,
    MowerRainType,
    MowerRemoteMsg,
    MowerRemoteMsgType,
    MowerRobotInfo,
    MowerRobotMsg,
    MowerRobotMsgType,
    MowerRobotTask,
    MowerRtkMode,
    MowerSkuInfo,
    MowerSkuRegion,
    MowerTimePoint,
    MowerTimeSlot,
    MowerWeekday,
)

CAPTURED_PREFERENCE_REPLY = {
    "type": "MOW_PREFERENCE_CONFIG",
    "preference_config": {
        "global": {
            "mow_times": 1,
            "effective": "DAILY",
            "direction": 5,
            "keep_edge": 1,
            "mode": "GLOBAL",
            "direction_type": "AUTO_DEFLECTION",
        },
        "custom": [
            {"effective": "MANICURE", "area_name": "A1", "area_id": 2, "mode": "CUSTOM"},
            {"effective": "MANICURE", "area_name": "A2", "area_id": 3, "mode": "CUSTOM"},
            {"effective": "DAILY", "area_name": "A3", "area_id": 4, "mode": "GLOBAL"},
        ],
        "mode": "GLOBAL",
    },
}


def test_robot_msg_from_captured_preference_reply() -> None:
    reply = MowerRobotMsg.from_dict(CAPTURED_PREFERENCE_REPLY)

    assert reply.type is MowerRobotMsgType.MOW_PREFERENCE_CONFIG
    config = reply.preference_config
    assert config is not None
    assert config.mode is MowerPreferenceMode.GLOBAL
    assert config.global_preference == MowerPreference(
        mow_times=1,
        effective=MowerPreferenceEffective.DAILY,
        direction=5,
        keep_edge=1,
        mode=MowerPreferenceMode.GLOBAL,
        direction_type=MowerDirectionType.AUTO_DEFLECTION,
    )
    assert config.custom == [
        MowerPreference(
            effective=MowerPreferenceEffective.MANICURE,
            area_name="A1",
            area_id=2,
            mode=MowerPreferenceMode.CUSTOM,
        ),
        MowerPreference(
            effective=MowerPreferenceEffective.MANICURE,
            area_name="A2",
            area_id=3,
            mode=MowerPreferenceMode.CUSTOM,
        ),
        MowerPreference(
            effective=MowerPreferenceEffective.DAILY,
            area_name="A3",
            area_id=4,
            mode=MowerPreferenceMode.GLOBAL,
        ),
    ]
    # Omitted fields stay None rather than defaulting to zero.
    assert config.global_preference.height is None
    assert config.custom[0].mow_times is None


def test_preference_config_round_trips_through_as_dict() -> None:
    config = MowerRobotMsg.from_dict(CAPTURED_PREFERENCE_REPLY).preference_config
    assert config is not None

    assert MowerPreferenceConfig.from_dict(config.as_dict()) == config


def test_remote_msg_from_documented_select_example() -> None:
    """The documented MOW_SELECT request parses into a typed message."""
    msg = MowerRemoteMsg.from_dict(
        {
            "id": "1793289600002",
            "type": "APP_BUTTON",
            "app_button": "MOW_SELECT",
            "modify_map": {"boundaries": [{"id": 7}, {"id": 12}]},
        }
    )

    assert msg == MowerRemoteMsg(
        id="1793289600002",
        type=MowerRemoteMsgType.APP_BUTTON,
        app_button=MowerAppButton.MOW_SELECT,
        modify_map=MowerMapSelection(boundaries=[MowerBoundaryRef(id=7), MowerBoundaryRef(id=12)]),
    )


def test_remote_msg_accepts_integer_enum_codes() -> None:
    """Enum fields accept the wire integer as well as the protobuf name."""
    msg = MowerRemoteMsg.from_dict({"id": 42, "type": 6, "app_button": 14})

    assert msg.id == "42"
    assert msg.type is MowerRemoteMsgType.APP_BUTTON
    assert msg.app_button is MowerAppButton.MOW_GLOBAL


def test_robot_msg_robot_info_reply() -> None:
    reply = MowerRobotMsg.from_dict(
        {
            "type": "ROBOT_INFO",
            "robot_task": {"working_state": 3, "robot_detail_state": "MOW_ZIG_ZAG"},
            "mow_continue": {"continue_state": 1, "plan_mow": True, "plan_id": 7},
            "battery": {"charged": False, "percent": 64, "voltage": 20100, "current": 0},
            "mow_working_state": 18,
        }
    )

    assert reply.type is MowerRobotMsgType.ROBOT_INFO
    assert reply.robot_task == MowerRobotTask(
        working_state=MowerFsmState.SUSPEND, robot_detail_state=MowerDetailState.MOW_ZIG_ZAG
    )
    assert reply.mow_continue == MowerMowContinue(continue_state=1, plan_mow=True, plan_id=7)
    assert reply.battery == MowerBattery(charged=False, percent=64, voltage=20100, current=0)


def test_robot_msg_feature_set_accepts_decimal_strings() -> None:
    """64-bit words may be serialized as decimal strings on the JSON route."""
    reply = MowerRobotMsg.from_dict({"type": "FEATURESET", "features": {"details": ["18446744073709551615", 5]}})

    assert reply.features == MowerFeatureSet(details=[2**64 - 1, 5])


def test_robot_msg_hardware_and_version_replies() -> None:
    reply = MowerRobotMsg.from_dict(
        {
            "type": "FEATURE_INFO",
            "feature_info": {
                "cutter_feature": {"main_cutter_radius": 0.1, "main_cutter_diameter_mm": 200},
                "nav_feature": {"solution": "RTK_VISION"},
                "drive_feature": {"mode": 2},
                "mobile_4g_feature": {"mode": "INTERNAL_ESIM"},
                "sku_info": {
                    "market_name": "RockNeo Q1",
                    "declare_cut_area": 1000,
                    "battery_capacity": 5.2,
                    "region": "EU",
                    "main_cutter_height": {"min_height": 30, "max_height": 70, "step_height": 5},
                },
            },
            "mcu_version": {"project": 1, "mcu_versions": [{"mcu_type": 1, "version": "1.2.3"}]},
            "sw_version": "02.14.06",
            "serial_number": "SN123",
            "time_zone": "Europe/Copenhagen",
        }
    )

    info = reply.feature_info
    assert info is not None
    assert info.cutter_feature == MowerCutterFeature(main_cutter_radius=0.1, main_cutter_diameter_mm=200)
    assert info.nav_feature == MowerNavFeature(solution=MowerNavSolution.RTK_VISION)
    assert info.drive_feature == MowerDriveFeature(mode=MowerDriveMode.FOUR_WHEEL_DRIVE)
    assert info.mobile_4g_feature == MowerMobile4GFeature(mode=MowerMobile4GMode.INTERNAL_ESIM)
    assert info.sku_info == MowerSkuInfo(
        market_name="RockNeo Q1",
        declare_cut_area=1000,
        battery_capacity=5.2,
        region=MowerSkuRegion.EU,
        main_cutter_height=MowerMainCutterHeight(min_height=30, max_height=70, step_height=5),
    )
    assert reply.mcu_version == MowerMcuVersion(
        project=1, mcu_versions=[MowerMcuVersionItem(mcu_type=MowerMcuType.REAR_DRV_MCU, version="1.2.3")]
    )
    assert reply.sw_version == "02.14.06"
    assert reply.serial_number == "SN123"
    assert reply.time_zone == "Europe/Copenhagen"


def test_robot_msg_user_mode_config_and_schedule() -> None:
    reply = MowerRobotMsg.from_dict(
        {
            "type": "USER_MODE_CONFIG",
            "user_mode_config": {
                "rainfall_config": {"type": "RAIN_NO", "enable": True, "delay_time": 3.0},
                "not_disturb_config": {
                    "enable": True,
                    "time": [{"start": {"hour": 22, "minute": 0}, "end": {"hour": 6, "minute": 30}}],
                },
                "audio_config": {"volume": 60},
                "rtk_mode_config": 1,
                "child_lock_enable": False,
            },
            "mow_schedule": {
                "time_zone": "Europe/Copenhagen",
                "update_time": 1700000000,
                "plans": [
                    {
                        "id": 12345,
                        "type": "WEEKLY",
                        "status": "OPEN",
                        "start": 1700000000,
                        "end": 1700007200,
                        "days": [{"type": "MONDAY"}, {"type": 4}],
                        "mode": "GLOBAL",
                        "fsm_state": "MOW_GLOBAL",
                        "config": {"global": {"mow_times": 2}, "mode": "GLOBAL"},
                    }
                ],
            },
        }
    )

    config = reply.user_mode_config
    assert config is not None
    assert config.rainfall_config == MowerRainfallConfig(type=MowerRainType.RAIN_NO, enable=True, delay_time=3.0)
    assert config.not_disturb_config == MowerNotDisturbConfig(
        enable=True,
        time=[MowerTimeSlot(start=MowerTimePoint(hour=22, minute=0), end=MowerTimePoint(hour=6, minute=30))],
    )
    assert config.audio_config == MowerAudioConfig(volume=60)
    assert config.rtk_mode_config is MowerRtkMode.BASE_RTK
    assert config.child_lock_enable is False

    schedule = reply.mow_schedule
    assert schedule is not None
    assert schedule.time_zone == "Europe/Copenhagen"
    assert schedule.plans == [
        MowerMowingPlan(
            id=12345,
            type=MowerPlanType.WEEKLY,
            status=MowerPlanStatus.OPEN,
            start=1700000000,
            end=1700007200,
            days=[MowerPlanDay(type=MowerWeekday.MONDAY), MowerPlanDay(type=MowerWeekday.THURSDAY)],
            mode=MowerPreferenceMode.GLOBAL,
            fsm_state=MowerFsmState.MOW_GLOBAL,
            config=MowerPreferenceConfig(
                global_preference=MowerPreference(mow_times=2),
                mode=MowerPreferenceMode.GLOBAL,
            ),
        )
    ]


def test_robot_msg_ack_and_error() -> None:
    accepted = MowerRobotMsg.from_dict({"type": "ACK", "ack": {"result": "OK", "id": 1793289600001}})
    rejected = MowerRobotMsg.from_dict(
        {"type": "APP_RESPONSE_ERROR", "app_response_error": {"error_code": 7, "error_msg": "busy"}}
    )

    assert accepted.ack == MowerAck(result=MowerAckResult.OK, id="1793289600001")
    assert rejected.app_response_error == MowerAppResponseError(error_code=7, error_msg="busy")


def test_robot_info_detail_state_property() -> None:
    assert MowerRobotInfo().detail_state is None
    assert (
        MowerRobotInfo(robot_task=MowerRobotTask(robot_detail_state=MowerDetailState.FREE)).detail_state
        is MowerDetailState.FREE
    )


def test_robot_msg_unknown_enum_values_resolve_to_unknown() -> None:
    """Values from newer firmware resolve to the explicit unknown member."""
    reply = MowerRobotMsg.from_dict(
        {
            "type": "SOME_FUTURE_TYPE",
            "robot_task": {"working_state": 999, "robot_detail_state": 999},
            "user_mode_config": {"rtk_mode_config": 999},
        }
    )

    assert reply.type is MowerRobotMsgType.UNKNOWN
    assert reply.robot_task == MowerRobotTask(
        working_state=MowerFsmState.UNKNOWN, robot_detail_state=MowerDetailState.UNKNOWN
    )
    assert reply.user_mode_config is not None
    assert reply.user_mode_config.rtk_mode_config is MowerRtkMode.UNKNOWN


def test_partial_command_preserves_zero_false_empty_and_large_id() -> None:
    """Omitted fields stay None, while supplied zero/false/empty values survive."""
    msg = MowerRemoteMsg.from_dict(
        {"id": "18446744073709551615", "type": "APP_BUTTON", "start_index": 0, "new_task": False, "region_ids": []}
    )
    assert msg.id == "18446744073709551615"
    assert msg.start_index == 0
    assert msg.new_task is False
    assert msg.region_ids == []
    assert msg.app_button is None
    assert msg.as_dict() == {
        "id": "18446744073709551615",
        "type": "app_button",
        "startIndex": 0,
        "newTask": False,
        "regionIds": [],
    }
    assert MowerRemoteMsg.from_dict(msg.as_dict()) == msg


def test_omitted_zero_values_retain_payload_presence() -> None:
    """The model distinguishes omitted scalars from explicitly supplied wire zeroes."""
    assert MowerAck.from_dict({"id": "5"}) == MowerAck(id="5")
    assert MowerAck.from_dict({"id": "5", "result": 0}) == MowerAck(id="5", result=MowerAckResult.OK)
    assert MowerPlanDay.from_dict({}) == MowerPlanDay()
    assert MowerPlanDay.from_dict({"type": 0}) == MowerPlanDay(type=MowerWeekday.SUNDAY)
