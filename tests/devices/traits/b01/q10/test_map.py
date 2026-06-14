"""Tests for the Q10 B01 map content trait."""

from pathlib import Path
from typing import cast

import pytest

from roborock.devices.traits.b01.q10.map import MapContentTrait
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.fixtures.channel_fixtures import FakeChannel

FIXTURE = Path("tests/map/testdata/b01_q10_map.bin")
TRACE_FIXTURE = Path("tests/map/testdata/b01_q10_trace.bin")


@pytest.fixture
def fake_channel() -> FakeChannel:
    return FakeChannel()


def _trait(channel: FakeChannel) -> MapContentTrait:
    return MapContentTrait(cast(MqttChannel, channel))


def _map_message(payload: bytes) -> RoborockMessage:
    return RoborockMessage(
        protocol=RoborockMessageProtocol.MAP_RESPONSE,
        payload=payload,
        version=b"B01",
    )


async def test_map_refresh_populates_image_and_rooms(fake_channel: FakeChannel) -> None:
    """refresh() triggers the device push, then parses the map payload."""
    payload = FIXTURE.read_bytes()
    fake_channel.response_queue.append(_map_message(payload))

    trait = _trait(fake_channel)
    await trait.refresh()

    assert trait.raw_api_response == payload
    assert trait.image_content is not None
    assert trait.image_content[:8] == b"\x89PNG\r\n\x1a\n"
    assert {room.id: room.name for room in trait.rooms} == {2: "Living Room", 3: "Bedroom"}
    assert trait.map_data is not None

    # The refresh trigger is a dpRequestDps (code 102) request.
    assert len(fake_channel.published_messages) == 1
    trigger = fake_channel.published_messages[0].payload
    assert trigger is not None and b'"102"' in trigger


async def test_map_refresh_times_out_without_response(
    fake_channel: FakeChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the device never pushes a map, refresh raises a clear error."""
    monkeypatch.setattr("roborock.devices.rpc.b01_q10_channel._MAP_TIMEOUT", 0.05)
    trait = _trait(fake_channel)  # no queued response -> times out
    with pytest.raises(RoborockException, match="Timed out waiting for Q10 map"):
        await trait.refresh()


def test_parse_without_refresh_raises(fake_channel: FakeChannel) -> None:
    trait = _trait(fake_channel)
    with pytest.raises(RoborockException, match="No map payload available"):
        trait.parse_map_content()


async def test_refresh_trace_populates_path_and_position(fake_channel: FakeChannel) -> None:
    """refresh_trace() parses the live position from a real ss07 trace packet."""
    fake_channel.response_queue.append(_map_message(TRACE_FIXTURE.read_bytes()))

    trait = _trait(fake_channel)
    await trait.refresh_trace()

    assert [(p.x, p.y) for p in trait.path] == [(169, 0)]
    assert trait.robot_position is not None
    assert (trait.robot_position.x, trait.robot_position.y) == (169, 0)


async def test_refresh_trace_ignores_map_packets(fake_channel: FakeChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """A map (01 01) push must not satisfy a trace request."""
    monkeypatch.setattr("roborock.devices.rpc.b01_q10_channel._MAP_TIMEOUT", 0.05)
    fake_channel.response_queue.append(_map_message(FIXTURE.read_bytes()))  # map, not trace
    trait = _trait(fake_channel)
    with pytest.raises(RoborockException, match="Timed out waiting for Q10 trace"):
        await trait.refresh_trace()
