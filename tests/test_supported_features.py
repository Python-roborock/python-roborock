from roborock import SHORT_MODEL_TO_ENUM
from roborock.device_features import DeviceFeatures


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

    num_true = sum(vars(device_features).values())
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
    num_true = sum(vars(device_features).values())
    assert num_true != 0
    assert device_features
    assert device_features.is_custom_mode_supported
    assert device_features.is_led_status_switch_supported
    assert not device_features.is_hot_wash_towel_supported
    num_true = sum(vars(device_features).values())
    assert num_true != 0
