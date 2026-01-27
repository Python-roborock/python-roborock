import json
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from roborock.devices.traits.b01.q10 import Q10PropertiesApi
from roborock.devices.traits.b01.q10.vacuum import VacuumTrait
from tests.fixtures.channel_fixtures import FakeChannel


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


@pytest.fixture(name="q10_api")
def q10_api_fixture(fake_channel: FakeChannel) -> Q10PropertiesApi:
    return Q10PropertiesApi(fake_channel)  # type: ignore[arg-type]


@pytest.fixture(name="vacuumm")
def vacuumm_fixture(q10_api: Q10PropertiesApi) -> VacuumTrait:
    return q10_api.vacuum


@pytest.mark.parametrize(
    ("command_fn", "expected_payload"),
    [
        (lambda x: x.start_clean(), {"201": {"cmd": 1}}),
        (lambda x: x.pause_clean(), {"204": {}}),
        (lambda x: x.resume_clean(), {"205": {}}),
        (lambda x: x.stop_clean(), {"206": {}}),
        (lambda x: x.return_to_dock(), {"203": {}}),
    ],
)
async def test_vacuum_commands(
    vacuumm: VacuumTrait,
    fake_channel: FakeChannel,
    command_fn: Callable[[VacuumTrait], Awaitable[None]],
    expected_payload: dict[str, Any],
) -> None:
    """Test sending a vacuum start command."""
    await command_fn(vacuumm)

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.payload
    payload_data = json.loads(message.payload.decode())
    assert payload_data == {"dps": expected_payload}
