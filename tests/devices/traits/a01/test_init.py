import datetime
import json
from dataclasses import replace
from typing import Any

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from freezegun import freeze_time

from roborock.data import DyadScheduleTask
from roborock.data.dyad.dyad_code_mappings import (
    DyadCleanMode,
    DyadDryingMode,
    DyadFeatureBits,
    DyadSelfCleanIntensity,
    DyadSuction,
    DyadWaterLevel,
)
from roborock.devices.traits.a01 import DyadApi, ZeoApi, create
from roborock.devices.traits.a01.device_feature import build_force_load_dp_list
from roborock.exceptions import RoborockUnsupportedFeature
from roborock.roborock_message import RoborockDyadDataProtocol, RoborockMessageProtocol, RoborockZeoProtocol
from roborock.testing.a01_simulator import DEFAULT_DYAD_PRODUCT
from tests.fixtures.channel_fixtures import FakeChannel
from tests.protocols.common import build_a01_message


@pytest.fixture(name="fake_channel")
def fake_channel_fixture() -> FakeChannel:
    return FakeChannel()


@pytest.fixture(name="dyad_api")
def dyad_api_fixture(fake_channel: FakeChannel) -> DyadApi:
    return DyadApi(fake_channel, model="roborock.wdv.a194")  # type: ignore[arg-type]


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


async def test_dyad_f25_ultra_status_snapshot(dyad_api: DyadApi, fake_channel: FakeChannel):
    """Data points pushed by an F25 Ultra (roborock.wdv.a194) are decoded."""
    await dyad_api.start()

    fake_channel.notify_subscribers(
        build_a01_message({238: 0, 239: 1, 240: 1, 241: 2, 242: 3, 243: 2, 244: 3, 245: 2, 246: 0, 247: 100, 248: 0})
    )
    fake_channel.notify_subscribers(build_a01_message({270: 0, 271: 3, 272: 5}))

    assert dyad_api.values == {
        RoborockDyadDataProtocol.SET_CLEANSER_AMOUNT: "off",
        RoborockDyadDataProtocol.AUTO_SMART_SELF_CLEAN_SET: True,
        RoborockDyadDataProtocol.LIGHT_SET: True,
        RoborockDyadDataProtocol.CLEAN_ASSIST_POWER_SET: "moderate",
        RoborockDyadDataProtocol.SELF_CLEAN_WATER_TEMP_LEVEL_SET: "high",
        RoborockDyadDataProtocol.DOCK_TYPE: 2,
        RoborockDyadDataProtocol.WATER_MODE_SUCTION: "l3",
        RoborockDyadDataProtocol.WATER_MODE_BRUSH_SPEED: "l2",
        RoborockDyadDataProtocol.CHARGE_ERROR_STATUS: False,
        RoborockDyadDataProtocol.DRYING_RATE: 100,
        RoborockDyadDataProtocol.FLAT_STATUS: "standing",
        RoborockDyadDataProtocol.SELF_CLEAN_CUR_MODE: "smart",
        RoborockDyadDataProtocol.SELF_CLEAN_CUR_TEMP: "high",
        RoborockDyadDataProtocol.DRY_CUR_MODE: "fast",
    }


