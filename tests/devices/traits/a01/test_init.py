import datetime
import json
from typing import Any

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from freezegun import freeze_time

from roborock.devices.traits.a01 import DyadApi, ZeoApi, create
from roborock.devices.traits.a01.device_feature import build_force_load_dp_list
from roborock.roborock_message import RoborockDyadDataProtocol, RoborockMessageProtocol, RoborockZeoProtocol
from roborock.testing.a01_simulator import DEFAULT_DYAD_PRODUCT
from tests.fixtures.channel_fixtures import FakeChannel
from tests.protocols.common import build_a01_message


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


@pytest.fixture(name="dyad_api")
def dyad_api_fixture(fake_channel: FakeChannel) -> DyadApi:
    return DyadApi(fake_channel)  # type: ignore[arg-type]


@pytest.fixture(name="zeo_api")
def zeo_api_fixture(fake_channel: FakeChannel) -> ZeoApi:
    return ZeoApi(fake_channel)  # type: ignore[arg-type]


async def test_dyad_api_query_values(dyad_api: DyadApi, fake_channel: FakeChannel):
    """Test that DyadApi currently returns raw values without conversion."""
    fake_channel.response_queue.append(
        build_a01_message(
            {
                209: 1,  # POWER
                201: 6,  # STATUS
                207: 3,  # WATER_LEVEL
                214: 120,  # MESH_LEFT
                215: 90,  # BRUSH_LEFT
                227: 85,  # SILENT_MODE_START_TIME
                229: "3,4,5",  # RECENT_RUN_TIME
                230: 123456,  # TOTAL_RUN_TIME
                222: 1,  # STAND_LOCK_AUTO_RUN
                224: 0,  # AUTO_DRY_MODE
            }
        )
    )
    result = await dyad_api.query_values(
        [
            RoborockDyadDataProtocol.POWER,
            RoborockDyadDataProtocol.STATUS,
            RoborockDyadDataProtocol.WATER_LEVEL,
            RoborockDyadDataProtocol.MESH_LEFT,
            RoborockDyadDataProtocol.BRUSH_LEFT,
            RoborockDyadDataProtocol.SILENT_MODE_START_TIME,
            RoborockDyadDataProtocol.RECENT_RUN_TIME,
            RoborockDyadDataProtocol.TOTAL_RUN_TIME,
            RoborockDyadDataProtocol.STAND_LOCK_AUTO_RUN,
            RoborockDyadDataProtocol.AUTO_DRY_MODE,
        ]
    )
    assert result == {
        RoborockDyadDataProtocol.POWER: 1,
        RoborockDyadDataProtocol.STATUS: "self_clean_deep_cleaning",
        RoborockDyadDataProtocol.WATER_LEVEL: "l3",
        RoborockDyadDataProtocol.MESH_LEFT: 352800,
        RoborockDyadDataProtocol.BRUSH_LEFT: 354600,
        RoborockDyadDataProtocol.SILENT_MODE_START_TIME: datetime.time(1, 25),
        RoborockDyadDataProtocol.RECENT_RUN_TIME: [3, 4, 5],
        RoborockDyadDataProtocol.TOTAL_RUN_TIME: 123456,
        RoborockDyadDataProtocol.STAND_LOCK_AUTO_RUN: True,
        RoborockDyadDataProtocol.AUTO_DRY_MODE: False,
    }

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == b"A01"
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    assert payload_data["dps"] == {"10000": "[209, 201, 207, 214, 215, 227, 229, 230, 222, 224]"}
    assert "t" in payload_data


