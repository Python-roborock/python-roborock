import datetime
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, call, patch

import pytest

from roborock.devices.mqtt_channel import MqttChannel
from roborock.devices.traits.a01 import DyadApi, ZeoApi
from roborock.roborock_message import RoborockDyadDataProtocol, RoborockZeoProtocol


@pytest.fixture(name="mock_channel")
def mock_channel_fixture() -> AsyncMock:
    return AsyncMock(spec=MqttChannel)


@pytest.fixture(name="mock_send")
def mock_send_fixture(mock_channel) -> Generator[AsyncMock, None, None]:
    with patch("roborock.devices.traits.a01.send_decoded_command") as mock_send:
        yield mock_send


async def test_dyad_api_query_values(mock_channel: AsyncMock, mock_send: AsyncMock):
    """Test that DyadApi currently returns raw values without conversion."""
    api = DyadApi(mock_channel)

    mock_send.return_value = {
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
    result = await api.query_values(
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

    # Note: Bug here, this is the wrong encoding for the query
    assert mock_send.call_args_list == [
        call(
            mock_channel,
            {
                RoborockDyadDataProtocol.ID_QUERY: "[209, 201, 207, 214, 215, 227, 229, 230, 222, 224]",
            },
        ),
    ]


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
    mock_channel: AsyncMock,
    mock_send: AsyncMock,
    query: list[RoborockDyadDataProtocol],
    response: dict[int, Any],
    expected_result: dict[RoborockDyadDataProtocol, Any],
):
    """Test that DyadApi currently returns raw values without conversion."""
    api = DyadApi(mock_channel)

    mock_send.return_value = response
    result = await api.query_values(query)
    assert result == expected_result


async def test_zeo_api_query_values(mock_channel: AsyncMock, mock_send: AsyncMock):
    """Test that ZeoApi currently returns raw values without conversion."""
    api = ZeoApi(mock_channel)

    mock_send.return_value = {
        203: 6,  # spinning
        207: 3,  # medium
        226: 1,
        227: 0,
        224: 1,  # Times after clean. Testing int value
        218: 0,  # Washing left. Testing zero int value
    }
    result = await api.query_values(
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
    # Note: Bug here, this is the wrong encoding for the query
    assert mock_send.call_args_list == [
        call(
            mock_channel,
            {
                RoborockZeoProtocol.ID_QUERY: "[203, 207, 226, 227, 224, 218]",
            },
        ),
    ]


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
    mock_channel: AsyncMock,
    mock_send: AsyncMock,
    query: list[RoborockZeoProtocol],
    response: dict[int, Any],
    expected_result: dict[RoborockZeoProtocol, Any],
):
    """Test that ZeoApi currently returns raw values without conversion."""
    api = ZeoApi(mock_channel)

    mock_send.return_value = response
    result = await api.query_values(query)
    assert result == expected_result
