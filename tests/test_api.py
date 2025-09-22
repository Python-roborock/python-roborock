import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from queue import Queue
from typing import Any
from unittest.mock import AsyncMock, patch

import paho.mqtt.client as mqtt
import pytest

from roborock import (
    HomeData,
    RoborockDockDustCollectionModeCode,
    RoborockDockTypeCode,
    RoborockDockWashTowelModeCode,
    UserData,
)
from roborock.containers import DeviceData, RoomMapping, S7MaxVStatus
from roborock.exceptions import RoborockException, RoborockTimeout
from roborock.protocol import MessageParser
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.version_1_apis import RoborockMqttClientV1
from roborock.web_api import PreparedRequest, RoborockApiClient
from tests.mock_data import (
    BASE_URL_REQUEST,
    GET_CODE_RESPONSE,
    HOME_DATA_RAW,
    LOCAL_KEY,
    MQTT_PUBLISH_TOPIC,
    STATUS,
    USER_DATA,
)

from . import mqtt_packet


def test_can_create_prepared_request():
    PreparedRequest("https://sample.com", AsyncMock())


async def test_can_create_mqtt_roborock():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(device=home_data.devices[0], model=home_data.products[0].model)
    RoborockMqttClientV1(UserData.from_dict(USER_DATA), device_info)


async def test_get_base_url_no_url():
    rc = RoborockApiClient("sample@gmail.com")
    with patch("roborock.web_api.PreparedRequest.request") as mock_request:
        mock_request.return_value = BASE_URL_REQUEST
        await rc._get_iot_login_info()
    assert await rc.base_url == "https://sample.com"


async def test_request_code():
    rc = RoborockApiClient("sample@gmail.com")
    with (
        patch("roborock.web_api.RoborockApiClient._get_iot_login_info"),
        patch("roborock.web_api.RoborockApiClient._get_header_client_id"),
        patch("roborock.web_api.PreparedRequest.request") as mock_request,
    ):
        mock_request.return_value = GET_CODE_RESPONSE
        await rc.request_code()


async def test_get_home_data():
    rc = RoborockApiClient("sample@gmail.com")
    with (
        patch("roborock.web_api.RoborockApiClient._get_iot_login_info"),
        patch("roborock.web_api.RoborockApiClient._get_header_client_id"),
        patch("roborock.web_api.PreparedRequest.request") as mock_prepared_request,
    ):
        mock_prepared_request.side_effect = [
            {"code": 200, "msg": "success", "data": {"rrHomeId": 1}},
            {"code": 200, "success": True, "result": HOME_DATA_RAW},
        ]

        user_data = UserData.from_dict(USER_DATA)
        result = await rc.get_home_data(user_data)

        assert result == HomeData.from_dict(HOME_DATA_RAW)


async def test_get_dust_collection_mode():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(device=home_data.devices[0], model=home_data.products[0].model)
    rmc = RoborockMqttClientV1(UserData.from_dict(USER_DATA), device_info)
    with patch("roborock.version_1_apis.roborock_client_v1.AttributeCache.async_value") as command:
        command.return_value = {"mode": 1}
        dust = await rmc.get_dust_collection_mode()
        assert dust is not None
        assert dust.mode == RoborockDockDustCollectionModeCode.light


async def test_get_mop_wash_mode():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(device=home_data.devices[0], model=home_data.products[0].model)
    rmc = RoborockMqttClientV1(UserData.from_dict(USER_DATA), device_info)
    with patch("roborock.version_1_apis.roborock_client_v1.AttributeCache.async_value") as command:
        command.return_value = {"smart_wash": 0, "wash_interval": 1500}
        mop_wash = await rmc.get_smart_wash_params()
        assert mop_wash is not None
        assert mop_wash.smart_wash == 0
        assert mop_wash.wash_interval == 1500


