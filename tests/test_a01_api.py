import asyncio
import json
from collections.abc import AsyncGenerator
from queue import Queue
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import paho.mqtt.client as mqtt
import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from roborock import (
    HomeData,
    UserData,
)
from roborock.data import DeviceData, RoborockCategory
from roborock.exceptions import RoborockException
from roborock.protocol import MessageParser
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
    RoborockZeoProtocol,
)
from roborock.version_a01_apis import RoborockMqttClientA01
from tests.mock_data import (
    HOME_DATA_RAW,
    LOCAL_KEY,
    MQTT_PUBLISH_TOPIC,
    USER_DATA,
    WASHER_PRODUCT,
    ZEO_ONE_DEVICE,
)

from . import mqtt_packet
from .conftest import QUEUE_TIMEOUT

RELEASE_TIMEOUT = 2


@pytest.fixture(name="category")
def category_fixture() -> RoborockCategory:
    return RoborockCategory.WASHING_MACHINE


@pytest.fixture(name="a01_mqtt_client")
async def a01_mqtt_client_fixture(
    mock_create_connection: None,
    mock_select: None,
    category: RoborockCategory,
) -> AsyncGenerator[RoborockMqttClientA01, None]:
    user_data = UserData.from_dict(USER_DATA)
    home_data = HomeData.from_dict(
        {
            **HOME_DATA_RAW,
            "devices": [ZEO_ONE_DEVICE],
            "products": [WASHER_PRODUCT],
        }
    )
    device_info = DeviceData(
        device=home_data.devices[0],
        model=home_data.products[0].model,
    )
    client = RoborockMqttClientA01(user_data, device_info, category, queue_timeout=QUEUE_TIMEOUT)
    try:
        yield client
    finally:
        # Cleanup is best effort to reduce number of active threads
        if client.is_connected():
            try:
                async with asyncio.timeout(RELEASE_TIMEOUT):
                    await client.async_release()
            except Exception:
                pass


@pytest.fixture(name="connected_a01_mqtt_client")
async def connected_a01_mqtt_client_fixture(
    response_queue: Queue, a01_mqtt_client: RoborockMqttClientA01
) -> AsyncGenerator[RoborockMqttClientA01, None]:
    response_queue.put(mqtt_packet.gen_connack(rc=0, flags=2))
    response_queue.put(mqtt_packet.gen_suback(1, 0))
    await a01_mqtt_client.async_connect()
    yield a01_mqtt_client


async def test_async_connect(received_requests: Queue, connected_a01_mqtt_client: RoborockMqttClientA01) -> None:
    """Test connecting to the MQTT broker."""

    assert connected_a01_mqtt_client.is_connected()
    # Connecting again is a no-op
    await connected_a01_mqtt_client.async_connect()
    assert connected_a01_mqtt_client.is_connected()

    await connected_a01_mqtt_client.async_disconnect()
    assert not connected_a01_mqtt_client.is_connected()

    # Broker received a connect and subscribe. Disconnect packet is not
    # guaranteed to be captured by the time the async_disconnect returns
    assert received_requests.qsize() >= 2  # Connect and Subscribe


async def test_connect_failure(
    received_requests: Queue, response_queue: Queue, a01_mqtt_client: RoborockMqttClientA01
) -> None:
    """Test the broker responding with a connect failure."""

    response_queue.put(mqtt_packet.gen_connack(rc=1))

    with pytest.raises(RoborockException, match="Failed to connect"):
        await a01_mqtt_client.async_connect()
    assert not a01_mqtt_client.is_connected()
    assert received_requests.qsize() == 1  # Connect attempt


async def test_disconnect_already_disconnected(connected_a01_mqtt_client: RoborockMqttClientA01) -> None:
    """Test the MQTT client error handling for a no-op disconnect."""

    assert connected_a01_mqtt_client.is_connected()

    # Make the MQTT client simulate returning that it already thinks it is disconnected
    with patch("roborock.cloud_api.mqtt.Client.disconnect", return_value=mqtt.MQTT_ERR_NO_CONN):
        await connected_a01_mqtt_client.async_disconnect()


