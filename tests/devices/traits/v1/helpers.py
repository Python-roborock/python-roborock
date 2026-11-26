"""Shared helpers for V1 trait tests."""

from roborock.data import HomeData, RoborockDockTypeCode
from roborock.device_features import NewFeatureStrBit, RoborockDockFeatures
from tests import mock_data


def dock_types_with_capability(capability: str, expected: bool = True) -> list[RoborockDockTypeCode]:
    """Return dock types matching a RoborockDockFeatures capability."""
    return [
        dock_type
        for dock_type in RoborockDockTypeCode
        if getattr(RoborockDockFeatures.from_dock_type(dock_type), capability) is expected
    ]


def home_data_with_feature_bit(bit: NewFeatureStrBit, supported: bool) -> HomeData:
    """Return home data whose first device has a new feature bit set or cleared."""
    home_data = HomeData.from_dict(mock_data.HOME_DATA_RAW)
    device = home_data.get_all_devices()[0]
    assert device.new_feature_set is not None
    bits = int(device.new_feature_set, 16)
    mask = 1 << bit
    bits = bits | mask if supported else bits & ~mask
    device.new_feature_set = format(bits, "x").zfill(len(device.new_feature_set))
    return home_data
