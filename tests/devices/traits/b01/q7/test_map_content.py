from typing import cast
from unittest.mock import patch

import pytest
from vacuum_map_parser_base.map_data import MapData

from roborock.devices.traits.b01.q7 import Q7PropertiesApi
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.exceptions import RoborockException
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.fixtures.channel_fixtures import FakeChannel

from . import B01MessageBuilder


async def test_q7_map_content_refresh_populates_cached_values(
    q7_api: Q7PropertiesApi,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
):
    fake_channel.response_queue.append(message_builder.build({"map_list": [{"id": 1772093512, "cur": True}]}))
    fake_channel.response_queue.append(
        RoborockMessage(
            protocol=RoborockMessageProtocol.MAP_RESPONSE,
            payload=b"raw-map-payload",
            version=b"B01",
            seq=message_builder.seq + 1,
        )
    )

    dummy_map_data = MapData()
    with patch(
        "roborock.devices.traits.b01.q7.map_content.B01MapParser.parse",
        return_value=type("X", (), {"image_content": b"pngbytes", "map_data": dummy_map_data})(),
    ) as parse:
        await q7_api.map_content.refresh()

    assert q7_api.map_content.image_content == b"pngbytes"
    assert q7_api.map_content.map_data is dummy_map_data
    assert q7_api.map_content.raw_api_response == b"raw-map-payload"

    parse.assert_called_once()


def test_q7_map_content_parse_errors_cleanly(q7_api: Q7PropertiesApi):
    with patch("roborock.devices.traits.b01.q7.map_content.B01MapParser.parse", side_effect=ValueError("boom")):
        with pytest.raises(RoborockException, match="Failed to parse B01 map data"):
            q7_api.map_content.parse_map_content(b"raw")


def test_q7_map_content_preserves_specific_roborock_errors(q7_api: Q7PropertiesApi):
    with patch(
        "roborock.devices.traits.b01.q7.map_content.B01MapParser.parse",
        side_effect=RoborockException("Specific decoder failure"),
    ):
        with pytest.raises(RoborockException, match="Specific decoder failure"):
            q7_api.map_content.parse_map_content(b"raw")


def test_q7_map_content_requires_metadata_at_init(fake_channel: FakeChannel):
    from roborock.data import HomeDataDevice, HomeDataProduct, RoborockCategory

    with pytest.raises(ValueError, match="requires device serial number and product model metadata"):
        Q7PropertiesApi(
            cast(MqttChannel, fake_channel),
            device=HomeDataDevice(
                duid="abc123",
                name="Q7",
                local_key="key123key123key1",
                product_id="product-id-q7",
                sn=None,
            ),
            product=HomeDataProduct(
                id="product-id-q7",
                name="Roborock Q7",
                model="roborock.vacuum.sc05",
                category=RoborockCategory.VACUUM,
            ),
        )