@pytest.mark.parametrize(
    ("protocol", "raw", "expected"),
    [
        (RoborockDyadDataProtocol.SET_CLEANSER_AMOUNT, 0, "off"),
        (RoborockDyadDataProtocol.SET_CLEANSER_AMOUNT, 1, "low"),
        (RoborockDyadDataProtocol.SET_CLEANSER_AMOUNT, 2, "standard"),
        (RoborockDyadDataProtocol.SET_CLEANSER_AMOUNT, 3, "high"),
        (RoborockDyadDataProtocol.SET_CLEANSER_AMOUNT, 42, "unknown"),
        (RoborockDyadDataProtocol.CLEAN_ASSIST_POWER_SET, 1, "gentle"),
        (RoborockDyadDataProtocol.CLEAN_ASSIST_POWER_SET, 2, "moderate"),
        (RoborockDyadDataProtocol.CLEAN_ASSIST_POWER_SET, 3, "strong"),
        (RoborockDyadDataProtocol.SELF_CLEAN_WATER_TEMP_LEVEL_SET, 3, "high"),
        (RoborockDyadDataProtocol.SELF_CLEAN_WATER_TEMP_LEVEL_SET, 4, "steam"),
        (RoborockDyadDataProtocol.SELF_CLEAN_WATER_TEMP_LEVEL_SET, 1, "low"),
        (RoborockDyadDataProtocol.SELF_CLEAN_WATER_TEMP_LEVEL_SET, 2, "mid"),
        (RoborockDyadDataProtocol.SELF_CLEAN_WATER_TEMP_LEVEL_SET, 9, "unknown"),
        (RoborockDyadDataProtocol.SELF_CLEAN_CUR_TEMP, 4, "steam"),
        (RoborockDyadDataProtocol.SELF_CLEAN_CUR_MODE, 0, "smart"),
        (RoborockDyadDataProtocol.SELF_CLEAN_CUR_MODE, 1, "standard"),
        (RoborockDyadDataProtocol.SELF_CLEAN_CUR_MODE, 2, "deep"),
        (RoborockDyadDataProtocol.WATER_MODE_SUCTION, 4, "l4"),
        (RoborockDyadDataProtocol.LIGHT_SET, 0, False),
        (RoborockDyadDataProtocol.AUTO_SMART_SELF_CLEAN_SET, 0, False),
        (RoborockDyadDataProtocol.CHARGE_ERROR_STATUS, 1, True),
        (RoborockDyadDataProtocol.AUTO_SELF_CLEAN_SET, 1, True),
        (RoborockDyadDataProtocol.AUTO_SELF_CLEAN_SET, 0, False),
        (RoborockDyadDataProtocol.AUTO_SELF_CLEAN_SET_MODE, 2, "deep"),
        (RoborockDyadDataProtocol.POWERWHEEL_DIRECTION, 0, "stop"),
        (RoborockDyadDataProtocol.POWERWHEEL_DIRECTION, 1, "forward"),
        (RoborockDyadDataProtocol.POWERWHEEL_DIRECTION, 2, "backward"),
        (RoborockDyadDataProtocol.POWERWHEEL_DIRECTION, 3, "left"),
        (RoborockDyadDataProtocol.POWERWHEEL_DIRECTION, 4, "right"),
        (RoborockDyadDataProtocol.POWERWHEEL_DIRECTION, 5, "forward_left"),
        (RoborockDyadDataProtocol.POWERWHEEL_DIRECTION, 6, "forward_right"),
        (RoborockDyadDataProtocol.POWERWHEEL_DIRECTION, 7, "backward_left"),
        (RoborockDyadDataProtocol.POWERWHEEL_DIRECTION, 8, "backward_right"),
        (RoborockDyadDataProtocol.POWERWHEEL_DIRECTION, 9, "exit"),
        (RoborockDyadDataProtocol.POWERWHEEL_DIRECTION, 10, "unknown"),
        (RoborockDyadDataProtocol.FLAT_STATUS, 1, "flat"),
        (RoborockDyadDataProtocol.FLAT_STATUS, 2, "error"),
        (RoborockDyadDataProtocol.FLAT_STATUS, 3, "unknown"),
        (RoborockDyadDataProtocol.STATUS, 15, "combination"),
        (RoborockDyadDataProtocol.ERROR, 20010, "error_20010"),
        (RoborockDyadDataProtocol.ERROR, 12345, "unknown"),
        (RoborockDyadDataProtocol.FEATURE_INFO, 102, 102),
        (RoborockDyadDataProtocol.SELF_CLEAN_PROGRESS, 50, 50),
        (RoborockDyadDataProtocol.MECHANICAL_ARM, 1, True),
        (RoborockDyadDataProtocol.POWERWHEEL_SPEED, 15, 15),
        (RoborockDyadDataProtocol.DRY_CUR_MODE, 5, "fast"),
        (RoborockDyadDataProtocol.DRY_CUR_MODE, 22, "silent"),
        (RoborockDyadDataProtocol.DRY_CUR_MODE, 7, "unknown"),
        (RoborockDyadDataProtocol.SILENT_DRY_DURATION, 22, 22),
    ],
)
async def test_dyad_f25_ultra_value_conversion(
    protocol: RoborockDyadDataProtocol,
    raw: int,
    expected: Any,
    dyad_api: DyadApi,
    fake_channel: FakeChannel,
):
    """Values observed on an F25 Ultra while changing settings in the app."""
    await dyad_api.start()
    fake_channel.notify_subscribers(build_a01_message({int(protocol): raw}))
    assert dyad_api.values == {protocol: expected}


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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", []),
        (
            '[{"id":1794139256726,"on":true,"cron":"0 15 * * 1,2,3,4,5","dpAction":{"200":1,"204":1}}]',
            [DyadScheduleTask(id=1794139256726, on=True, cron="0 15 * * 1,2,3,4,5", dp_action={200: 1, 204: 1})],
        ),
    ],
    ids=["empty", "weekdays"],
)
async def test_dyad_schedule_task(
    raw: str,
    expected: list[DyadScheduleTask],
    dyad_api: DyadApi,
    fake_channel: FakeChannel,
):
    """The schedule payload seen on an F25 Ultra is decoded into typed tasks."""
    await dyad_api.start()
    fake_channel.notify_subscribers(build_a01_message({10002: raw}))
    assert dyad_api.values == {RoborockDyadDataProtocol.SCHEDULE_TASK: expected}


