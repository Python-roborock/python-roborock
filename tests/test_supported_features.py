import logging
from dataclasses import asdict, fields
from unittest.mock import AsyncMock

import pytest
from syrupy import SnapshotAssertion

from roborock import SHORT_MODEL_TO_ENUM
from roborock.data import HomeDataProduct
from roborock.data.code_mappings import RoborockProductNickname
from roborock.data.v1 import RoborockDockTypeCode
from roborock.device_features import (
    PRODUCT_FEATURE_MAP,
    DeviceFeatures,
    RoborockDockFeatures,
    is_valid_dock,
    is_wash_n_fill_dock,
)
from roborock.devices.cache import CacheData, DeviceCache, InMemoryCache
from roborock.devices.traits.v1.device_features import DeviceFeaturesTrait
from roborock.roborock_typing import RoborockCommand
from tests import mock_data

# RR_API DockConfigs snapshot from the Qrevo Edge 2 bundle decoded on 2026-07-11.
RR_API_DOCK_TYPES = {
    0: "o0_dock",
    1: "o1_dock",
    2: "o2_dock",
    3: "o3_dock",
    5: "oc_dock",
    6: "o3_plus_dock",
    7: "o4_dock",
    8: "pearl_dock",
    9: "pearl_plus_dock",
    10: "o5_dock",
    11: "shell_2s_dock",
    13: "couple_dock",
    14: "shell_3_dock",
    15: "shell_2c_dock",
    16: "shell_3s_dock",
    17: "k1_dock",
    18: "o6_dock",
    19: "k1c_dock",
    20: "k1s_dock",
    21: "shell_e_dock",
    22: "shell_2e_dock",
    23: "shell_3c_dock",
    24: "hera_dock",
    26: "k1s_pro_dock",
    27: "type_27_dock",
    28: "k1c_lite_dock",
    29: "k1r_dock",
    30: "shell_2e_lite_dock",
    31: "shell_4rc_dock",
    32: "shell_4r_dock",
    33: "shell_4p_dock",
    34: "shell_4s_dock",
    35: "o7_dock",
    37: "k1d_dock",
    38: "shell_3p_dock",
    39: "shell_4d_dock",
    40: "shell_2e_heat_dock",
    41: "f1_dock",
    42: "f1r_dock",
    43: "f2r_dock",
    44: "f1s_dock",
    45: "o7h_dock",
    46: "f1c_dock",
}


def test_supported_features_qrevo_maxv():
    """Ensure that a QREVO MaxV has some more complicated features enabled."""
    model = "roborock.vacuum.a87"
    product_nickname = SHORT_MODEL_TO_ENUM.get(model.split(".")[-1])
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=4499197267967999,
        new_feature_info_str="508A977F7EFEFFFF",
        feature_info=[111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125],
        product_nickname=product_nickname,
    )
    assert device_features
    print("\n".join(device_features.get_supported_features()))

    num_true = sum(v for v in vars(device_features).values() if isinstance(v, bool))
    print(num_true)
    assert num_true != 0
    assert device_features.is_dust_collection_setting_supported
    assert device_features.is_led_status_switch_supported
    assert device_features.is_shake_mop_set_supported
    assert device_features.is_clean_route_setting_supported
    assert not device_features.is_matter_supported
    print(device_features)


def test_supported_features_s7():
    """Ensure that a S7 has some more basic features enabled."""

    model = "roborock.vacuum.a15"
    product_nickname = SHORT_MODEL_TO_ENUM.get(model.split(".")[-1])
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=636084721975295,
        new_feature_info_str="0000000000002000",
        feature_info=[111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125],
        product_nickname=product_nickname,
    )
    num_true = sum(v for v in vars(device_features).values() if isinstance(v, bool))
    assert num_true != 0
    assert device_features
    assert device_features.is_custom_mode_supported
    assert device_features.is_led_status_switch_supported
    assert device_features.is_shake_mop_set_supported
    assert device_features.is_clean_route_setting_supported
    assert not device_features.is_hot_wash_towel_supported
    num_true = sum(v for v in vars(device_features).values() if isinstance(v, bool))
    assert num_true != 0


