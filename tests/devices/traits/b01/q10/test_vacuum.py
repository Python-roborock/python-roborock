from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import (
    Q10CleanCount,
    YXCleanLine,
    YXCleanType,
    YXFanLevel,
    YXWaterLevel,
)
from roborock.devices.traits.b01.q10 import Q10PropertiesApi, create
from roborock.devices.traits.b01.q10.vacuum import VacuumTrait
from roborock.exceptions import RoborockException

from .conftest import FakeB01Q10Channel


@pytest.fixture(name="vacuum")
def vacuum_fixture(q10_api: Q10PropertiesApi) -> VacuumTrait:
    return q10_api.vacuum


@pytest.mark.parametrize(
    ("command_fn", "expected_payload"),
    [
        # Payloads verified live against ss07 hardware.
        (lambda x: x.start_clean(), {"201": 1}),
        (lambda x: x.clean_segments([9]), {"201": {"cmd": 2, "clean_paramters": [9]}}),
        (lambda x: x.clean_segments([1, 2]), {"201": {"cmd": 2, "clean_paramters": [1, 2]}}),
        (lambda x: x.spot_clean(), {"201": 5}),
        (lambda x: x.pause_clean(), {"204": 0}),
        (lambda x: x.resume_clean(), {"205": 0}),
        (lambda x: x.stop_clean(), {"206": 0}),
        (lambda x: x.return_to_dock(), {"202": 5}),
        (lambda x: x.empty_dustbin(), {"203": 2}),
        (lambda x: x.set_clean_mode(YXCleanType.VAC_AND_MOP), {"137": 1}),
        (lambda x: x.set_fan_level(YXFanLevel.BALANCED), {"123": 2}),
        (lambda x: x.set_water_level(YXWaterLevel.HIGH), {"124": 3}),
        (lambda x: x.set_clean_count(Q10CleanCount.TWICE), {"136": 2}),
        (lambda x: x.set_clean_line(YXCleanLine.FINE), {"101": {"78": 2}}),
    ],
)
async def test_vacuum_commands(
    vacuum: VacuumTrait,
    fake_channel: FakeB01Q10Channel,
    command_fn: Callable[[VacuumTrait], Awaitable[None]],
    expected_payload: dict[str, Any],
) -> None:
    """Test sending a vacuum start command."""
    await command_fn(vacuum)

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]

    dp_code = int(list(expected_payload.keys())[0])
    expected_params = list(expected_payload.values())[0]

    assert command.code == dp_code
    assert params == expected_params


@pytest.mark.parametrize(
    "command",
    [
        lambda vacuum: vacuum.set_clean_mode(YXCleanType.UNKNOWN),
        lambda vacuum: vacuum.set_fan_level(YXFanLevel.UNKNOWN),
        lambda vacuum: vacuum.set_water_level(YXWaterLevel.UNKNOWN),
        lambda vacuum: vacuum.set_clean_count(Q10CleanCount.UNKNOWN),
        lambda vacuum: vacuum.set_clean_mode(1),  # type: ignore[arg-type]
        lambda vacuum: vacuum.set_fan_level(1),  # type: ignore[arg-type]
        lambda vacuum: vacuum.set_water_level(1),  # type: ignore[arg-type]
        lambda vacuum: vacuum.set_clean_count(1),  # type: ignore[arg-type]
        lambda vacuum: vacuum.set_clean_line(1),  # type: ignore[arg-type]
    ],
)
async def test_setting_commands_reject_unknown_without_publish(
    vacuum: VacuumTrait,
    fake_channel: FakeB01Q10Channel,
    command: Callable[[VacuumTrait], Awaitable[None]],
) -> None:
    with pytest.raises(ValueError, match="supported"):
        await command(vacuum)

    assert fake_channel.published_commands == []


@pytest.mark.parametrize(
    "command",
    [
        lambda vacuum: vacuum.set_water_level(YXWaterLevel.HIGH),
        lambda vacuum: vacuum.set_clean_count(Q10CleanCount.TWICE),
        lambda vacuum: vacuum.set_clean_line(YXCleanLine.FINE),
    ],
)
async def test_advanced_cleaning_commands_reject_unverified_model(
    fake_channel: FakeB01Q10Channel,
    command: Callable[[VacuumTrait], Awaitable[None]],
) -> None:
    vacuum = create(fake_channel, model="roborock.vacuum.ss99").vacuum

    with pytest.raises(RoborockException, match="only verified"):
        await command(vacuum)

    assert vacuum.advanced_cleaning_supported is False
    assert fake_channel.published_commands == []