@pytest.mark.parametrize(
    ("query", "response", "expected_result"),
    [
        (
            [RoborockDyadDataProtocol.STATUS],
            {
                7: 1,
                RoborockDyadDataProtocol.STATUS: 3,
                9999: -3,
            },
            {
                RoborockDyadDataProtocol.STATUS: "charging",
            },
        ),
        (
            [RoborockDyadDataProtocol.SILENT_MODE_START_TIME],
            {
                RoborockDyadDataProtocol.SILENT_MODE_START_TIME: "invalid",
            },
            {
                RoborockDyadDataProtocol.SILENT_MODE_START_TIME: None,
            },
        ),
        (
            [RoborockDyadDataProtocol.SILENT_MODE_START_TIME],
            {
                RoborockDyadDataProtocol.SILENT_MODE_START_TIME: 85,
                RoborockDyadDataProtocol.POWER: 2,
                9999: -3,
            },
            {
                RoborockDyadDataProtocol.SILENT_MODE_START_TIME: datetime.time(1, 25),
            },
        ),
    ],
    ids=[
        "ignored-unknown-protocol",
        "invalid-value",
        "additional-returned-values",
    ],
)
async def test_dyad_invalid_response_value(
    query: list[RoborockDyadDataProtocol],
    response: dict[int, Any],
    expected_result: dict[RoborockDyadDataProtocol, Any],
    dyad_api: DyadApi,
    fake_channel: FakeChannel,
):
    """Test that DyadApi currently returns raw values without conversion."""
    fake_channel.response_queue.append(build_a01_message(response))

    result = await dyad_api.query_values(query)
    assert result == expected_result


async def test_dyad_values_track_pushes(dyad_api: DyadApi, fake_channel: FakeChannel):
    """Pushed values are merged into `values` in arrival order."""
    assert dyad_api.values == {}
    await dyad_api.start()

    fake_channel.notify_subscribers(build_a01_message({201: 6, 209: 80}))
    assert dyad_api.values == {
        RoborockDyadDataProtocol.STATUS: "self_clean_deep_cleaning",
        RoborockDyadDataProtocol.POWER: 80,
    }

    fake_channel.notify_subscribers(build_a01_message({209: 50, 999: 1}))
    assert dyad_api.values == {
        RoborockDyadDataProtocol.STATUS: "self_clean_deep_cleaning",
        RoborockDyadDataProtocol.POWER: 50,
    }


async def test_dyad_update_listener(dyad_api: DyadApi, fake_channel: FakeChannel):
    """Update listeners are notified when a value changes, not on identical pushes."""
    updates: list[dict[RoborockDyadDataProtocol, Any]] = []
    unsub = dyad_api.add_update_listener(lambda: updates.append(dyad_api.values))
    await dyad_api.start()

    fake_channel.notify_subscribers(build_a01_message({209: 80}))
    assert updates == [{RoborockDyadDataProtocol.POWER: 80}]

    fake_channel.notify_subscribers(build_a01_message({209: 80}))
    assert len(updates) == 1

    fake_channel.notify_subscribers(build_a01_message({209: 50}))
    assert len(updates) == 2
    assert updates[1] == {RoborockDyadDataProtocol.POWER: 50}

    unsub()
    fake_channel.notify_subscribers(build_a01_message({209: 20}))
    assert len(updates) == 2


async def test_dyad_query_values_updates_values(dyad_api: DyadApi, fake_channel: FakeChannel):
    """Query responses populate `values` even without an active subscription."""
    fake_channel.response_queue.append(build_a01_message({201: 6, 209: 80}))
    await dyad_api.query_values([RoborockDyadDataProtocol.STATUS, RoborockDyadDataProtocol.POWER])

    assert dyad_api.values == {
        RoborockDyadDataProtocol.STATUS: "self_clean_deep_cleaning",
        RoborockDyadDataProtocol.POWER: 80,
    }
    assert dyad_api.last_message_time is not None


async def test_dyad_query_response_does_not_overwrite_newer_push(dyad_api: DyadApi, fake_channel: FakeChannel):
    """A push arriving while the query is still in flight wins over the query response."""
    await dyad_api.start()
    fake_channel.response_queue.append(build_a01_message({209: 80}))

    # Deliver the push in the suspension window between the response arriving
    # and query_values() returning.
    async def push_before_query_returns() -> None:
        fake_channel.notify_subscribers(build_a01_message({209: 50}))

    fake_channel.health_manager.on_success = push_before_query_returns  # type: ignore[method-assign]

    result = await dyad_api.query_values([RoborockDyadDataProtocol.POWER])
    assert result == {RoborockDyadDataProtocol.POWER: 80}
    assert dyad_api.values == {RoborockDyadDataProtocol.POWER: 50}


