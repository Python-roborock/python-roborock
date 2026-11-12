"""Tests for the DustCollectionModeTrait class."""

from unittest.mock import AsyncMock, call

import pytest

from roborock.data import RoborockDockDustCollectionModeCode, RoborockDockTypeCode
from roborock.devices.device import RoborockDevice
from roborock.devices.traits.v1.dust_collection_mode import DustCollectionModeTrait
from roborock.exceptions import RoborockException, RoborockUnsupportedFeature
from roborock.roborock_typing import RoborockCommand
from tests.devices.traits.v1.helpers import dock_types_with_capability

DUST_COLLECTION_MODE_DATA = [{"mode": 2}]


@pytest.fixture(name="dust_collection_mode")
def dust_collection_mode_trait(
    device: RoborockDevice,
    discover_features_fixture: None,
) -> DustCollectionModeTrait | None:
    """Create a DustCollectionModeTrait instance with mocked dependencies."""
    assert device.v1_properties
    return device.v1_properties.dust_collection_mode


@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_collectable"),
)
async def test_dust_collection_mode_available(
    dust_collection_mode: DustCollectionModeTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test successfully refreshing the dust collection mode."""
    assert dust_collection_mode is not None

    mock_rpc_channel.send_command.side_effect = [
        DUST_COLLECTION_MODE_DATA,
    ]

    await dust_collection_mode.refresh()

    mock_rpc_channel.send_command.assert_has_calls(
        [
            call(RoborockCommand.GET_DUST_COLLECTION_MODE),
        ]
    )

    assert dust_collection_mode.mode == RoborockDockDustCollectionModeCode.balanced


@pytest.mark.parametrize(
    ("dock_type_code"),
    dock_types_with_capability("is_collectable", expected=False),
)
async def test_unsupported_dust_collection_mode(
    dust_collection_mode: DustCollectionModeTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that the trait is not available for unsupported dock types."""
    assert dust_collection_mode is None


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
async def test_options(
    dust_collection_mode: DustCollectionModeTrait | None,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test the dust collection modes offered by the app."""
    assert dust_collection_mode is not None
    assert dust_collection_mode.dust_collection_mode_options == [
        RoborockDockDustCollectionModeCode.smart,
        RoborockDockDustCollectionModeCode.light,
        RoborockDockDustCollectionModeCode.balanced,
        RoborockDockDustCollectionModeCode.max,
    ]


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
@pytest.mark.parametrize(
    ("mode"),
    [
        RoborockDockDustCollectionModeCode.smart,
        RoborockDockDustCollectionModeCode.light,
        RoborockDockDustCollectionModeCode.balanced,
        RoborockDockDustCollectionModeCode.max,
    ],
)
async def test_set_dust_collection_mode(
    dust_collection_mode: DustCollectionModeTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    mode: RoborockDockDustCollectionModeCode,
) -> None:
    """Test setting an offered dust collection mode."""
    assert dust_collection_mode is not None

    await dust_collection_mode.set_dust_collection_mode(mode)

    mock_rpc_channel.send_command.assert_called_once_with(
        RoborockCommand.SET_DUST_COLLECTION_MODE, params={"mode": mode.value}
    )
    assert dust_collection_mode.mode == mode


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
@pytest.mark.parametrize(
    ("mode"),
    [RoborockDockDustCollectionModeCode.strong, RoborockDockDustCollectionModeCode.unknown],
)
async def test_set_rejects_unoffered(
    dust_collection_mode: DustCollectionModeTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    mode: RoborockDockDustCollectionModeCode,
) -> None:
    """Test that a mode the app does not offer is rejected without sending."""
    assert dust_collection_mode is not None

    with pytest.raises(RoborockUnsupportedFeature):
        await dust_collection_mode.set_dust_collection_mode(mode)

    mock_rpc_channel.send_command.assert_not_called()


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
async def test_set_failure_keeps_state(
    dust_collection_mode: DustCollectionModeTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
) -> None:
    """Test that a failed command leaves the mode unchanged."""
    assert dust_collection_mode is not None
    dust_collection_mode.mode = RoborockDockDustCollectionModeCode.max
    mock_rpc_channel.send_command.side_effect = RoborockException("boom")

    with pytest.raises(RoborockException):
        await dust_collection_mode.set_dust_collection_mode(RoborockDockDustCollectionModeCode.smart)

    assert dust_collection_mode.mode == RoborockDockDustCollectionModeCode.max


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"mode": 4}, RoborockDockDustCollectionModeCode.max),  # Saros 10R
        ({"mode": 3}, RoborockDockDustCollectionModeCode.strong),
        ({"mode": 5}, RoborockDockDustCollectionModeCode.unknown),
    ],
)
async def test_refresh_unknown_code(
    dust_collection_mode: DustCollectionModeTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    response: dict[str, int],
    expected: RoborockDockDustCollectionModeCode,
) -> None:
    """Test that refresh decodes known codes and tolerates unknown ones."""
    assert dust_collection_mode is not None
    mock_rpc_channel.send_command.side_effect = [response]

    await dust_collection_mode.refresh()

    mock_rpc_channel.send_command.assert_called_once_with(RoborockCommand.GET_DUST_COLLECTION_MODE)
    assert dust_collection_mode.mode == expected


@pytest.mark.parametrize(("dock_type_code"), [RoborockDockTypeCode.o4_dock])
@pytest.mark.parametrize(
    ("method_name", "command"),
    [
        ("start_dust_collection", RoborockCommand.APP_START_COLLECT_DUST),
        ("stop_dust_collection", RoborockCommand.APP_STOP_COLLECT_DUST),
    ],
)
async def test_dust_collection_actions(
    dust_collection_mode: DustCollectionModeTrait | None,
    mock_rpc_channel: AsyncMock,
    dock_type_code: RoborockDockTypeCode,
    method_name: str,
    command: RoborockCommand,
) -> None:
    """Test starting and stopping a manual dust collection."""
    assert dust_collection_mode is not None

    await getattr(dust_collection_mode, method_name)()

    mock_rpc_channel.send_command.assert_called_once_with(command)
