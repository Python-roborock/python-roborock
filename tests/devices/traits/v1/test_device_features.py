"""Tests for the DeviceFeaturesTrait related functionality."""

import pytest
from syrupy import SnapshotAssertion

from roborock.data import HomeDataDevice
from roborock.data.v1.v1_containers import ConsumableField, StatusField
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.consumeable import ConsumableTrait
from roborock.devices.traits.v1.status import StatusTrait
from tests import mock_data

V1_DEVICES = {
    k: HomeDataDevice.from_dict(device) for k, device in mock_data.DEVICES.items() if device.get("pv") == "1.0"
}


@pytest.mark.parametrize(
    ("device_info"),
    V1_DEVICES.values(),
    ids=list(V1_DEVICES.keys()),
)
async def test_is_attribute_supported(
    device_info: HomeDataDevice,
    device: RoborockDevice,
    discover_features_fixture: None,
    snapshot: SnapshotAssertion,
) -> None:
    """Test if a field is supported."""
    assert device.v1_properties is not None
    assert device.v1_properties.device_features is not None
    device_features_trait = device.v1_properties.device_features

    is_v1_supported = {
        field.value: device_features_trait.is_field_supported(StatusTrait, field) for field in StatusField
    }
    assert is_v1_supported == snapshot


@pytest.mark.parametrize(
    ("device_info"),
    V1_DEVICES.values(),
    ids=list(V1_DEVICES.keys()),
)
async def test_is_consumable_field_supported(
    device_info: HomeDataDevice,
    device: RoborockDevice,
    discover_features_fixture: None,
    snapshot: SnapshotAssertion,
) -> None:
    """Test if a field is supported."""
    assert device.v1_properties is not None
    assert device.v1_properties.device_features is not None
    device_features_trait = device.v1_properties.device_features

    is_v1_supported = {
        field.value: device_features_trait.is_field_supported(ConsumableTrait, field) for field in ConsumableField
    }
    assert is_v1_supported == snapshot