def test_device_feature_serialization(snapshot: SnapshotAssertion) -> None:
    """Test serialization and deserialization of DeviceFeatures."""
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=636084721975295,
        new_feature_info_str="0000000000002000",
        feature_info=[111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 122, 123, 124, 125],
        product_nickname=RoborockProductNickname.TANOSS,
    )
    serialized = device_features.as_dict()
    deserialized = DeviceFeatures.from_dict(serialized)
    assert deserialized == device_features


def test_new_feature_str_missing():
    """Ensure that DeviceFeatures missing fields can still be created."""
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str="",
        feature_info=[],
        product_nickname=None,
    )
    # Check arbitrary fields that are false by default
    assert not device_features.is_dust_collection_setting_supported
    assert not device_features.is_hot_wash_towel_supported
    assert not device_features.is_show_clean_finish_reason_supported


@pytest.mark.parametrize("product_nickname", list(RoborockProductNickname), ids=lambda product: product.name)
def test_product_feature_map(product_nickname: RoborockProductNickname, snapshot: SnapshotAssertion) -> None:
    """Snapshot the product features of every nickname so changes show up per product."""
    assert PRODUCT_FEATURE_MAP[product_nickname] == snapshot


@pytest.mark.parametrize(
    ("roller_mop_bit", "expected_mop_support"),
    [
        (0, False),
        (1 << 128, True),
    ],
)
def test_roller_mop_product_features(roller_mop_bit: int, expected_mop_support: bool) -> None:
    """Test a roller-mop model without a mop module gets its mop support from the roller-mop bit."""
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str=f"{roller_mop_bit:X}",
        feature_info=[],
        product_nickname=RoborockProductNickname.BERYLS,
    )

    assert device_features.is_max_plus_mode_supported
    assert device_features.is_ai_recognition_setting_supported
    assert device_features.is_pure_clean_mop_supported
    assert not device_features.is_new_remote_view_supported
    assert device_features.is_support_water_mode is expected_mop_support
    assert device_features.is_customized_clean_supported is expected_mop_support
    assert device_features.is_clean_route_setting_supported is expected_mop_support


def test_clean_route_setting_support_from_shake_mop_flag() -> None:
    """Test clean-route capability includes the runtime shake-mop flag."""
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=262144,
        new_feature_info_str="",
        feature_info=[],
        product_nickname=None,
    )

    assert device_features.is_shake_mop_set_supported
    assert device_features.is_clean_route_setting_supported


def test_clean_route_setting_support_from_spin_mop_model() -> None:
    """Test clean-route capability includes model-level spin-mop support."""
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str="",
        feature_info=[],
        product_nickname=RoborockProductNickname.PEARLSLITE,
    )

    assert not device_features.is_shake_mop_set_supported
    assert not device_features.is_roller_mop_supported
    assert device_features.is_clean_route_setting_supported


@pytest.mark.parametrize(
    ("feature_bit", "expected"),
    [
        (127, False),
        (128, True),
        (129, False),
    ],
)
def test_mop_support_from_roller_mop_bit(feature_bit: int, expected: bool) -> None:
    """Test only the RR_API roller-mop bit adds mop support to models without a mop module."""
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str=f"{1 << feature_bit:X}",
        feature_info=[],
        product_nickname=None,
    )

    assert device_features.is_roller_mop_supported is expected
    assert device_features.is_clean_route_setting_supported is expected
    assert device_features.is_support_water_mode is expected
    assert device_features.is_customized_clean_supported is expected
    # Smart mop water also needs its own bit, so the roller-mop bit alone does not enable it.
    assert device_features.is_smart_water_supported is False


@pytest.mark.parametrize(
    ("feature_bits", "expected"),
    [
        ([], False),
        ([128], False),
        ([166], False),
        ([128, 166], True),
    ],
)
def test_smart_water_support_needs_roller_mop(feature_bits: list[int], expected: bool) -> None:
    """Test smart mop water needs both the smart-water bit and the roller-mop bit."""
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str=f"{sum(1 << bit for bit in feature_bits):X}",
        feature_info=[],
        product_nickname=None,
    )

    assert device_features.is_smart_water_supported is expected


