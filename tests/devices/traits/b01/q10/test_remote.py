import json
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from roborock.devices.traits.b01.q10 import Q10PropertiesApi
from roborock.devices.traits.b01.q10.remote import RemoteTrait
from tests.fixtures.channel_fixtures import FakeChannel


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


@pytest.fixture(name="q10_api")
def q10_api_fixture(fake_channel: FakeChannel) -> Q10PropertiesApi:
    return Q10PropertiesApi(fake_channel)  # type: ignore[arg-type]


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
        (lambda x: x.exit(), {"101": {"12": 5}}),
    ],
)
async def test_remote_commands(
    remote: RemoteTrait,
    fake_channel: FakeChannel,
    command_fn: Callable[[RemoteTrait], Awaitable[None]],
    expected_payload: dict[str, Any],
) -> None:
    """Test sending a remote start command."""
    await command_fn(remote)

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.payload
    payload_data = json.loads(message.payload.decode())
    assert payload_data == {"dps": expected_payload}
