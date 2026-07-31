from base64 import b64decode
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import YXCleanType, YXFanLevel
from roborock.devices.traits.b01.q10 import Q10PropertiesApi
from roborock.devices.traits.b01.q10.vacuum import VacuumTrait

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


async def test_clean_zone(
    vacuum: VacuumTrait,
    fake_channel: FakeB01Q10Channel,
) -> None:
    """Test the source-verified Q10 zone payload."""
    await vacuum.clean_zone(25550, 25600, 25650, 25700, clean_count=2)

    command, params = fake_channel.published_commands[0]
    assert command.code == 201
    assert params["cmd"] == 3
    assert b64decode(params["clean_paramters"]) == bytes(
        (
            1,
            2,
            1,
            4,
            0,
            10,
            0,
            20,
            0,
            30,
            0,
            20,
            0,
            30,
            0,
            40,
            0,
            10,
            0,
            40,
            0,
            *([0] * 19),
        )
    )


@pytest.mark.parametrize("clean_count", [0, 4])
async def test_clean_zone_rejects_invalid_clean_count(
    vacuum: VacuumTrait,
    clean_count: int,
) -> None:
    """Test that the device clean-count range is validated."""
    with pytest.raises(ValueError, match="clean_count must be between 1 and 3"):
        await vacuum.clean_zone(25550, 25600, 25650, 25700, clean_count=clean_count)