@pytest.mark.parametrize(
    ("new_feature_info", "expected"),
    [
        (0, False),
        (262143, False),
        (262144, True),
        (262145, True),
        (1 << 60, False),
    ],
)
def test_shake_mop_feature_bit_boundary(new_feature_info: int, expected: bool) -> None:
    """Test only feature values containing the shake-mop bit enable it."""
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=new_feature_info,
        new_feature_info_str="",
        feature_info=[],
        product_nickname=None,
    )

    assert device_features.is_shake_mop_set_supported is expected
    assert device_features.is_clean_route_setting_supported is expected


# NewFeatureStr bits read by the newest Roborock app plugins.
APP_NEW_FEATURE_STR_BITS = {
    6: "is_support_silent_ota_supported",
    121: "is_product_experience_improvement_supported",
    122: "is_floor_plan_map_supported",
    125: "is_invasion_detection_supported",
    129: "is_change_mop_supported",
    130: "is_forbid_pure_mop_supported",
    131: "is_dynamic_obstacle_supplementary_clean_supported",
    132: "is_zone_replenish_clean_supported",
    133: "is_exhibition_for_dance_and_pick_supported",
    134: "is_dock_independent_mop_wash_supported",
    135: "is_intelligent_object_search_supported",
    136: "is_stair_door_sill_supported",
    137: "is_no_mop_avoid_stroll_supported",
    138: "is_curtain_supported",
    139: "is_support_retractable_mop_supported",
    140: "is_support_multiple_dnd_time_periods_supported",
    141: "is_iot_base_msg_supported",
    142: "is_vibrate_mop_supported",
    143: "is_cancel_one_time_sweep_then_mop_supported",
    144: "is_support_ai_wash_towel_supported",
    145: "is_show_sewage_box_clean_state_supported",
    146: "is_support_baidu_voice_control_supported",
    147: "is_carpet_stair_clean_supported",
    148: "is_support_wash_phase_pumping_supported",
    149: "is_support_download_voice_ota_url_supported",
    150: "is_support_only_smart_wash_towel_supported",
    151: "is_support_app_backup_and_restore_supported",
    152: "is_patrol_photo_storage_optimization_supported",
    153: "is_support_clean_before_dust_collection_supported",
    154: "is_zone_replenish_clean_switch_supported",
    155: "is_pet_album_supported",
    156: "is_door_sill_mat_supported",
    158: "is_timer_interval_days_and_temp_off_supported",
    160: "is_no_arm_right_brush_stretch_supported",
    161: "is_multi_skip_clean_supported",
    164: "is_replenish_zone_edit_supported",
    165: "is_timer_segment_zone_hybrid_supported",
    166: "is_smart_water_supported",
    167: "is_firmware_cloud_backup_privacy_supported",
    168: "is_sound_record_supported",
    169: "is_swing_arm_wheel_control_supported",
}

# Bits that only count together with another bit, mapped to that bit and its field.
NEW_FEATURE_STR_BIT_PREREQUISITES = {
    166: (128, "is_roller_mop_supported"),
}


@pytest.mark.parametrize(("feature_bit", "feature_name"), APP_NEW_FEATURE_STR_BITS.items())
def test_new_feature_str_bits_from_app(feature_bit: int, feature_name: str) -> None:
    """Test each app NewFeatureStr bit enables only its own capability."""
    feature_bits = [feature_bit]
    expected = {feature_name}
    if prerequisite := NEW_FEATURE_STR_BIT_PREREQUISITES.get(feature_bit):
        prerequisite_bit, prerequisite_name = prerequisite
        feature_bits.append(prerequisite_bit)
        expected.add(prerequisite_name)
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str=f"{sum(1 << bit for bit in feature_bits):X}",
        feature_info=[],
        product_nickname=None,
    )

    enabled = {
        f.name
        for f in fields(DeviceFeatures)
        if "new_feature_str_bit" in f.metadata and getattr(device_features, f.name)
    }
    assert enabled == expected


def test_new_feature_str_bits_from_app_all_set() -> None:
    """Test the app NewFeatureStr bits are read from one long feature string."""
    feature_bits = set(APP_NEW_FEATURE_STR_BITS) | {bit for bit, _ in NEW_FEATURE_STR_BIT_PREREQUISITES.values()}
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str=f"{sum(1 << bit for bit in feature_bits):X}",
        feature_info=[],
        product_nickname=None,
    )

    assert all(getattr(device_features, name) for name in APP_NEW_FEATURE_STR_BITS.values())