async def test_dyad_last_message_time(dyad_api: DyadApi, fake_channel: FakeChannel):
    """Every decoded message updates last_message_time, even an identical heartbeat."""
    assert dyad_api.last_message_time is None
    await dyad_api.start()

    with freeze_time("2026-08-31 10:00:00") as frozen:
        fake_channel.notify_subscribers(build_a01_message({209: 80}))
        first = dyad_api.last_message_time
        assert first is not None

        frozen.tick(datetime.timedelta(seconds=30))
        fake_channel.notify_subscribers(build_a01_message({209: 80}))
        assert dyad_api.last_message_time == first + datetime.timedelta(seconds=30)


async def test_dyad_initial_status_seeds_values(fake_channel: FakeChannel):
    """The cloud status snapshot populates `values` without a device round trip."""
    api = DyadApi(fake_channel, initial_status={201: 6, 209: 80, 999: 1})  # type: ignore[arg-type]

    assert api.values == {
        RoborockDyadDataProtocol.STATUS: "self_clean_deep_cleaning",
        RoborockDyadDataProtocol.POWER: 80,
    }
    assert api.last_message_time is None


async def test_create_seeds_values_from_device_status(fake_channel: FakeChannel):
    """create() normalizes the string-keyed cloud snapshot before seeding."""
    api = create(DEFAULT_DYAD_PRODUCT, fake_channel, device_status={"201": 6, "209": 80})  # type: ignore[arg-type]

    assert isinstance(api, DyadApi)
    assert api.values == {
        RoborockDyadDataProtocol.STATUS: "self_clean_deep_cleaning",
        RoborockDyadDataProtocol.POWER: 80,
    }


async def test_dyad_close_stops_tracking(dyad_api: DyadApi, fake_channel: FakeChannel):
    """After close(), pushes no longer update `values`."""
    await dyad_api.start()
    fake_channel.notify_subscribers(build_a01_message({209: 80}))
    assert dyad_api.values == {RoborockDyadDataProtocol.POWER: 80}

    dyad_api.close()
    fake_channel.notify_subscribers(build_a01_message({209: 50}))
    assert dyad_api.values == {RoborockDyadDataProtocol.POWER: 80}


async def test_zeo_values_track_pushes(zeo_api: ZeoApi, fake_channel: FakeChannel):
    """Pushed values are merged into `values` after start()."""
    force_load_response = {int(dp): 0 for dp in build_force_load_dp_list(None)}
    fake_channel.response_queue.append(build_a01_message(force_load_response))
    await zeo_api.start()

    fake_channel.notify_subscribers(build_a01_message({203: 6, 218: 12}))
    assert zeo_api.values[RoborockZeoProtocol.STATE] == "spinning"
    assert zeo_api.values[RoborockZeoProtocol.WASHING_LEFT] == 12

    fake_channel.notify_subscribers(build_a01_message({203: 7}))
    assert zeo_api.values[RoborockZeoProtocol.STATE] == "drying"
    assert zeo_api.values[RoborockZeoProtocol.WASHING_LEFT] == 12


async def test_dyad_add_listener(dyad_api: DyadApi, fake_channel: FakeChannel):
    """add_listener delivers decoded values for pushed messages and skips unknown codes."""
    received: list[dict[RoborockDyadDataProtocol, Any]] = []
    unsub = await dyad_api.add_listener(received.append)

    fake_channel.notify_subscribers(build_a01_message({206: 3, 209: 80, 216: 0, 999: 1}))

    assert received == [
        {
            RoborockDyadDataProtocol.SUCTION: "l3",
            RoborockDyadDataProtocol.POWER: 80,
            RoborockDyadDataProtocol.ERROR: "none",
        }
    ]

    unsub()
    fake_channel.notify_subscribers(build_a01_message({206: 1}))
    assert len(received) == 1


