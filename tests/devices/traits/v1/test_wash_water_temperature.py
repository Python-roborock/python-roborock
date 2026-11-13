"""Tests for the WashWaterTemperatureTrait class."""

from unittest.mock import AsyncMock

import pytest

from roborock.data import HomeData, RoborockDockTypeCode, RoborockDockWashWaterTemperatureCode
from roborock.device_features import NewFeatureStrBit, RoborockDockFeatures
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.wash_water_temperature import (
    WashWaterTemperatureTrait,
    get_wash_water_temperatures,
)
from roborock.exceptions import RoborockException, RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand
from tests import mock_data
from tests.devices.traits.v1.helpers import dock_types_with_capability

SAROS_10R_DOCK = RoborockDockTypeCode.shell_3s_dock


@pytest.fixture(name="wash_water_temperature")
def wash_water_temperature_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> WashWaterTemperatureTrait | None:
    """Create a WashWaterTemperatureTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.wash_water_temperature


@pytest.mark.parametrize(
    ("dock_type_code", "expected"),
    [
        (
            # Saros 10R: neither high temperature nor steam
            RoborockDockTypeCode.shell_3s_dock,
            [
                RoborockDockWashWaterTemperatureCode.room_temperature,
                RoborockDockWashWaterTemperatureCode.warm,
                RoborockDockWashWaterTemperatureCode.hot,
            ],
        ),
        (
            # Steam only
            RoborockDockTypeCode.o7h_dock,
            [
                RoborockDockWashWaterTemperatureCode.room_temperature,
                RoborockDockWashWaterTemperatureCode.hot,
                RoborockDockWashWaterTemperatureCode.steam,
            ],
        ),
        (
            # High temperature only
            RoborockDockTypeCode.k1r_dock,
            [
                RoborockDockWashWaterTemperatureCode.room_temperature,
                RoborockDockWashWaterTemperatureCode.warm,
                RoborockDockWashWaterTemperatureCode.hot,
            ],
        ),
    ],
)
def test_get_wash_water_temperatures(
    dock_type_code: RoborockDockTypeCode,
    expected: list[RoborockDockWashWaterTemperatureCode],
) -> None:
    """Test the temperatures offered for each dock family."""
    assert get_wash_water_temperatures(RoborockDockFeatures.from_dock_type(dock_type_code)) == expected


@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_washable"),
)
async def test_wash_water_temperature_available(
    wash_water_temperature: WashWaterTemperatureTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that the trait is available for washing docks."""
    assert wash_water_temperature is not None


@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_washable", expected=False),
)
async def test_unsupported_wash_water_temperature(
    wash_water_temperature: WashWaterTemperatureTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that the trait is not available for docks without mop washing."""
    assert wash_water_temperature is None


def _home_data_with_hot_wash(supported: bool) -> HomeData:
    """Return home data whose device has the hot wash towel feature bit set or cleared."""
    home_data = HomeData.from_dict(mock_data.HOME_DATA_RAW)
    device = home_data.get_all_devices()[0]
    assert device.new_feature_set is not None
    bits = int(device.new_feature_set, 16)
    mask = 1 << NewFeatureStrBit.HOT_WASH_TOWEL
    bits = bits | mask if supported else bits & ~mask
    device.new_feature_set = format(bits, "x").zfill(len(device.new_feature_set))
    return home_data


@pytest.fixture(name="trait_home_data")
def trait_home_data_fixture(request: pytest.FixtureRequest) -> HomeData:
    """Default to a device that can heat wash water, as the Saros 10R."""
    return getattr(request, "param", _home_data_with_hot_wash(True))


@pytest.mark.parametrize("trait_home_data", [_home_data_with_hot_wash(False)], indirect=True)
@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
async def test_unsupported_without_hot_wash(
    trait_home_data: HomeData,
    device: RoborockDevice,
    wash_water_temperature: WashWaterTemperatureTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that a washing dock on a device that cannot heat wash water has no temperature trait."""
    assert device.v1_properties
    assert device.is_connected
    assert not device.v1_properties.device_features.is_hot_wash_towel_supported
    assert wash_water_temperature is None


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"wash_water_temperature": 2}, RoborockDockWashWaterTemperatureCode.hot),  # Saros 10R
        ({"wash_water_temperature": 0}, RoborockDockWashWaterTemperatureCode.room_temperature),
        ({"wash_water_temperature": 9}, RoborockDockWashWaterTemperatureCode.unknown),
    ],
)
async def test_refresh_unknown_code(
    wash_water_temperature: WashWaterTemperatureTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    response: dict[str, int],
    expected: RoborockDockWashWaterTemperatureCode,
) -> None:
    """Test that refresh decodes known codes and tolerates unknown ones."""
    assert wash_water_temperature is not None
    mock_rpc_channel.send_command.side_effect = [response]

    await wash_water_temperature.refresh()

    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_WASH_WATER_TEMPERATURE)
    assert wash_water_temperature.wash_water_temperature == expected


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
async def test_options(
    wash_water_temperature: WashWaterTemperatureTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that the trait offers the temperatures of its dock."""
    assert wash_water_temperature is not None
    assert wash_water_temperature.wash_water_temperature_options == [
        RoborockDockWashWaterTemperatureCode.room_temperature,
        RoborockDockWashWaterTemperatureCode.warm,
        RoborockDockWashWaterTemperatureCode.hot,
    ]


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
@pytest.mark.parametrize(
    ("temperature"),
    [
        RoborockDockWashWaterTemperatureCode.room_temperature,
        RoborockDockWashWaterTemperatureCode.warm,
        RoborockDockWashWaterTemperatureCode.hot,
    ],
)
async def test_set_wash_water_temperature(
    wash_water_temperature: WashWaterTemperatureTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    temperature: RoborockDockWashWaterTemperatureCode,
) -> None:
    """Test setting an offered wash water temperature."""
    assert wash_water_temperature is not None

    await wash_water_temperature.set_wash_water_temperature(temperature)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_WASH_WATER_TEMPERATURE, params={"values": temperature.value}
    )
    assert wash_water_temperature.wash_water_temperature == temperature


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
@pytest.mark.parametrize(
    ("temperature"),
    [
        RoborockDockWashWaterTemperatureCode.steam,
        RoborockDockWashWaterTemperatureCode.pet_steam,
        RoborockDockWashWaterTemperatureCode.unknown,
    ],
)
async def test_set_rejects_unoffered(
    wash_water_temperature: WashWaterTemperatureTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    temperature: RoborockDockWashWaterTemperatureCode,
) -> None:
    """Test that a temperature the dock does not offer is rejected without sending."""
    assert wash_water_temperature is not None

    with pytest.raises(RoborockUnsupportedFeature):
        await wash_water_temperature.set_wash_water_temperature(temperature)

    mock_rpc_channel.send_command.assert_not_called()


@pytest.mark.parametrize(("dock_type_code"), [SAROS_10R_DOCK])
async def test_set_failure_keeps_state(
    wash_water_temperature: WashWaterTemperatureTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that a failed command leaves the temperature unchanged."""
    assert wash_water_temperature is not None
    wash_water_temperature.wash_water_temperature = RoborockDockWashWaterTemperatureCode.hot
    mock_rpc_channel.send_command.side_effect = RoborockException("boom")

    with pytest.raises(RoborockException):
        await wash_water_temperature.set_wash_water_temperature(RoborockDockWashWaterTemperatureCode.warm)

    assert wash_water_temperature.wash_water_temperature == RoborockDockWashWaterTemperatureCode.hot