async def test_dyad_schedule_task_invalid(dyad_api: DyadApi, fake_channel: FakeChannel):
    """A malformed schedule payload does not produce a value."""
    await dyad_api.start()
    fake_channel.notify_subscribers(build_a01_message({10002: "not json"}))
    assert dyad_api.values == {}


@pytest.mark.parametrize(
    ("method", "expected_dps"),
    [
        ("start_drying", {"200": 1, "204": 1}),
        ("stop", {"200": 0}),
        ("pause_self_clean", {"200": 2}),
        ("resume_self_clean", {"200": 1}),
        ("reset_filter", {"218": 1}),
        ("reset_brush", {"219": 1}),
    ],
)
async def test_dyad_action_commands(
    method: str,
    expected_dps: dict[str, int],
    dyad_api: DyadApi,
    fake_channel: FakeChannel,
):
    """Action commands send the data points used by the app."""
    await getattr(dyad_api, method)()

    assert len(fake_channel.published_messages) == 1
    payload_data = json.loads(unpad(fake_channel.published_messages[0].payload, AES.block_size))
    assert payload_data["dps"] == expected_dps


@pytest.mark.parametrize(
    ("mode", "expected_dps"),
    [
        (DyadDryingMode.fast, {"225": 5}),
        (DyadDryingMode.silent, {"225": 22}),
    ],
)
async def test_dyad_set_drying_mode(
    mode: DyadDryingMode,
    expected_dps: dict[str, int],
    dyad_api: DyadApi,
    fake_channel: FakeChannel,
):
    """The drying mode is written to the data point used by the app."""
    await dyad_api.set_drying_mode(mode)

    assert len(fake_channel.published_messages) == 1
    payload_data = json.loads(unpad(fake_channel.published_messages[0].payload, AES.block_size))
    assert payload_data["dps"] == expected_dps


async def test_dyad_set_drying_mode_unknown(dyad_api: DyadApi, fake_channel: FakeChannel):
    """The unknown placeholder is rejected and nothing is sent to the device."""
    with pytest.raises(ValueError):
        await dyad_api.set_drying_mode(DyadDryingMode.unknown)

    assert fake_channel.published_messages == []