@pytest.mark.parametrize(
    ("product_nickname", "expected"),
    [
        (RoborockProductNickname.BERYLLITE, True),
        (RoborockProductNickname.CORALPROSAW, True),
        (RoborockProductNickname.BERYL, False),
        (RoborockProductNickname.CORALPRO, False),
        (None, False),
    ],
)
def test_wash_phase_pumping_support_from_model(
    product_nickname: RoborockProductNickname | None, expected: bool
) -> None:
    """Test the app enables wash phase pumping for BerylLite and CoralProSAw without the feature bit."""
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str="",
        feature_info=[],
        product_nickname=product_nickname,
    )

    assert device_features.is_support_wash_phase_pumping_supported is expected


@pytest.mark.parametrize(
    ("feature_id", "feature_name"),
    [
        (111, "is_fds_endpoint_supported"),
        (112, "is_auto_split_segments_supported"),
        (114, "is_order_segment_clean_supported"),
        (116, "is_map_segment_supported"),
    ],
)
def test_robot_features_from_app(feature_id: int, feature_name: str) -> None:
    """Test the app robotFeatures ids enable their capability."""
    # RubySC is one of the models that needs robotFeatures 116 for map segments.
    without_feature = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str="",
        feature_info=[feature_id - 1, feature_id + 1],
        product_nickname=RoborockProductNickname.RUBYSC,
    )
    with_feature = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str="",
        feature_info=[feature_id],
        product_nickname=RoborockProductNickname.RUBYSC,
    )

    assert getattr(without_feature, feature_name) is False
    assert getattr(with_feature, feature_name) is True


@pytest.mark.parametrize(
    ("product_nickname", "expected"),
    [
        (RoborockProductNickname.RUBYSC, False),
        (RoborockProductNickname.RUBYPLUS, False),
        (RoborockProductNickname.RUBYSLITE, True),
        (RoborockProductNickname.TANOSS, True),
        (None, True),
    ],
)
def test_map_segment_support_from_model(product_nickname: RoborockProductNickname | None, expected: bool) -> None:
    """Test only RubySC and RubyPlus need robotFeatures 116 for map segments."""
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str="",
        feature_info=[],
        product_nickname=product_nickname,
    )

    assert device_features.is_map_segment_supported is expected


@pytest.mark.parametrize("product_nickname", [RoborockProductNickname.RUBYSC, RoborockProductNickname.RUBYPLUS])
def test_map_segment_support_from_feature_id(product_nickname: RoborockProductNickname) -> None:
    """Test RubySC and RubyPlus support map segments when they report robotFeatures 116."""
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=0,
        new_feature_info_str="",
        feature_info=[116],
        product_nickname=product_nickname,
    )

    assert device_features.is_map_segment_supported is True


async def test_from_dict_rejects_legacy_missing_capabilities(caplog: pytest.LogCaptureFixture) -> None:
    """Test stale cached features become a quiet cache miss."""
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=262144,
        new_feature_info_str="",
        feature_info=[],
        product_nickname=None,
    )
    legacy_data = device_features.as_dict()
    for legacy_missing_key in (
        "isAiRecognitionSettingSupported",
        "isAiRecognitionObstacleSupported",
        "isRollerMopSupported",
    ):
        del legacy_data[legacy_missing_key]

    restored = DeviceFeatures.from_dict(legacy_data)

    assert restored is None

    with caplog.at_level(logging.ERROR):
        cache_data = CacheData.from_dict({"deviceInfo": {"legacy-device": {"deviceFeatures": legacy_data}}})

    assert cache_data.device_info["legacy-device"].device_features is None
    assert not caplog.records

    cache = InMemoryCache()
    await cache.set(cache_data)
    device_cache = DeviceCache("legacy-device", cache)
    product = HomeDataProduct.from_dict(mock_data.PRODUCTS["home_data_product_a27.json"])
    trait = DeviceFeaturesTrait(product, device_cache)
    rpc_channel = AsyncMock()
    rpc_channel.send_command.return_value = [mock_data.APP_GET_INIT_STATUS]
    trait._rpc_channel = rpc_channel

    await trait.refresh()

    rpc_channel.send_command.assert_awaited_once_with(RoborockCommand.APP_GET_INIT_STATUS)
    assert trait.is_ai_recognition_setting_supported
    assert trait.is_ai_recognition_obstacle_supported
    assert (await device_cache.get()).device_features is trait