async def test_zeo_api_query_values(zeo_api: ZeoApi, fake_channel: FakeChannel):
    """Test that ZeoApi currently returns raw values without conversion."""
    fake_channel.response_queue.append(
        build_a01_message(
            {
                203: 6,  # spinning
                207: 3,  # medium
                226: 1,
                227: 0,
                224: 1,  # Times after clean. Testing int value
                218: 0,  # Washing left. Testing zero int value
            }
        )
    )
    result = await zeo_api.query_values(
        [
            RoborockZeoProtocol.STATE,
            RoborockZeoProtocol.TEMP,
            RoborockZeoProtocol.DETERGENT_EMPTY,
            RoborockZeoProtocol.SOFTENER_EMPTY,
            RoborockZeoProtocol.TIMES_AFTER_CLEAN,
            RoborockZeoProtocol.WASHING_LEFT,
        ]
    )
    assert result == {
        # Note: Bug here, should return enum/bool values
        RoborockZeoProtocol.STATE: "spinning",
        RoborockZeoProtocol.TEMP: "medium",
        RoborockZeoProtocol.DETERGENT_EMPTY: True,
        RoborockZeoProtocol.SOFTENER_EMPTY: False,
        RoborockZeoProtocol.TIMES_AFTER_CLEAN: 1,
        RoborockZeoProtocol.WASHING_LEFT: 0,
    }

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == b"A01"
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    assert payload_data["dps"] == {"10000": "[203, 207, 226, 227, 224, 218]"}
    assert "t" in payload_data


@pytest.mark.parametrize(
    ("query", "response", "expected_result"),
    [
        (
            [RoborockZeoProtocol.STATE],
            {
                7: 1,
                RoborockZeoProtocol.STATE: 1,
                9999: -3,
            },
            {
                RoborockZeoProtocol.STATE: "standby",
            },
        ),
        (
            [RoborockZeoProtocol.WASHING_LEFT],
            {
                RoborockZeoProtocol.WASHING_LEFT: "invalid",
            },
            {
                RoborockZeoProtocol.WASHING_LEFT: None,
            },
        ),
        (
            [RoborockZeoProtocol.STATE],
            {
                RoborockZeoProtocol.STATE: 1,
                RoborockZeoProtocol.WASHING_LEFT: 2,
                9999: -3,
            },
            {
                RoborockZeoProtocol.STATE: "standby",
            },
        ),
    ],
    ids=[
        "ignored-unknown-protocol",
        "invalid-value",
        "additional-returned-values",
    ],
)
async def test_zeo_invalid_response_value(
    query: list[RoborockZeoProtocol],
    response: dict[int, Any],
    expected_result: dict[RoborockZeoProtocol, Any],
    zeo_api: ZeoApi,
    fake_channel: FakeChannel,
):
    """Test that ZeoApi currently returns raw values without conversion."""
    fake_channel.response_queue.append(build_a01_message(response))

    result = await zeo_api.query_values(query)
    assert result == expected_result


async def test_dyad_api_set_value(dyad_api: DyadApi, fake_channel: FakeChannel):
    """Test DyadApi set_value sends correct command."""
    await dyad_api.set_value(RoborockDyadDataProtocol.POWER, 1)

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]

    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == b"A01"

    # decode the payload to verify contents
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    # A01 protocol expects values to be strings in the dps dict
    assert payload_data["dps"] == {"209": 1}
    assert "t" in payload_data


async def test_zeo_api_set_value(zeo_api: ZeoApi, fake_channel: FakeChannel):
    """Test ZeoApi set_value sends correct command."""
    await zeo_api.set_value(RoborockZeoProtocol.MODE, "standard")

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]

    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == b"A01"

    # decode the payload to verify contents
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    # A01 protocol expects values to be strings in the dps dict
    assert payload_data["dps"] == {"204": "standard"}
    assert "t" in payload_data
