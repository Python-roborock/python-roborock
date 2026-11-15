"""Tests for the CarpetBoostTrait class."""

from dataclasses import replace
from unittest.mock import AsyncMock, call

import pytest

from roborock.data import HomeDataDevice
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.carpet_boost import CarpetBoostTrait
from roborock.exceptions import RoborockParsingException, RoborockTimeout
from roborock.roborock_typing import RoborockCommand
from tests import mock_data

# The Saros 10R reports is_carpet_supported (robot_new_features bit 512); the copy has only that bit cleared.
SAROS_10R = mock_data.DEVICE_PRODUCT_PAIRS["home_data_device_saros_10r.json"][0]
SAROS_10R_WITHOUT_CARPET = replace(SAROS_10R, new_feature_set="0005075028ED3EDDCFFF8F7F7EFEFDFF")

# Captured from a Qrevo 2 Pro (roborock.vacuum.a294) via get_carpet_mode
CARPET_MODE_RESPONSE = [
    {"enable": 1, "current_integral": 1000, "current_high": 500, "current_low": 1000, "stall_time": 10}
]
TUNING = {"current_integral": 1000, "current_high": 500, "current_low": 1000, "stall_time": 10}


@pytest.fixture(name="carpet_boost")
def carpet_boost_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> CarpetBoostTrait | None:
    """Return the trait created by feature discovery."""
    assert device.v1_properties
    return device.v1_properties.carpet_boost


@pytest.mark.parametrize("device_info", [SAROS_10R_WITHOUT_CARPET])
async def test_unsupported_without_carpet_feature(
    carpet_boost: CarpetBoostTrait | None,
    device_info: HomeDataDevice,
) -> None:
    """The trait is not created when the device does not report carpet support."""
    assert carpet_boost is None


@pytest.mark.parametrize("device_info", [SAROS_10R])
async def test_refresh(
    carpet_boost: CarpetBoostTrait | None,
    device_info: HomeDataDevice,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Refreshing reads the boost setting; the motor tuning values are not exposed."""
    assert carpet_boost is not None
    assert not carpet_boost.is_on
    mock_rpc_channel.send_command.return_value = CARPET_MODE_RESPONSE

    await carpet_boost.refresh()

    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_CARPET_MODE)
    assert carpet_boost.is_on
    assert carpet_boost.as_dict() == {"enabled": 1}


@pytest.mark.parametrize("device_info", [SAROS_10R])
@pytest.mark.parametrize(
    "response",
    [
        pytest.param([{"enable": 1, "current_integral": 1000}], id="missing-field"),
        pytest.param([{**CARPET_MODE_RESPONSE[0], "current_integral": None}], id="null-field"),
        pytest.param([], id="empty-list"),
    ],
)
async def test_refresh_malformed_response(
    carpet_boost: CarpetBoostTrait | None,
    device_info: HomeDataDevice,
    mock_rpc_channel: AsyncMock,
    response: list,
) -> None:
    """A malformed response is rejected and the previously read values are kept for writes."""
    assert carpet_boost is not None
    mock_rpc_channel.send_command.return_value = CARPET_MODE_RESPONSE
    await carpet_boost.refresh()

    mock_rpc_channel.send_command.return_value = response
    with pytest.raises(RoborockParsingException):
        await carpet_boost.refresh()
    assert carpet_boost.is_on

    mock_rpc_channel.send_command.reset_mock()
    await carpet_boost.disable()
    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_CARPET_MODE, params=[{"enable": 0, **TUNING}]
    )


@pytest.mark.parametrize("device_info", [SAROS_10R])
async def test_disable_and_enable(
    carpet_boost: CarpetBoostTrait | None,
    device_info: HomeDataDevice,
    mock_rpc_channel: AsyncMock,
) -> None:
    """Writes send the boost setting with the motor tuning values from the last refresh."""
    assert carpet_boost is not None
    mock_rpc_channel.send_command.return_value = CARPET_MODE_RESPONSE
    await carpet_boost.refresh()
    mock_rpc_channel.send_command.reset_mock()

    await carpet_boost.disable()
    assert not carpet_boost.is_on
    await carpet_boost.enable()
    assert carpet_boost.is_on

    assert mock_rpc_channel.send_command.call_args_list == [
        call(RoborockCommand.SET_CARPET_MODE, params=[{"enable": 0, **TUNING}]),
        call(RoborockCommand.SET_CARPET_MODE, params=[{"enable": 1, **TUNING}]),
    ]


@pytest.mark.parametrize("device_info", [SAROS_10R])
async def test_first_write_reads_tuning(
    carpet_boost: CarpetBoostTrait | None,
    device_info: HomeDataDevice,
    mock_rpc_channel: AsyncMock,
) -> None:
    """A write before any refresh reads the tuning values first, then writes."""
    assert carpet_boost is not None
    mock_rpc_channel.send_command.side_effect = [CARPET_MODE_RESPONSE, {}, {}]

    await carpet_boost.disable()
    assert not carpet_boost.is_on
    await carpet_boost.enable()
    assert carpet_boost.is_on

    assert mock_rpc_channel.send_command.call_args_list == [
        call(RoborockCommand.GET_CARPET_MODE),
        call(RoborockCommand.SET_CARPET_MODE, params=[{"enable": 0, **TUNING}]),
        call(RoborockCommand.SET_CARPET_MODE, params=[{"enable": 1, **TUNING}]),
    ]


@pytest.mark.parametrize("device_info", [SAROS_10R])
@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        pytest.param(RoborockTimeout("timeout"), RoborockTimeout, id="timeout"),
        pytest.param([[]], RoborockParsingException, id="malformed"),
    ],
)
async def test_first_write_failed_read(
    carpet_boost: CarpetBoostTrait | None,
    device_info: HomeDataDevice,
    mock_rpc_channel: AsyncMock,
    side_effect: Exception | list,
    expected_error: type[Exception],
) -> None:
    """If the initial tuning read fails, the error propagates and nothing is written."""
    assert carpet_boost is not None
    mock_rpc_channel.send_command.side_effect = side_effect

    with pytest.raises(expected_error):
        await carpet_boost.enable()

    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_CARPET_MODE)
    assert not carpet_boost.is_on