@pytest.mark.parametrize(
    ("dock_type", "is_collectable", "is_washable"),
    [
        (RoborockDockTypeCode.unknown, False, False),
        (RoborockDockTypeCode.o0_dock, False, False),
        (RoborockDockTypeCode.o1_dock, True, False),
        (RoborockDockTypeCode.o2_dock, False, True),
        (RoborockDockTypeCode.o3_dock, True, True),
        (RoborockDockTypeCode.oc_dock, True, False),
        (RoborockDockTypeCode.o3_plus_dock, True, True),
        (RoborockDockTypeCode.o4_dock, True, True),
        (RoborockDockTypeCode.pearl_dock, True, True),
        (RoborockDockTypeCode.pearl_plus_dock, True, True),
        (RoborockDockTypeCode.o5_dock, True, True),
        (RoborockDockTypeCode.shell_2s_dock, True, True),
        (RoborockDockTypeCode.couple_dock, True, True),
        (RoborockDockTypeCode.shell_3_dock, True, True),
        (RoborockDockTypeCode.shell_2c_dock, True, True),
        (RoborockDockTypeCode.shell_3s_dock, True, True),
        (RoborockDockTypeCode.k1_dock, True, True),
        (RoborockDockTypeCode.o6_dock, True, True),
        (RoborockDockTypeCode.k1c_dock, True, True),
        (RoborockDockTypeCode.k1s_dock, True, True),
        (RoborockDockTypeCode.shell_e_dock, True, True),
        (RoborockDockTypeCode.shell_2e_dock, True, True),
        (RoborockDockTypeCode.shell_3c_dock, True, True),
        (RoborockDockTypeCode.hera_dock, True, True),
        (RoborockDockTypeCode.k1s_pro_dock, True, True),
        (RoborockDockTypeCode.type_27_dock, True, True),
        (RoborockDockTypeCode.k1c_lite_dock, True, True),
        (RoborockDockTypeCode.k1r_dock, True, True),
        (RoborockDockTypeCode.shell_2e_lite_dock, True, True),
        (RoborockDockTypeCode.shell_4rc_dock, True, True),
        (RoborockDockTypeCode.shell_4r_dock, True, True),
        (RoborockDockTypeCode.shell_4p_dock, True, True),
        (RoborockDockTypeCode.shell_4s_dock, True, True),
        (RoborockDockTypeCode.o7_dock, True, True),
        (RoborockDockTypeCode.k1d_dock, True, True),
        (RoborockDockTypeCode.shell_3p_dock, True, True),
        (RoborockDockTypeCode.shell_4d_dock, True, True),
        (RoborockDockTypeCode.shell_2e_heat_dock, True, True),
        (RoborockDockTypeCode.f1_dock, True, True),
        (RoborockDockTypeCode.f1r_dock, True, True),
        (RoborockDockTypeCode.f2r_dock, True, True),
        (RoborockDockTypeCode.f1s_dock, True, True),
        (RoborockDockTypeCode.o7h_dock, True, True),
        (RoborockDockTypeCode.f1c_dock, True, True),
        (RoborockDockTypeCode.type_49_dock, True, True),
    ],
)
def test_dock_features(dock_type: RoborockDockTypeCode, is_collectable: bool, is_washable: bool) -> None:
    dock_features = RoborockDockFeatures.from_dock_type(dock_type)

    assert dock_features.has_dock is (dock_type not in {RoborockDockTypeCode.unknown, RoborockDockTypeCode.o0_dock})
    assert dock_features.is_collectable is is_collectable
    assert dock_features.is_washable is is_washable
    assert is_valid_dock(dock_type) is dock_features.has_dock
    assert is_wash_n_fill_dock(dock_type) is dock_features.is_washable


