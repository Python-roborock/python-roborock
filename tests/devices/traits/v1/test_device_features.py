"""Tests for the DeviceFeaturesTrait related functionality."""

from unittest.mock import AsyncMock

import pytest
from syrupy import SnapshotAssertion

from roborock.data import HomeDataDevice
from roborock.data.v1.v1_containers import ConsumableField, StatusField
from roborock.devices.cache import DeviceCache
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.consumeable import ConsumableTrait
from roborock.devices.traits.v1.status import StatusTrait
from roborock.exceptions import RoborockParsingException
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


@pytest.mark.parametrize("payload", [[], ["ok"]], ids=["empty", "non-dict"])
async def test_refresh_unexpected_list_keeps_state(
    device: RoborockDevice,
    device_cache: DeviceCache,
    mock_rpc_channel: AsyncMock,
    payload: list,
) -> None:
    """An empty or non-dict init status reply raises a parsing error and keeps the previous features."""
    assert device.v1_properties is not None
    device_features_trait = device.v1_properties.device_features
    previous = device_features_trait.as_dict()
    # Force a device read instead of the cached features from discovery.
    cache_data = await device_cache.get()
    cache_data.device_features = None
    await device_cache.set(cache_data)
    mock_rpc_channel.send_command.return_value = payload

    with pytest.raises(
        RoborockParsingException,
        match=r"Failed to parse APP_GET_INIT_STATUS response for DeviceFeaturesTrait.*ValueError.*",
    ):
        await device_features_trait.refresh()

    assert device_features_trait.as_dict() == previous