async def test_disconnect_failure(connected_a01_mqtt_client: RoborockMqttClientA01) -> None:
    """Test that the MQTT client ignores  MQTT client error handling for a no-op disconnect."""

    assert connected_a01_mqtt_client.is_connected()

    # Make the MQTT client returns with an error when disconnecting
    with (
        patch("roborock.cloud_api.mqtt.Client.disconnect", return_value=mqtt.MQTT_ERR_PROTOCOL),
        pytest.raises(RoborockException, match="Failed to disconnect"),
    ):
        await connected_a01_mqtt_client.async_disconnect()


async def test_async_release(connected_a01_mqtt_client: RoborockMqttClientA01) -> None:
    """Test the async_release API will disconnect the client."""
    await connected_a01_mqtt_client.async_release()
    assert not connected_a01_mqtt_client.is_connected()


async def test_subscribe_failure(
    received_requests: Queue, response_queue: Queue, a01_mqtt_client: RoborockMqttClientA01
) -> None:
    """Test the broker responding with the wrong message type on subscribe."""

    response_queue.put(mqtt_packet.gen_connack(rc=0, flags=2))

    with (
        patch("roborock.cloud_api.mqtt.Client.subscribe", return_value=(mqtt.MQTT_ERR_NO_CONN, None)),
        pytest.raises(RoborockException, match="Failed to subscribe"),
    ):
        await a01_mqtt_client.async_connect()

    assert received_requests.qsize() == 1  # Connect attempt

    # NOTE: The client is "connected" but not "subscribed" and cannot recover
    # from this state without disconnecting first. This can likely be improved.
    assert a01_mqtt_client.is_connected()

    # Attempting to reconnect is a no-op since the client already thinks it is connected
    await a01_mqtt_client.async_connect()
    assert a01_mqtt_client.is_connected()
    assert received_requests.qsize() == 1


def build_rpc_response(message: dict[Any, Any]) -> bytes:
    """Build an encoded RPC response message."""
    return MessageParser.build(
        [
            RoborockMessage(
                protocol=RoborockMessageProtocol.RPC_RESPONSE,
                payload=pad(
                    json.dumps(
                        {
                            "dps": message,  # {10000: json.dumps(message)},
                        }
                    ).encode(),
                    AES.block_size,
                ),
                version=b"A01",
                seq=2020,
            ),
        ],
        local_key=LOCAL_KEY,
    )


async def test_update_zeo_values(
    received_requests: Queue,
    response_queue: Queue,
    connected_a01_mqtt_client: RoborockMqttClientA01,
) -> None:
    """Test sending an arbitrary MQTT message and parsing the response."""

    message = build_rpc_response(
        {
            203: 6,  # spinning
            207: 3,  # medium
            226: 1,
            227: 0,
            224: 1,  # Times after clean. Testing int value
            218: 0,  # Washing left. Testing zero int value
        }
    )
    response_queue.put(mqtt_packet.gen_publish(MQTT_PUBLISH_TOPIC, payload=message))

    data = await connected_a01_mqtt_client.update_values(
        [
            RoborockZeoProtocol.STATE,
            RoborockZeoProtocol.TEMP,
            RoborockZeoProtocol.DETERGENT_EMPTY,
            RoborockZeoProtocol.SOFTENER_EMPTY,
            RoborockZeoProtocol.TIMES_AFTER_CLEAN,
            RoborockZeoProtocol.WASHING_LEFT,
        ]
    )
    assert data == {
        RoborockZeoProtocol.STATE: "spinning",
        RoborockZeoProtocol.TEMP: "medium",
        RoborockZeoProtocol.DETERGENT_EMPTY: True,
        RoborockZeoProtocol.SOFTENER_EMPTY: False,
        RoborockZeoProtocol.TIMES_AFTER_CLEAN: 1,
        RoborockZeoProtocol.WASHING_LEFT: 0,
    }


