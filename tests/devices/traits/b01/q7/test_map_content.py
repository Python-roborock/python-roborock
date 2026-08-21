from unittest.mock import patch

import pytest
from vacuum_map_parser_base.map_data import MapData

from roborock.devices.traits.b01.q7 import Q7PropertiesApi
from roborock.exceptions import RoborockException
from roborock.map.b01_map_parser import ParsedMapData
from roborock.map.proto.b01_scmap_pb2 import RobotMap  # type: ignore[attr-defined]
from roborock.roborock_typing import RoborockB01Q7Methods

from .conftest import FakeQ7Channel


def scmap_frame(map_type: int = 0) -> bytes:
    """Serialize a minimal SCMap frame of the given map type."""
    return RobotMap(mapType=map_type).SerializeToString()


async def test_q7_map_content_refresh_populates_cached_values(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeQ7Channel,
):
    fake_channel.response_queue.extend(
        [
            {"map_list": [{"id": 1772093512, "cur": True}]},
            b"inflated-payload",
        ]
    )

    # Ensure we have map metadata first
    await q7_api.map.refresh()

    dummy_map_data = MapData()
    parsed_map_data = ParsedMapData(
        image_content=b"pngbytes",
        map_data=dummy_map_data,
    )
    with patch(
        "roborock.devices.traits.b01.q7.map_content.B01MapParser.parse",
        return_value=parsed_map_data,
    ) as parse:
        await q7_api.map_content.refresh()

    assert q7_api.map_content.image_content == b"pngbytes"
    assert q7_api.map_content.map_data is dummy_map_data
    assert q7_api.map_content.raw_api_response == b"inflated-payload"

    parse.assert_called_once_with(b"inflated-payload")

    assert len(fake_channel.published_commands) == 2
    cmd, params = fake_channel.published_commands[0]
    assert cmd == RoborockB01Q7Methods.GET_MAP_LIST

    map_cmd, map_params = fake_channel.published_commands[1]
    assert map_cmd == RoborockB01Q7Methods.UPLOAD_BY_MAPID
    assert map_params == {"map_id": 1772093512}


async def test_q7_map_content_refresh_falls_back_to_first_map(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeQ7Channel,
):
    """If no current map marker exists, first map in list is used."""
    fake_channel.response_queue.extend(
        [
            {"map_list": [{"id": 111}, {"id": 222, "cur": False}]},
            b"inflated-payload",
        ]
    )

    # Load current map
    await q7_api.map.refresh()

    dummy_map_data = MapData()
    with patch(
        "roborock.devices.traits.b01.q7.map_content.B01MapParser.parse",
        return_value=type("X", (), {"image_content": b"pngbytes", "map_data": dummy_map_data})(),
    ):
        await q7_api.map_content.refresh()

    assert len(fake_channel.published_commands) == 2
    map_cmd, map_params = fake_channel.published_commands[1]
    assert map_params == {"map_id": 111}


async def test_q7_map_content_refresh_errors_without_map_list(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeQ7Channel,
):
    """Refresh should fail clearly when map list is unusable."""
    fake_channel.response_queue.extend([{"map_list": []}])

    with pytest.raises(RoborockException, match="Unable to determine current map ID"):
        await q7_api.map_content.refresh()


async def test_q7_map_content_updates_from_push(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeQ7Channel,
):
    """Unsolicited map pushes update the cached map and notify listeners."""
    await q7_api.start()
    assert fake_channel.map_push_callback is not None

    updates: list[bool] = []
    q7_api.map_content.add_update_listener(lambda: updates.append(True))

    dummy_map_data = MapData()
    parsed_map_data = ParsedMapData(
        image_content=b"pngbytes",
        map_data=dummy_map_data,
    )
    pushed_payload = scmap_frame()
    with patch(
        "roborock.devices.traits.b01.q7.map_content.B01MapParser.parse",
        return_value=parsed_map_data,
    ):
        fake_channel.map_push_callback(pushed_payload)

    assert q7_api.map_content.image_content == b"pngbytes"
    assert q7_api.map_content.raw_api_response == pushed_payload
    assert updates == [True]

    await q7_api.close()
    assert fake_channel.map_push_callback is None


async def test_q7_map_content_push_parse_failure_keeps_previous_map(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeQ7Channel,
):
    """A malformed pushed frame is dropped without clearing cached content."""
    await q7_api.start()
    assert fake_channel.map_push_callback is not None

    dummy_map_data = MapData()
    parsed_map_data = ParsedMapData(
        image_content=b"pngbytes",
        map_data=dummy_map_data,
    )
    good_payload = scmap_frame()
    with patch(
        "roborock.devices.traits.b01.q7.map_content.B01MapParser.parse",
        return_value=parsed_map_data,
    ):
        fake_channel.map_push_callback(good_payload)

    updates: list[bool] = []
    q7_api.map_content.add_update_listener(lambda: updates.append(True))

    fake_channel.map_push_callback(b"not a map")

    assert q7_api.map_content.image_content == b"pngbytes"
    assert q7_api.map_content.raw_api_response == good_payload
    assert updates == []
    await q7_api.close()


async def test_q7_map_content_push_ignores_non_live_map(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeQ7Channel,
):
    """Only frames of the live map may update the cached map."""
    await q7_api.start()
    assert fake_channel.map_push_callback is not None

    dummy_map_data = MapData()
    parsed_map_data = ParsedMapData(
        image_content=b"pngbytes",
        map_data=dummy_map_data,
    )
    good_payload = scmap_frame()
    with patch(
        "roborock.devices.traits.b01.q7.map_content.B01MapParser.parse",
        return_value=parsed_map_data,
    ):
        fake_channel.map_push_callback(good_payload)

    updates: list[bool] = []
    q7_api.map_content.add_update_listener(lambda: updates.append(True))

    with patch(
        "roborock.devices.traits.b01.q7.map_content.B01MapParser.parse",
        return_value=ParsedMapData(image_content=b"othermap", map_data=MapData()),
    ) as parse:
        fake_channel.map_push_callback(scmap_frame(map_type=1))

    parse.assert_not_called()
    assert q7_api.map_content.image_content == b"pngbytes"
    assert q7_api.map_content.raw_api_response == good_payload
    assert updates == []
    await q7_api.close()


async def test_q7_start_is_idempotent(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeQ7Channel,
):
    """Repeated start() calls must not leak additional subscriptions."""
    await q7_api.start()
    await q7_api.start()

    assert fake_channel.map_push_subscribe_count == 1
    await q7_api.close()
    assert fake_channel.map_push_callback is None