async def test_get_washing_mode():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(device=home_data.devices[0], model=home_data.products[0].model)
    rmc = RoborockMqttClientV1(UserData.from_dict(USER_DATA), device_info)
    with patch("roborock.version_1_apis.roborock_client_v1.AttributeCache.async_value") as command:
        command.return_value = {"wash_mode": 2}
        washing_mode = await rmc.get_wash_towel_mode()
        assert washing_mode is not None
        assert washing_mode.wash_mode == RoborockDockWashTowelModeCode.deep
        assert washing_mode.wash_mode == 2


async def test_get_prop():
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(device=home_data.devices[0], model=home_data.products[0].model)
    rmc = RoborockMqttClientV1(UserData.from_dict(USER_DATA), device_info)
    with (
        patch("roborock.version_1_apis.roborock_mqtt_client_v1.RoborockMqttClientV1.get_status") as get_status,
        patch("roborock.version_1_apis.roborock_client_v1.RoborockClientV1.send_command"),
        patch("roborock.version_1_apis.roborock_client_v1.AttributeCache.async_value"),
        patch("roborock.version_1_apis.roborock_mqtt_client_v1.RoborockMqttClientV1.get_dust_collection_mode"),
    ):
        status = S7MaxVStatus.from_dict(STATUS)
        status.dock_type = RoborockDockTypeCode.auto_empty_dock_pure
        get_status.return_value = status

        props = await rmc.get_prop()
        assert props
        assert props.dock_summary
        assert props.dock_summary.wash_towel_mode is None
        assert props.dock_summary.smart_wash_params is None
        assert props.dock_summary.dust_collection_mode is not None


@pytest.fixture(name="connected_mqtt_client")
async def connected_mqtt_client_fixture(
    response_queue: Queue, mqtt_client: RoborockMqttClientV1
) -> AsyncGenerator[RoborockMqttClientV1, None]:
    response_queue.put(mqtt_packet.gen_connack(rc=0, flags=2))
    response_queue.put(mqtt_packet.gen_suback(1, 0))
    await mqtt_client.async_connect()
    yield mqtt_client
    if mqtt_client.is_connected():
        try:
            await mqtt_client.async_disconnect()
        except Exception:
            pass


async def test_async_connect(received_requests: Queue, connected_mqtt_client: RoborockMqttClientV1) -> None:
    """Test connecting to the MQTT broker."""

    assert connected_mqtt_client.is_connected()
    # Connecting again is a no-op
    await connected_mqtt_client.async_connect()
    assert connected_mqtt_client.is_connected()

    await connected_mqtt_client.async_disconnect()
    assert not connected_mqtt_client.is_connected()

    # Broker received a connect and subscribe. Disconnect packet is not
    # guaranteed to be captured by the time the async_disconnect returns
    assert received_requests.qsize() >= 2  # Connect and Subscribe


async def test_connect_failure_response(
    received_requests: Queue, response_queue: Queue, mqtt_client: RoborockMqttClientV1
) -> None:
    """Test the broker responding with a connect failure."""

    response_queue.put(mqtt_packet.gen_connack(rc=1))

    with pytest.raises(RoborockException, match="Failed to connect"):
        await mqtt_client.async_connect()
    assert not mqtt_client.is_connected()
    assert received_requests.qsize() == 1  # Connect attempt


async def test_disconnect_already_disconnected(connected_mqtt_client: RoborockMqttClientV1) -> None:
    """Test the MQTT client error handling for a no-op disconnect."""

    assert connected_mqtt_client.is_connected()

    # Make the MQTT client simulate returning that it already thinks it is disconnected
    with patch("roborock.cloud_api.mqtt.Client.disconnect", return_value=mqtt.MQTT_ERR_NO_CONN):
        await connected_mqtt_client.async_disconnect()


async def test_disconnect_failure(connected_mqtt_client: RoborockMqttClientV1) -> None:
    """Test that the MQTT client ignores  MQTT client error handling for a no-op disconnect."""

    assert connected_mqtt_client.is_connected()

    # Make the MQTT client returns with an error when disconnecting
    with (
        patch("roborock.cloud_api.mqtt.Client.disconnect", return_value=mqtt.MQTT_ERR_PROTOCOL),
        pytest.raises(RoborockException, match="Failed to disconnect"),
    ):
        await connected_mqtt_client.async_disconnect()


