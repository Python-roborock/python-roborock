from collections.abc import AsyncGenerator
from typing import Any

import pytest

from roborock.devices.rpc.b01_q10_channel import B01Q10Channel, Q10RpcChannel
from roborock.devices.traits.b01.q10 import Q10PropertiesApi, create
from roborock.protocols.b01_q10_protocol import Q10Message


class FakeQ10RpcChannel(Q10RpcChannel):
    """Plaintext mock RPC channel for Q10."""

    def __init__(self) -> None:
        self.published_commands: list[tuple[Any, Any]] = []

    async def send_command(self, command: Any, params: Any = None) -> None:
        self.published_commands.append((command, params))


class FakeB01Q10Channel(B01Q10Channel):
    """Plaintext mock transport channel for Q10."""

    def __init__(self) -> None:
        self.published_commands: list[tuple[Any, Any]] = []
        self.messages_to_stream: list[Q10Message] = []

    @property
    def is_connected(self) -> bool:
        return True

    @property
    def is_local_connected(self) -> bool:
        return False

    async def subscribe(self, callback: Any) -> Any:
        return lambda: None

    async def subscribe_stream(self) -> AsyncGenerator[Q10Message, None]:
        for msg in self.messages_to_stream:
            yield msg

    async def send_command(self, command: Any, params: Any = None) -> None:
        self.published_commands.append((command, params))


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeB01Q10Channel:
    return FakeB01Q10Channel()


@pytest.fixture(name="q10_api")
def q10_api_fixture(fake_channel: FakeB01Q10Channel) -> Q10PropertiesApi:
    return create(fake_channel)