@pytest.mark.parametrize(
    ("intensity", "expected_dps"),
    [
        (DyadSelfCleanIntensity.smart, {"203": 1, "223": 1, "239": 1}),
        (DyadSelfCleanIntensity.standard, {"203": 1, "223": 1, "239": 0}),
        (DyadSelfCleanIntensity.deep, {"203": 2, "223": 2, "239": 0}),
    ],
)
async def test_dyad_set_self_clean_intensity(
    intensity: DyadSelfCleanIntensity,
    expected_dps: dict[str, int],
    dyad_api: DyadApi,
    fake_channel: FakeChannel,
):
    """The intensity is written to all the data points the device reports it on."""
    await dyad_api.set_self_clean_intensity(intensity)

    assert len(fake_channel.published_messages) == 1
    payload_data = json.loads(unpad(fake_channel.published_messages[0].payload, AES.block_size))
    assert payload_data["dps"] == expected_dps


async def test_dyad_set_self_clean_intensity_unknown(dyad_api: DyadApi, fake_channel: FakeChannel):
    """The unknown placeholder is rejected and nothing is sent to the device."""
    with pytest.raises(ValueError):
        await dyad_api.set_self_clean_intensity(DyadSelfCleanIntensity.unknown)

    assert fake_channel.published_messages == []


@pytest.mark.parametrize(
    ("method", "suction", "expected_dps"),
    [
        ("set_suction", DyadSuction.l2, {"206": 2, "208": 1}),
        ("set_suction", DyadSuction.l3, {"206": 3, "208": 2}),
        ("set_suction", DyadSuction.l4, {"206": 4, "208": 2}),
        ("set_sponge_suction", DyadSuction.l2, {"244": 2, "245": 1}),
        ("set_sponge_suction", DyadSuction.l3, {"244": 3, "245": 2}),
        ("set_sponge_suction", DyadSuction.l4, {"244": 4, "245": 2}),
    ],
)
async def test_dyad_set_suction(
    method: str,
    suction: DyadSuction,
    expected_dps: dict[str, int],
    dyad_api: DyadApi,
    fake_channel: FakeChannel,
):
    """Suction is sent together with the brush speed the app pairs with it."""
    await getattr(dyad_api, method)(suction)

    assert len(fake_channel.published_messages) == 1
    payload_data = json.loads(unpad(fake_channel.published_messages[0].payload, AES.block_size))
    assert payload_data["dps"] == expected_dps


@pytest.mark.parametrize("method", ["set_suction", "set_sponge_suction"])
@pytest.mark.parametrize("suction", [DyadSuction.l1, DyadSuction.l5, DyadSuction.l6])
async def test_dyad_set_suction_unsupported(
    method: str,
    suction: DyadSuction,
    dyad_api: DyadApi,
    fake_channel: FakeChannel,
):
    """Levels not seen on the F25 Ultra are rejected and nothing is sent."""
    with pytest.raises(ValueError):
        await getattr(dyad_api, method)(suction)

    assert fake_channel.published_messages == []


@pytest.mark.parametrize("level", [1, 2])
async def test_dyad_start_self_clean(level: int, dyad_api: DyadApi, fake_channel: FakeChannel):
    """Self-clean starts with the level currently set on the device."""
    fake_channel.response_queue.append(build_a01_message({203: level}))

    await dyad_api.start_self_clean()

    assert len(fake_channel.published_messages) == 2
    payload_data = json.loads(unpad(fake_channel.published_messages[1].payload, AES.block_size))
    assert payload_data["dps"] == {"200": 1, "203": level}


async def test_dyad_start_self_clean_on_any_model(fake_channel: FakeChannel):
    """The app starts self-clean the same way on every model."""
    api = create(DEFAULT_DYAD_PRODUCT, fake_channel)  # type: ignore[arg-type]
    assert isinstance(api, DyadApi)
    fake_channel.response_queue.append(build_a01_message({203: 1}))

    await api.start_self_clean()

    assert len(fake_channel.published_messages) == 2


