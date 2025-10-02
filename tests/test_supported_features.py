def test_supported_features_qrevo_maxv(qrevo_maxv_device_features):
    """Ensure that a QREVO MaxV has some more complicated features enabled."""
    device_features = qrevo_maxv_device_features
    assert device_features
    print("\n".join(device_features.get_supported_features()))

    num_true = sum(vars(device_features).values())
    print(num_true)
    assert num_true != 0
    assert device_features.is_dust_collection_setting_supported
    assert device_features.is_led_status_switch_supported
    assert not device_features.is_matter_supported


def test_supported_features_s7(s7_device_features):
    """Ensure that a S7 has some more basic features enabled."""
    device_features = s7_device_features
    num_true = sum(vars(device_features).values())
    assert num_true != 0
    assert device_features
    assert device_features.is_custom_mode_supported
    assert device_features.is_led_status_switch_supported
    assert not device_features.is_hot_wash_towel_supported
    num_true = sum(vars(device_features).values())
    assert num_true != 0
