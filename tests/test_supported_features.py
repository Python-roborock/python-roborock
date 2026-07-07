from dataclasses import asdict

import pytest
from syrupy import SnapshotAssertion

from roborock import SHORT_MODEL_TO_ENUM
from roborock.data.code_mappings import RoborockProductNickname
from roborock.data.v1 import RoborockDockTypeCode
from roborock.device_features import DeviceFeatures, RoborockDockFeatures, is_valid_dock, is_wash_n_fill_dock
from tests import mock_data


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
        (RoborockDockTypeCode.type_27_dock, True, True),
        (RoborockDockTypeCode.k1c_lite_dock, True, True),
        (RoborockDockTypeCode.shell_2e_lite_dock, True, True),
    ],
)
def test_dock_features(dock_type: RoborockDockTypeCode, is_collectable: bool, is_washable: bool) -> None:
    dock_features = RoborockDockFeatures.from_dock_type(dock_type)

    assert dock_features.has_dock is (dock_type not in {RoborockDockTypeCode.unknown, RoborockDockTypeCode.o0_dock})
    assert dock_features.is_collectable is is_collectable
    assert dock_features.is_washable is is_washable
    assert is_valid_dock(dock_type) is dock_features.has_dock
    assert is_wash_n_fill_dock(dock_type) is dock_features.is_washable


def test_dock_feature_flags_from_rr_api() -> None:
    """Verify dock-specific feature flags that are not currently trait gates."""
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.shell_3s_dock).is_auto_sterilize_supported
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.o4_dock).is_cleaning_brush_supported
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.o4_dock).is_clean_fluid_auto_delivery_supported
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.couple_dock).is_hatch_door_dock_cool_fan_supported
    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.shell_2e_lite_dock).is_special_support_wash_temp


def test_dock_feature_flags_with_am_variants_from_rr_api() -> None:
    """Verify dock flags where the app distinguishes AM and non-AM docks by the same type code."""
    assert not RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.shell_3_dock
    ).is_clean_fluid_auto_delivery_supported
    assert RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.shell_3_dock, has_am=True
    ).is_clean_fluid_auto_delivery_supported

    assert RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.shell_3_dock).is_clean_carousel_self_clean_supported
    assert not RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.shell_3_dock, has_am=True
    ).is_clean_carousel_self_clean_supported

    assert not RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.o5_dock).is_water_updown_drain_supported
    assert RoborockDockFeatures.from_dock_type(
        RoborockDockTypeCode.o5_dock, has_am=True
    ).is_water_updown_drain_supported


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