@pytest.mark.parametrize(
    ("method", "args", "model"),
    [
        ("set_drying_mode", (DyadDryingMode.fast,), "roborock.wetdryvac.a151"),
        ("set_drying_mode", (DyadDryingMode.silent,), "roborock.wdv.a300"),
        ("set_drying_mode", (DyadDryingMode.fast,), "roborock.wetdryvac.a238"),
        ("set_self_clean_intensity", (DyadSelfCleanIntensity.smart,), "roborock.wetdryvac.a132"),
        ("set_suction", (DyadSuction.l3,), "roborock.wetdryvac.a174"),
        ("set_sponge_suction", (DyadSuction.l3,), "roborock.wdv.a260"),
        ("pause_self_clean", (), "roborock.wetdryvac.a56"),
    ],
)
async def test_dyad_commands_accepted_by_model(
    method: str,
    args: tuple[Any, ...],
    model: str,
    fake_channel: FakeChannel,
):
    """Commands are sent to the models the app enables them for."""
    api = DyadApi(fake_channel, model=model)  # type: ignore[arg-type]

    await getattr(api, method)(*args)

    assert len(fake_channel.published_messages) == 1


@pytest.mark.parametrize(
    ("method", "args", "model"),
    [
        ("set_drying_mode", (DyadDryingMode.fast,), "roborock.wetdryvac.a56"),
        ("set_drying_mode", (DyadDryingMode.fast,), "roborock.wetdryvac.a132"),
        ("set_drying_mode", (DyadDryingMode.fast,), "roborock.wetdryvac.a01"),
        ("set_drying_mode", (DyadDryingMode.fast,), None),
        ("set_self_clean_intensity", (DyadSelfCleanIntensity.smart,), "roborock.wetdryvac.a56"),
        ("set_self_clean_intensity", (DyadSelfCleanIntensity.deep,), "roborock.wetdryvac.a01"),
        ("set_suction", (DyadSuction.l3,), "roborock.wetdryvac.a238"),
        ("set_suction", (DyadSuction.l3,), "roborock.wetdryvac.a56"),
        ("set_sponge_suction", (DyadSuction.l3,), "roborock.wetdryvac.a238"),
        ("pause_self_clean", (), "roborock.wetdryvac.a132"),
        ("pause_self_clean", (), "roborock.wetdryvac.a138"),
        ("resume_self_clean", (), "roborock.wetdryvac.a132"),
        ("pause_self_clean", (), None),
    ],
)
async def test_dyad_commands_rejected_by_model(
    method: str,
    args: tuple[Any, ...],
    model: str | None,
    fake_channel: FakeChannel,
):
    """Commands fail on models the app does not enable them for, and nothing is sent."""
    api = DyadApi(fake_channel, model=model)  # type: ignore[arg-type]

    with pytest.raises(RoborockUnsupportedFeature):
        await getattr(api, method)(*args)

    assert fake_channel.published_messages == []


@pytest.mark.parametrize(
    ("method", "value"),
    [
        ("set_drying_mode", 7),
        ("set_drying_mode", "fast"),
        ("set_drying_mode", None),
        ("set_self_clean_intensity", 7),
        ("set_self_clean_intensity", "deep"),
        ("set_suction", 9),
        ("set_sponge_suction", 9),
        ("set_water_level", DyadWaterLevel.l1),
        ("set_water_level", 9),
    ],
)
async def test_dyad_invalid_values_rejected(method: str, value: Any, dyad_api: DyadApi, fake_channel: FakeChannel):
    """Values the app does not offer are rejected and nothing is sent."""
    with pytest.raises(ValueError):
        await getattr(dyad_api, method)(value)

    assert fake_channel.published_messages == []


@pytest.mark.parametrize(
    ("model", "mode"),
    [
        ("roborock.wdv.a194", DyadCleanMode.auto),
        ("roborock.wdv.a194", DyadCleanMode.steam),
        ("roborock.wdv.a194", DyadCleanMode.hot_water),
        ("roborock.wdv.a194", DyadCleanMode.dehydration),
        ("roborock.wetdryvac.a151", DyadCleanMode.max),
        ("roborock.wetdryvac.a151", DyadCleanMode.power_saving),
        ("roborock.wetdryvac.a151", DyadCleanMode.dehydration),
        ("roborock.wetdryvac.a132", DyadCleanMode.power_saving),
        ("roborock.wetdryvac.a56", DyadCleanMode.dehydration),
    ],
)
async def test_dyad_set_clean_mode(model: str, mode: DyadCleanMode, fake_channel: FakeChannel):
    """Clean modes the app offers for the model are written to the clean mode data point."""
    api = DyadApi(fake_channel, model=model)  # type: ignore[arg-type]

    await api.set_clean_mode(mode)

    payload_data = json.loads(unpad(fake_channel.published_messages[0].payload, AES.block_size))
    assert payload_data["dps"] == {"205": int(mode)}