@pytest.mark.parametrize("category", [RoborockCategory.WET_DRY_VAC])
async def test_update_dyad_values(
    received_requests: Queue,
    response_queue: Queue,
    connected_a01_mqtt_client: RoborockMqttClientA01,
) -> None:
    """Test sending an arbitrary MQTT message and parsing the response."""

    message = build_rpc_response(
        {
            201: 3,  # charging
            215: 920,  # Brush left
            209: 74,  # Power
            222: 1,  # STAND_LOCK_AUTO_RUN on
            224: 0,  # AUTO_DRY_MODE off
        }
    )
    response_queue.put(mqtt_packet.gen_publish(MQTT_PUBLISH_TOPIC, payload=message))

    data = await connected_a01_mqtt_client.update_values(
        [
            RoborockDyadDataProtocol.STATUS,
            RoborockDyadDataProtocol.BRUSH_LEFT,
            RoborockDyadDataProtocol.POWER,
            RoborockDyadDataProtocol.STAND_LOCK_AUTO_RUN,
            RoborockDyadDataProtocol.AUTO_DRY_MODE,
        ]
    )
    assert data == {
        RoborockDyadDataProtocol.STATUS: "charging",
        RoborockDyadDataProtocol.BRUSH_LEFT: 304800,
        RoborockDyadDataProtocol.POWER: 74,
        RoborockDyadDataProtocol.STAND_LOCK_AUTO_RUN: True,
        RoborockDyadDataProtocol.AUTO_DRY_MODE: False,
    }


async def test_set_value(
    received_requests: Queue,
    response_queue: Queue,
    connected_a01_mqtt_client: RoborockMqttClientA01,
) -> None:
    """Test sending an arbitrary MQTT message and parsing the response."""
    # Clear existing messages received during setup
    assert received_requests.qsize() == 2
    assert received_requests.get(block=True, timeout=QUEUE_TIMEOUT)
    assert received_requests.get(block=True, timeout=QUEUE_TIMEOUT)
    assert received_requests.empty()

    # Prepare the response message
    message = build_rpc_response({})
    response_queue.put(mqtt_packet.gen_publish(MQTT_PUBLISH_TOPIC, payload=message))

    await connected_a01_mqtt_client.set_value(RoborockZeoProtocol.STATE, "spinning")
    assert received_requests.get(block=True)


async def test_publish_failure(
    connected_a01_mqtt_client: RoborockMqttClientA01,
) -> None:
    """Test a failure return code when publishing a messaage."""

    msg = mqtt.MQTTMessageInfo(0)
    msg.rc = mqtt.MQTT_ERR_PROTOCOL
    with (
        patch("roborock.cloud_api.mqtt.Client.publish", return_value=msg),
        pytest.raises(RoborockException, match="Failed to publish"),
    ):
        await connected_a01_mqtt_client.update_values([RoborockZeoProtocol.STATE])


async def test_future_timeout(
    connected_a01_mqtt_client: RoborockMqttClientA01,
) -> None:
    """Test a timeout raised while waiting for an RPC response."""
    with patch("roborock.roborock_future.asyncio.timeout", side_effect=asyncio.TimeoutError):
        data = await connected_a01_mqtt_client.update_values([RoborockZeoProtocol.STATE])
    assert data.get(RoborockZeoProtocol.STATE) is None


async def test_send_decoded_command_handles_stringified_query() -> None:
    """Test that send_decoded_command handles ID_QUERY as a stringified list."""
    from roborock.devices.a01_channel import send_decoded_command
    from roborock.devices.mqtt_channel import MqttChannel
    from roborock.roborock_message import RoborockDyadDataProtocol, RoborockMessage, RoborockMessageProtocol

    channel = MagicMock(spec=MqttChannel)
    channel.publish = AsyncMock()

    captured_callback = None

    async def mock_subscribe(callback):
        nonlocal captured_callback
        captured_callback = callback
        return lambda: None

    channel.subscribe = AsyncMock(side_effect=mock_subscribe)

    protocol_id = 101
    params = {RoborockDyadDataProtocol.ID_QUERY: str([protocol_id])}

    task = asyncio.create_task(send_decoded_command(channel, params))
    await asyncio.sleep(0)

    response_data = {"dps": {str(protocol_id): 123}}
    payload = pad(json.dumps(response_data).encode("utf-8"), AES.block_size)
    message = RoborockMessage(protocol=RoborockMessageProtocol.RPC_RESPONSE, payload=payload)

    if captured_callback:
        captured_callback(message)

    result = await task
    assert result == {protocol_id: 123}
