import json

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from roborock.data import Q7MapList, Q7MapListEntry
from roborock.devices.traits.b01.q7 import Q7PropertiesApi
from roborock.exceptions import RoborockException
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.fixtures.channel_fixtures import FakeChannel

from . import B01MessageBuilder


async def test_q7_api_get_current_map_payload(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
):
    """Fetch current map by map-list lookup, then upload_by_mapid."""
    fake_channel.response_queue.append(message_builder.build({"map_list": [{"id": 1772093512, "cur": True}]}))
    fake_channel.response_queue.append(
        RoborockMessage(
            protocol=RoborockMessageProtocol.MAP_RESPONSE,
            payload=b"raw-map-payload",
            version=b"B01",
            seq=message_builder.seq + 1,
        )
    )

    raw_payload = await q7_api.map.get_current_map_payload()
    assert raw_payload == b"raw-map-payload"

    assert len(fake_channel.published_messages) == 2

    first = fake_channel.published_messages[0]
    first_payload = json.loads(unpad(first.payload, AES.block_size))
    assert first_payload["dps"]["10000"]["method"] == "service.get_map_list"
    assert first_payload["dps"]["10000"]["params"] == {}

    second = fake_channel.published_messages[1]
    second_payload = json.loads(unpad(second.payload, AES.block_size))
    assert second_payload["dps"]["10000"]["method"] == "service.upload_by_mapid"
    assert second_payload["dps"]["10000"]["params"] == {"map_id": 1772093512}


async def test_q7_api_map_trait_refresh_populates_cached_values(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
):
    """Map trait follows refresh + cached-value access pattern."""
    fake_channel.response_queue.append(message_builder.build({"map_list": [{"id": 101, "cur": True}]}))

    assert q7_api.map.map_list == []
    assert q7_api.map.current_map_id is None

    await q7_api.map.refresh()

    assert len(fake_channel.published_messages) == 1
    assert q7_api.map.map_list[0].id == 101
    assert q7_api.map.map_list[0].cur is True
    assert q7_api.map.current_map_id == 101


async def test_q7_api_get_current_map_payload_falls_back_to_first_map(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
):
    """If no current map marker exists, first map in list is used."""
    fake_channel.response_queue.append(message_builder.build({"map_list": [{"id": 111}, {"id": 222, "cur": False}]}))
    fake_channel.response_queue.append(
        RoborockMessage(
            protocol=RoborockMessageProtocol.MAP_RESPONSE,
            payload=b"raw-map-payload",
            version=b"B01",
            seq=message_builder.seq + 1,
        )
    )

    await q7_api.map.get_current_map_payload()

    second = fake_channel.published_messages[1]
    second_payload = json.loads(unpad(second.payload, AES.block_size))
    assert second_payload["dps"]["10000"]["params"] == {"map_id": 111}


async def test_q7_api_get_current_map_payload_errors_without_map_list(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
):
    """Current-map payload fetch should fail clearly when map list is unusable."""
    fake_channel.response_queue.append(message_builder.build({"map_list": []}))

    with pytest.raises(RoborockException, match="Unable to determine map_id"):
        await q7_api.map.get_current_map_payload()


def test_q7_map_list_current_map_id_prefers_marked_current():
    """Current-map resolution prefers the entry marked current."""
    map_list = Q7MapList(
        map_list=[
            Q7MapListEntry(id=111, cur=False),
            Q7MapListEntry(id=222, cur=True),
        ]
    )

    assert map_list.current_map_id == 222
