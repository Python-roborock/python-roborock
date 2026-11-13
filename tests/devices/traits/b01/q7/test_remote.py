from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from roborock.devices.traits.b01.q7 import Q7PropertiesApi, RemoteTrait
from roborock.roborock_message import RoborockB01Props
from roborock.roborock_typing import RoborockB01Q7Methods

from .conftest import FakeQ7Channel


@pytest.fixture(name="remote")
def remote_fixture(q7_api: Q7PropertiesApi) -> RemoteTrait:
    return q7_api.remote


@pytest.mark.parametrize(
    ("command_fn", "expected_commands"),
    [
        (lambda x: x.stop(), [(RoborockB01Q7Methods.SET_PROP, {RoborockB01Props.SWEEP_TYPE: 5})]),
        (lambda x: x.forward(), [(RoborockB01Q7Methods.SET_DIRECTION, {"direction": 1})]),
        (lambda x: x.left(), [(RoborockB01Q7Methods.SET_DIRECTION, {"direction": 2})]),
        (lambda x: x.right(), [(RoborockB01Q7Methods.SET_DIRECTION, {"direction": 3})]),
        (
            lambda x: x.exit_remote(),
            [
                (RoborockB01Q7Methods.SET_DIRECTION, {"direction": 0}),
                (RoborockB01Q7Methods.SET_PROP, {RoborockB01Props.SWEEP_TYPE: 0}),
            ],
        ),
    ],
)
async def test_remote_commands(
    remote: RemoteTrait,
    fake_channel: FakeQ7Channel,
    command_fn: Callable[[RemoteTrait], Awaitable[None]],
    expected_commands: list[tuple[Any, Any]],
) -> None:
    """Test remote control commands are sent with the verified Q7 payloads."""
    await command_fn(remote)

    assert fake_channel.published_commands == expected_commands
