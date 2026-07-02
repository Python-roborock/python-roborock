from roborock.data.b01_q7.b01_q7_containers import Q7MapListEntry
from roborock.devices.traits.b01.q7 import Q7PropertiesApi
from roborock.roborock_typing import RoborockB01Q7Methods

from .conftest import FakeQ7Channel


async def test_q7_map_refresh(q7_api: Q7PropertiesApi, fake_channel: FakeQ7Channel):
    """Test retrieving lists of saved maps."""
    fake_channel.response_queue.append({"map_list": [{"id": 111, "name": "Map 1"}]})
    await q7_api.map.refresh()

    assert len(fake_channel.published_commands) == 1
    command, params = fake_channel.published_commands[0]
    assert command == RoborockB01Q7Methods.GET_MAP_LIST
    assert params == {}
    assert q7_api.map.map_list == [Q7MapListEntry(id=111)]
