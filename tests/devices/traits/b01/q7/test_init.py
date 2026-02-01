import json
from typing import Any

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from roborock.data.b01_q7 import (
    CleanTaskTypeMapping,
    SCDeviceCleanParam,
    SCWindMapping,
    WaterLevelMapping,
    WorkStatusMapping,
)
from roborock.devices.rpc.b01_q7_channel import send_decoded_command
from roborock.devices.traits.b01.q7 import Q7PropertiesApi
from roborock.exceptions import RoborockException
from roborock.protocols.b01_q7_protocol import B01_VERSION, Q7RequestMessage
from roborock.roborock_message import RoborockB01Props, RoborockMessageProtocol
from tests.fixtures.channel_fixtures import FakeChannel

from . import B01MessageBuilder


async def test_q7_api_query_values(
    q7_api: Q7PropertiesApi, fake_channel: FakeChannel, message_builder: B01MessageBuilder
):
    """Test that Q7PropertiesApi correctly converts raw values."""
    # We need to construct the expected result based on the mappings
    # status: 1 -> WAITING_FOR_ORDERS
    # wind: 2 -> STANDARD
    response_data = {
        "status": 1,
        "wind": 2,
        "battery": 100,
    }

    # Queue the response
    fake_channel.response_queue.append(message_builder.build(response_data))

    result = await q7_api.query_values(
        [
            RoborockB01Props.STATUS,
            RoborockB01Props.WIND,
        ]
    )

    assert result is not None
    assert result.status == WorkStatusMapping.WAITING_FOR_ORDERS
    # wind might be mapped to SCWindMapping.STANDARD (2)
    # let's verify checking the prop definition in B01Props
    # wind: SCWindMapping | None = None
    # SCWindMapping.STANDARD is 2 ('balanced')
    from roborock.data.b01_q7 import SCWindMapping

    assert result.wind == SCWindMapping.STANDARD

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    assert message.protocol == RoborockMessageProtocol.RPC_REQUEST
    assert message.version == B01_VERSION

    # Verify request payload
    assert message.payload is not None
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    # {"dps": {"10000": {"method": "prop.get", "msgId": "123456789", "params": {"property": ["status", "wind"]}}}}
    assert "dps" in payload_data
    assert "10000" in payload_data["dps"]
    inner = payload_data["dps"]["10000"]
    assert inner["method"] == "prop.get"
    assert inner["msgId"] == str(message_builder.msg_id)
    assert inner["params"] == {"property": [RoborockB01Props.STATUS, RoborockB01Props.WIND]}


@pytest.mark.parametrize(
    ("query", "response_data", "expected_status"),
    [
        (
            [RoborockB01Props.STATUS],
            {"status": 2},
            WorkStatusMapping.PAUSED,
        ),
        (
            [RoborockB01Props.STATUS],
            {"status": 5},
            WorkStatusMapping.SWEEP_MOPING,
        ),
    ],
)
async def test_q7_response_value_mapping(
    query: list[RoborockB01Props],
    response_data: dict[str, Any],
    expected_status: WorkStatusMapping,
    q7_api: Q7PropertiesApi,
    fake_channel: FakeChannel,
    message_builder: B01MessageBuilder,
):
    """Test Q7PropertiesApi value mapping for different statuses."""
    fake_channel.response_queue.append(message_builder.build(response_data))

    result = await q7_api.query_values(query)

    assert result is not None
    assert result.status == expected_status


async def test_send_decoded_command_non_dict_response(fake_channel: FakeChannel, message_builder: B01MessageBuilder):
    """Test validity of handling non-dict responses (should not timeout)."""
    message = message_builder.build("some_string_error")
    fake_channel.response_queue.append(message)

    # Use a random string for command type to avoid needing import

    with pytest.raises(RoborockException, match="Unexpected data type for response"):
        await send_decoded_command(fake_channel, Q7RequestMessage(dps=10000, command="prop.get", params=[]))  # type: ignore[arg-type]


async def test_send_decoded_command_error_code(fake_channel: FakeChannel, message_builder: B01MessageBuilder):
    """Test that non-zero error codes from device are properly handled."""
    message = message_builder.build({}, code=5001)
    fake_channel.response_queue.append(message)

    with pytest.raises(RoborockException, match="B01 command failed with code 5001"):
        await send_decoded_command(fake_channel, Q7RequestMessage(dps=10000, command="prop.get", params=[]))  # type: ignore[arg-type]