async def test_disconnect_failure_response(
    received_requests: Queue,
    response_queue: Queue,
    connected_mqtt_client: RoborockMqttClientV1,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the broker responding with a connect failure."""

    # Enqueue a failed message -- however, the client does not process any
    # further messages and there is no parsing error, and no failed log messages.
    response_queue.put(mqtt_packet.gen_disconnect(reason_code=1))
    assert connected_mqtt_client.is_connected()
    with caplog.at_level(logging.ERROR):
        await connected_mqtt_client.async_disconnect()
        assert not connected_mqtt_client.is_connected()
        assert not caplog.records


async def test_async_release(connected_mqtt_client: RoborockMqttClientV1) -> None:
    """Test the async_release API will disconnect the client."""
    await connected_mqtt_client.async_release()
    assert not connected_mqtt_client.is_connected()


async def test_subscribe_failure(
    received_requests: Queue, response_queue: Queue, mqtt_client: RoborockMqttClientV1
) -> None:
    """Test the broker responding with the wrong message type on subscribe."""

    response_queue.put(mqtt_packet.gen_connack(rc=0, flags=2))

    with (
        patch("roborock.cloud_api.mqtt.Client.subscribe", return_value=(mqtt.MQTT_ERR_NO_CONN, None)),
        pytest.raises(RoborockException, match="Failed to subscribe"),
    ):
        await mqtt_client.async_connect()

    assert received_requests.qsize() == 1  # Connect attempt

    # NOTE: The client is "connected" but not "subscribed" and cannot recover
    # from this state without disconnecting first. This can likely be improved.
    assert mqtt_client.is_connected()

    # Attempting to reconnect is a no-op since the client already thinks it is connected
    await mqtt_client.async_connect()
    assert mqtt_client.is_connected()
    assert received_requests.qsize() == 1


def build_rpc_response(message: dict[str, Any]) -> bytes:
    """Build an encoded RPC response message."""
    return MessageParser.build(
        [
            RoborockMessage(
                protocol=RoborockMessageProtocol.RPC_RESPONSE,
                payload=json.dumps(
                    {
                        "dps": {102: json.dumps(message)},
                    }
                ).encode(),
                seq=2020,
            ),
        ],
        local_key=LOCAL_KEY,
    )


async def test_get_room_mapping(
    received_requests: Queue,
    response_queue: Queue,
    connected_mqtt_client: RoborockMqttClientV1,
) -> None:
    """Test sending an arbitrary MQTT message and parsing the response."""

    test_request_id = 5050
    message = build_rpc_response(
        {
            "id": test_request_id,
            "result": [[16, "2362048"], [17, "2362044"]],
        }
    )
    response_queue.put(mqtt_packet.gen_publish(MQTT_PUBLISH_TOPIC, payload=message))

    with patch("roborock.protocols.v1_protocol.get_next_int", return_value=test_request_id):
        room_mapping = await connected_mqtt_client.get_room_mapping()

    assert room_mapping == [
        RoomMapping(segment_id=16, iot_id="2362048"),
        RoomMapping(segment_id=17, iot_id="2362044"),
    ]


async def test_publish_failure(
    connected_mqtt_client: RoborockMqttClientV1,
) -> None:
    """Test a failure return code when publishing a messaage."""

    msg = mqtt.MQTTMessageInfo(0)
    msg.rc = mqtt.MQTT_ERR_PROTOCOL
    with (
        patch("roborock.cloud_api.mqtt.Client.publish", return_value=msg),
        pytest.raises(RoborockException, match="Failed to publish"),
    ):
        await connected_mqtt_client.get_room_mapping()


async def test_future_timeout(
    connected_mqtt_client: RoborockMqttClientV1,
) -> None:
    """Test a timeout raised while waiting for an RPC response."""
    with (
        patch("roborock.roborock_future.async_timeout.timeout", side_effect=asyncio.TimeoutError),
        pytest.raises(RoborockTimeout, match="Timeout after"),
    ):
        await connected_mqtt_client.get_room_mapping()
