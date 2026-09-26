"""Tests for the typed Zeo traits (command/settings/status).

Unlike the lazy design, these traits are built eagerly and are projected from
the same raw datapoints that feed ``values``: unsolicited pushes, query
responses, and the initial cloud status snapshot.
"""

import pytest

from roborock.data.zeo.zeo_code_mappings import ZeoMode
from roborock.devices.traits.a01 import ZeoApi
from roborock.devices.traits.a01.device_feature import build_force_load_dp_list
from roborock.roborock_message import RoborockZeoProtocol
from tests.fixtures.channel_fixtures import FakeChannel
from tests.protocols.common import build_a01_message

STATE = int(RoborockZeoProtocol.STATE)
MODE = int(RoborockZeoProtocol.MODE)
WASHING_LEFT = int(RoborockZeoProtocol.WASHING_LEFT)


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


@pytest.fixture(name="zeo_api")
def zeo_api_fixture(fake_channel: FakeChannel) -> ZeoApi:
    return ZeoApi(fake_channel)  # type: ignore[arg-type]


async def test_zeo_traits_are_built_eagerly(zeo_api: ZeoApi) -> None:
    """The typed traits exist (and are empty) before any message arrives."""
    assert zeo_api.settings.mode is None
    assert zeo_api.status.state is None
    assert zeo_api.command is not None


async def test_zeo_traits_track_pushes(zeo_api: ZeoApi, fake_channel: FakeChannel) -> None:
    """Unsolicited pushes are projected into the typed traits."""
    fake_channel.response_queue.append(build_a01_message({int(dp): 0 for dp in build_force_load_dp_list(None)}))
    await zeo_api.start()

    fake_channel.notify_subscribers(build_a01_message({STATE: 6, MODE: 1, WASHING_LEFT: 12}))

    assert zeo_api.settings.mode == ZeoMode.wash
    assert zeo_api.status.state is not None
    assert zeo_api.status.washing_left == 12

    # A partial push only updates the reported DP, leaving the rest intact.
    fake_channel.notify_subscribers(build_a01_message({MODE: 2}))

    assert zeo_api.settings.mode == ZeoMode.wash_and_dry
    assert zeo_api.status.washing_left == 12


async def test_zeo_traits_seeded_from_initial_status(fake_channel: FakeChannel) -> None:
    """The cloud status snapshot seeds the traits without a device round trip."""
    api = ZeoApi(fake_channel, initial_status={STATE: 6, MODE: 1})  # type: ignore[arg-type]

    assert api.settings.mode == ZeoMode.wash
    assert api.status.state is not None
    # The shared `values` view is seeded from the same snapshot.
    assert api.values[RoborockZeoProtocol.STATE] == "spinning"
