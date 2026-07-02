from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from roborock.devices.traits.b01.q10 import Q10PropertiesApi
from roborock.devices.traits.b01.q10.remote import RemoteTrait

from .conftest import FakeB01Q10Channel


@pytest.fixture(name="remote")
def remote_fixture(q10_api: Q10PropertiesApi) -> RemoteTrait:
    return q10_api.remote


@pytest.mark.parametrize(
    ("command_fn", "expected_payload"),
    [
        (lambda x: x.forward(), {"101": {"12": 0}}),
        (lambda x: x.left(), {"101": {"12": 2}}),
        (lambda x: x.right(), {"101": {"12": 3}}),
        (lambda x: x.stop(), {"101": {"12": 4}}),
        (lambda x: x.exit_remote(), {"101": {"12": 5}}),
    ],
)
async def test_remote_commands(
    remote: RemoteTrait,
    fake_channel: FakeB01Q10Channel,
    command_fn: Callable[[RemoteTrait], Awaitable[None]],
    expected_payload: dict[str, Any],
) -> None:
    """Test sending a remote start command."""
    await command_fn(remote)

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]

    dp_code = int(list(expected_payload.keys())[0])
    expected_params = list(expected_payload.values())[0]

    assert command.code == dp_code
    assert params == expected_params