def test_all_rr_api_dock_types_are_mapped() -> None:
    """Keep the enum synchronized with the RR_API DockConfigs snapshot."""
    mapped_docks = {
        dock_type.value: dock_type.name
        for dock_type in RoborockDockTypeCode
        if dock_type is not RoborockDockTypeCode.unknown
    }

    observed_docks = {49: "type_49_dock"}  # P30 Pro; not present in the older RR_API snapshot.
    assert mapped_docks == RR_API_DOCK_TYPES | observed_docks


def test_dock_feature_flags_from_rr_api() -> None:
    """Verify dock-specific feature flags that are not currently trait gates."""
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.shell_3s_dock).is_auto_sterilize_supported
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.o4_dock).is_cleaning_brush_supported
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.o4_dock).is_clean_fluid_auto_delivery_supported
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.couple_dock).is_hatch_door_dock_cool_fan_supported
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.shell_2e_lite_dock).is_special_support_wash_temp
    assert not RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.shell_2e_heat_dock
    ).is_clean_fluid_auto_delivery_supported
    assert not RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.shell_2e_heat_dock
    ).is_water_updown_drain_supported
    assert RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.shell_3p_dock
    ).is_clean_carousel_self_clean_supported
    assert RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.shell_3p_dock
    ).is_double_serial_communication_supported
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.o7_dock).is_only_x_series
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.o7_dock).is_clean_fluid_auto_delivery_supported
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.o7h_dock).is_steam_wash_supported
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.f1_dock).is_simple_wash_mode_supported
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.f1r_dock).is_no_water_flow_carousel


def test_dock_feature_flags_with_am_variants_from_rr_api() -> None:
    """Verify dock flags where the app distinguishes AM and non-AM docks by the same type code."""
    assert not RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.shell_3_dock
    ).is_clean_fluid_auto_delivery_supported
    assert RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.shell_3_dock, has_am=True
    ).is_clean_fluid_auto_delivery_supported
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.o5_dock).is_clean_fluid_auto_delivery_supported
    assert RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.o5_dock, has_am=True
    ).is_clean_fluid_auto_delivery_supported

    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.shell_3_dock).is_clean_carousel_self_clean_supported
    assert not RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.shell_3_dock, has_am=True
    ).is_clean_carousel_self_clean_supported

    assert not RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.o5_dock).is_water_updown_drain_supported
    assert RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.o5_dock, has_am=True
    ).is_water_updown_drain_supported
    assert RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.k1s_dock, has_am=True
    ).is_water_updown_drain_supported
    assert RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.shell_3c_dock, has_am=True
    ).is_water_updown_drain_supported

    shell_4rc = RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.shell_4rc_dock)
    shell_4rc_am = RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.shell_4rc_dock, has_am=True)
    assert shell_4rc.is_clean_carousel_self_clean_supported
    assert not shell_4rc_am.is_clean_carousel_self_clean_supported
    assert not shell_4rc.is_water_updown_drain_supported
    assert shell_4rc_am.is_water_updown_drain_supported
    assert not shell_4rc.is_clean_fluid_auto_delivery_supported
    assert not shell_4rc_am.is_clean_fluid_auto_delivery_supported
    assert shell_4rc.is_high_tmp_water_supported
    assert shell_4rc_am.is_high_tmp_water_supported
    assert not shell_4rc.is_double_serial_communication_supported
    assert shell_4rc_am.is_double_serial_communication_supported


@pytest.mark.parametrize(
    ("device_filename"),
    list(mock_data.DEVICE_PRODUCT_PAIRS.keys()),
)
def test_device_features_from_home_data(
    device_filename: str,
    snapshot: SnapshotAssertion,
) -> None:
    """Test DeviceFeatures constructed from real testdata devices and products.

    For each paired device+product in testdata, construct DeviceFeatures from the
    featureSet/newFeatureSet home data fields and assert the full feature dict
    matches the snapshot. This catches regressions in feature-flag decoding
    across all real device samples.
    """
    device, product = mock_data.DEVICE_PRODUCT_PAIRS[device_filename]
    device_features = DeviceFeatures.from_feature_flags(
        new_feature_info=int(device.feature_set or "0"),
        new_feature_info_str=device.new_feature_set or "",
        feature_info=[],
        product_nickname=product.product_nickname,
    )
    feature_dict = {k: v for k, v in asdict(device_features).items() if isinstance(v, bool)}
    assert feature_dict == snapshot
