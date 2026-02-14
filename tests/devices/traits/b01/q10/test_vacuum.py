import json
from collections.abc import Awaitable, Callable
from typing import Any, cast

import pytest

from roborock.data.b01_q10.b01_q10_code_mappings import YXCleanType, YXFanLevel
from roborock.devices.traits.b01.q10 import Q10PropertiesApi
from roborock.devices.traits.b01.q10.status import StatusTrait
from roborock.devices.traits.b01.q10.vacuum import VacuumTrait
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
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
        (lambda x: x.empty_dustbin(), {"203": 2}),
        (lambda x: x.set_clean_mode(YXCleanType.BOTH_WORK), {"137": 1}),
        (lambda x: x.set_fan_level(YXFanLevel.NORMAL), {"123": 2}),
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


def test_q10_api_has_status_trait(q10_api: Q10PropertiesApi) -> None:
    """Test that Q10PropertiesApi exposes StatusTrait."""
    assert hasattr(q10_api, "status")
    assert isinstance(q10_api.status, StatusTrait)


def test_q10_api_has_vacuum_trait(q10_api: Q10PropertiesApi) -> None:
    """Test that Q10PropertiesApi exposes VacuumTrait."""
    assert hasattr(q10_api, "vacuum")
    assert isinstance(q10_api.vacuum, VacuumTrait)


async def test_q10_api_status_refresh(q10_api: Q10PropertiesApi, fake_channel: FakeChannel) -> None:
    """Test that status trait can be refreshed via Q10PropertiesApi."""

    def build_q10_response(dps: dict[str, Any]) -> RoborockMessage:
        """Build a Q10 MQTT response message."""
        payload = {"dps": dps}
        return RoborockMessage(
            protocol=cast(RoborockMessageProtocol, 11),
            payload=json.dumps(payload).encode(),
            seq=0,
            version=b"B01",
        )

    # Queue a response with status and battery
    fake_channel.response_queue.append(build_q10_response({"121": 5, "122": 100}))

    result = await q10_api.status.refresh()

    # Verify that refresh returned data
    assert result is not None
    assert len(result) > 0

    # Verify that properties are accessible
    assert q10_api.status.battery == 100
    assert q10_api.status.state is not None