@pytest.mark.parametrize(
    ("model", "mode"),
    [
        ("roborock.wdv.a194", DyadCleanMode.max),
        ("roborock.wdv.a194", DyadCleanMode.power_saving),
        ("roborock.wdv.a194", DyadCleanMode.unknown),
        ("roborock.wdv.a194", 9),
        ("roborock.wetdryvac.a151", DyadCleanMode.steam),
        ("roborock.wetdryvac.a132", DyadCleanMode.dehydration),
        ("roborock.wetdryvac.a01", DyadCleanMode.auto),
        (None, DyadCleanMode.auto),
    ],
)
async def test_dyad_set_clean_mode_rejected(model: str | None, mode: Any, fake_channel: FakeChannel):
    """Clean modes the app does not offer for the model are rejected."""
    api = DyadApi(fake_channel, model=model)  # type: ignore[arg-type]

    with pytest.raises(RoborockUnsupportedFeature):
        await api.set_clean_mode(mode)

    assert fake_channel.published_messages == []


@pytest.mark.parametrize("level", [DyadWaterLevel.l2, DyadWaterLevel.l3, DyadWaterLevel.l4])
async def test_dyad_set_water_level(level: DyadWaterLevel, dyad_api: DyadApi, fake_channel: FakeChannel):
    """Water levels offered by the app are written to the water level data point."""
    await dyad_api.set_water_level(level)

    payload_data = json.loads(unpad(fake_channel.published_messages[0].payload, AES.block_size))
    assert payload_data["dps"] == {"207": int(level)}


async def test_dyad_set_water_level_rejected_by_model(fake_channel: FakeChannel):
    """Models without the app's water levels are rejected."""
    api = DyadApi(fake_channel, model="roborock.wetdryvac.a238")  # type: ignore[arg-type]

    with pytest.raises(RoborockUnsupportedFeature):
        await api.set_water_level(DyadWaterLevel.l3)

    assert fake_channel.published_messages == []


async def test_dyad_set_self_clean_intensity_without_smart(fake_channel: FakeChannel):
    """Models without smart self-clean do not get the smart data point."""
    api = DyadApi(fake_channel, model="roborock.wetdryvac.a56")  # type: ignore[arg-type]

    await api.set_self_clean_intensity(DyadSelfCleanIntensity.deep)

    payload_data = json.loads(unpad(fake_channel.published_messages[0].payload, AES.block_size))
    assert payload_data["dps"] == {"203": 2, "223": 2}


async def test_dyad_supports_feature_bits(dyad_api: DyadApi, fake_channel: FakeChannel):
    """Feature bits are read from the reported FEATURE_INFO value."""
    assert not dyad_api.supports(DyadFeatureBits.show_current_mode)

    await dyad_api.start()
    fake_channel.notify_subscribers(build_a01_message({235: 102}))

    assert dyad_api.supports(DyadFeatureBits.percentage_dry_timer)
    assert dyad_api.supports(DyadFeatureBits.remote_control)
    assert dyad_api.supports(DyadFeatureBits.show_self_clean_progress)
    assert dyad_api.supports(DyadFeatureBits.show_current_mode)
    assert not dyad_api.supports(DyadFeatureBits.three_plus_ten_dry_plan)
    assert not dyad_api.supports(DyadFeatureBits.unknown)


async def test_create_passes_dyad_model(fake_channel: FakeChannel):
    """The product model from home data enables model specific commands."""
    product = replace(DEFAULT_DYAD_PRODUCT, model="roborock.wdv.a194")
    api = create(product, fake_channel)  # type: ignore[arg-type]
    assert isinstance(api, DyadApi)

    await api.set_drying_mode(DyadDryingMode.fast)

    assert len(fake_channel.published_messages) == 1


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