async def test_q7_api_set_fan_speed(
    q7_api: Q7PropertiesApi, fake_channel: FakeChannel, message_builder: B01MessageBuilder
):
    """Test setting fan speed."""
    fake_channel.response_queue.append(message_builder.build({"result": "ok"}))
    await q7_api.set_fan_speed(SCWindMapping.STRONG)

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    assert payload_data["dps"]["10000"]["method"] == "prop.set"
    assert payload_data["dps"]["10000"]["params"] == {RoborockB01Props.WIND: SCWindMapping.STRONG.code}


async def test_q7_api_set_water_level(
    q7_api: Q7PropertiesApi, fake_channel: FakeChannel, message_builder: B01MessageBuilder
):
    """Test setting water level."""
    fake_channel.response_queue.append(message_builder.build({"result": "ok"}))
    await q7_api.set_water_level(WaterLevelMapping.HIGH)

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    assert payload_data["dps"]["10000"]["method"] == "prop.set"
    assert payload_data["dps"]["10000"]["params"] == {RoborockB01Props.WATER: WaterLevelMapping.HIGH.code}


async def test_q7_api_start_clean(
    q7_api: Q7PropertiesApi, fake_channel: FakeChannel, message_builder: B01MessageBuilder
):
    """Test starting cleaning."""
    fake_channel.response_queue.append(message_builder.build({"result": "ok"}))
    await q7_api.start_clean()

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    assert payload_data["dps"]["10000"]["method"] == "service.set_room_clean"
    assert payload_data["dps"]["10000"]["params"] == {
        "clean_type": CleanTaskTypeMapping.ALL.code,
        "ctrl_value": SCDeviceCleanParam.START.code,
        "room_ids": [],
    }


async def test_q7_api_pause_clean(
    q7_api: Q7PropertiesApi, fake_channel: FakeChannel, message_builder: B01MessageBuilder
):
    """Test pausing cleaning."""
    fake_channel.response_queue.append(message_builder.build({"result": "ok"}))
    await q7_api.pause_clean()

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    assert payload_data["dps"]["10000"]["method"] == "service.set_room_clean"
    assert payload_data["dps"]["10000"]["params"] == {
        "clean_type": CleanTaskTypeMapping.ALL.code,
        "ctrl_value": SCDeviceCleanParam.PAUSE.code,
        "room_ids": [],
    }


async def test_q7_api_stop_clean(
    q7_api: Q7PropertiesApi, fake_channel: FakeChannel, message_builder: B01MessageBuilder
):
    """Test stopping cleaning."""
    fake_channel.response_queue.append(message_builder.build({"result": "ok"}))
    await q7_api.stop_clean()

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    assert payload_data["dps"]["10000"]["method"] == "service.set_room_clean"
    assert payload_data["dps"]["10000"]["params"] == {
        "clean_type": CleanTaskTypeMapping.ALL.code,
        "ctrl_value": SCDeviceCleanParam.STOP.code,
        "room_ids": [],
    }


async def test_q7_api_return_to_dock(
    q7_api: Q7PropertiesApi, fake_channel: FakeChannel, message_builder: B01MessageBuilder
):
    """Test returning to dock."""
    fake_channel.response_queue.append(message_builder.build({"result": "ok"}))
    await q7_api.return_to_dock()

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    assert payload_data["dps"]["10000"]["method"] == "service.start_recharge"
    assert payload_data["dps"]["10000"]["params"] == {}


async def test_q7_api_find_me(q7_api: Q7PropertiesApi, fake_channel: FakeChannel, message_builder: B01MessageBuilder):
    """Test locating the device."""
    fake_channel.response_queue.append(message_builder.build({"result": "ok"}))
    await q7_api.find_me()

    assert len(fake_channel.published_messages) == 1
    message = fake_channel.published_messages[0]
    payload_data = json.loads(unpad(message.payload, AES.block_size))
    assert payload_data["dps"]["10000"]["method"] == "service.find_device"
    assert payload_data["dps"]["10000"]["params"] == {}
