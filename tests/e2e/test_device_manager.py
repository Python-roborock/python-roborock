"""End-to-end tests for MQTT session.

These tests use a real EMQX broker to verify the session implementation over
TCP, including the actual zmqtt protocol and subscription lifecycle.

These are higher level tests than the similar tests in tests/mqtt/test_roborock_session.py
which use mocks to verify specific behaviors.
"""

import asyncio
import copy
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any, cast

import pytest
import syrupy
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from roborock.data.b01_q7 import WorkStatusMapping
from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.containers import UserData
from roborock.data.zeo.zeo_code_mappings import ZeoState
from roborock.devices.cache import Cache, InMemoryCache
from roborock.devices.device_manager import DeviceManager, UserParams, create_device_manager
from roborock.protocol import MessageParser
from roborock.protocols.a01_protocol import A01_VERSION
from roborock.protocols.b01_q7_protocol import B01_VERSION
from roborock.protocols.v1_protocol import LocalProtocolVersion
from roborock.roborock_message import RoborockB01Props, RoborockMessage, RoborockMessageProtocol, RoborockZeoProtocol
from roborock.web_api import RoborockApiClient
from tests import mock_data
from tests.fixtures.logging import CapturedRequestLog
from tests.fixtures.mqtt import MQTT_HOST, MQTT_PORT, MqttResponder
from tests.mock_data import HOME_DATA_RAW, LOCAL_KEY

TEST_USERNAME = "user@example.com"
TEST_CODE = 1234

# The topic used for the user + device. This is determined from the fake Home
# data API response.
TEST_TOPIC_FORMAT = "rr/m/o/user123/19648f94/{duid}"
TEST_REQUEST_TOPIC_FORMAT = "rr/m/i/user123/19648f94/{duid}"
TEST_RANDOM = 23
TEST_HOST = mock_data.TEST_LOCAL_API_HOST
NETWORK_INFO = {
    "ip": TEST_HOST,
    "ssid": "test_wifi",
    "mac": "aa:bb:cc:dd:ee:ff",
    "bssid": "aa:bb:cc:dd:ee:ff",
    "rssi": -50,
}
# For tests that want to skip the web API login flow
TEST_USER_DATA = cast(dict[str, Any], copy.deepcopy(mock_data.USER_DATA))
TEST_USER_DATA["rriot"]["r"]["m"] = f"tcp://{MQTT_HOST}:{MQTT_PORT}"
TEST_USER_PARAMS = UserParams(
    username=TEST_USERNAME,
    user_data=UserData.from_dict(TEST_USER_DATA),
    base_url=mock_data.BASE_URL,
)


@pytest.fixture(autouse=True)
def auto_mock_local_client(mock_async_create_local_connection: None) -> None:
    """Automatically use the mock local client fixture."""


@pytest.fixture(name="device_manager_factory")
async def device_manager_factory_fixture() -> AsyncGenerator[Callable[[UserParams], Awaitable[DeviceManager]], None]:
    """Fixture to create a device manager and handle auto shutdown on test failure."""

    cleanup_tasks: list[Callable[[], Awaitable[None]]] = []
    cache: Cache = InMemoryCache()

    async def factory(user_params: UserParams) -> DeviceManager:
        """Create a device manager and auto cleanup."""
        device_manager = await create_device_manager(user_params, cache=cache)
        cleanup_tasks.append(device_manager.close)
        return device_manager

    yield factory

    await asyncio.gather(*[task() for task in cleanup_tasks])


class ResponseBuilder:
    """Utility class to build raw response messages.

    This helps keep track of sequence numbers and timestamps mostly to remove
    them from the main test body. These are mostly ignored by the client in the
    response.
    """

    def __init__(self) -> None:
        """Initialize the response builder."""
        self.seq_counter = 0
        self.timestamp_counter = 1766520441
        self.connect_nonce: int | None = None
        self.ack_nonce: int | None = None
        self.protocol = RoborockMessageProtocol.RPC_RESPONSE
        self.version: bytes = LocalProtocolVersion.V1.value.encode()

    def build_v1(
        self,
        payload: bytes,
        protocol: RoborockMessageProtocol | None = None,
    ) -> bytes:
        """Build an encoded response message."""
        self.seq_counter += 1
        return self._encrypt(
            self._build_roborock_message(
                payload=payload,
                protocol=protocol if protocol is not None else self.protocol,
            ),
        )

    def build_v1_rpc(
        self,
        data: dict[str, Any],
    ) -> bytes:
        """Build an encoded RPC response message."""
        self.timestamp_counter += 1
        return self.build_v1(
            payload=json.dumps(
                {
                    "t": self.timestamp_counter,
                    "dps": {
                        "102": json.dumps(data),
                    },
                }
            ).encode(),
        )

    def build_a01_rpc(self, data: dict[str, Any]) -> bytes:
        """Build an encoded A01 RPC response message."""
        self.timestamp_counter += 1
        return self._encrypt(
            self._build_roborock_message(
                payload=pad(json.dumps({"dps": data}).encode(), AES.block_size),
            ),
        )

    def build_b01_q7_rpc(self, data: dict[str, Any] | str, code: int | None = None, msg_id: int | None = None) -> bytes:
        """Build an encoded B01 RPC response message."""
        message: dict[str, Any] = {
            "msgId": str(msg_id),
            "data": data,
        }
        if code is not None:
            message["code"] = code
        return self._build_b01_dps(message)

    def _build_b01_dps(self, message: dict[str, Any] | str) -> bytes:
        """Build an encoded B01 RPC response message given an inner message."""
        dps_payload = {"dps": {"10000": json.dumps(message)}}
        self.seq_counter += 1
        return self._encrypt(
            self._build_roborock_message(
                payload=json.dumps(dps_payload).encode(),
            ),
        )

    def _build_roborock_message(
        self,
        payload: bytes,
        protocol: RoborockMessageProtocol | None = None,
    ) -> RoborockMessage:
        """Build a Roborock message."""
        return RoborockMessage(
            protocol=protocol if protocol is not None else self.protocol,
            random=TEST_RANDOM,
            seq=self.seq_counter,
            payload=payload,
            version=self.version,
        )

    def _encrypt(self, message: RoborockMessage) -> bytes:
        """Encrypt a message."""
        return MessageParser.build(
            message,
            local_key=LOCAL_KEY,
            connect_nonce=self.connect_nonce,
            ack_nonce=self.ack_nonce,
        )


async def test_v1_device(
    mock_rest: Any,
    local_response_queue: asyncio.Queue[bytes],
    local_received_requests: asyncio.Queue[bytes],
    log: CapturedRequestLog,
    snapshot: syrupy.SnapshotAssertion,
    device_manager_factory: Callable[[UserParams], Awaitable[DeviceManager]],
) -> None:
    """Test the device manager end to end flow with a v1 device."""

    # Simulate the login flow to get user params
    web_api = RoborockApiClient(username=TEST_USERNAME)
    await web_api.request_code()
    user_data = await web_api.code_login(TEST_CODE)
    user_data.rriot.r.m = f"tcp://{MQTT_HOST}:{MQTT_PORT}"

    # Prepare the device response sent through the real broker.
    response_builder = ResponseBuilder()
    test_topic = TEST_TOPIC_FORMAT.format(duid="abc123")
    request_topic = TEST_REQUEST_TOPIC_FORMAT.format(duid="abc123")
    mqtt_responses = [response_builder.build_v1_rpc(data={"id": 9090, "result": NETWORK_INFO})]

    # Prepare local device responses. The ids are deterministic based on deterministic_message_fixtures
    response_builder.seq_counter = 0
    local_responses: list[bytes] = [
        # Queue HELLO response
        response_builder.build_v1(protocol=RoborockMessageProtocol.HELLO_RESPONSE, payload=b"ok"),
        # Feature discovery part 1 & 2
        response_builder.build_v1_rpc(data={"id": 9094, "result": [mock_data.APP_GET_INIT_STATUS]}),
        response_builder.build_v1_rpc(data={"id": 9097, "result": [mock_data.STATUS]}),
    ]
    for payload in local_responses:
        local_response_queue.put_nowait(payload)

    # Create the device manager
    user_params = UserParams(
        username=TEST_USERNAME,
        user_data=user_data,
        base_url=await web_api.base_url,
    )
    async with MqttResponder(request_topic, test_topic, mqtt_responses, log) as responder:
        device_manager = await device_manager_factory(user_params)
        await responder.wait()

    # The mocked Home Data API returns a single v1 device
    devices = await device_manager.get_devices()
    assert len(devices) == 1
    device = devices[0]
    assert device.duid == "abc123"
    assert device.name == "Roborock S7 MaxV"
    assert device.is_connected
    assert device.is_local_connected

    # Verify GET_STATUS response based on mock_data.STATUS
    assert device.v1_properties
    assert device.v1_properties.status
    assert device.v1_properties.status.state_name == "charging"
    assert device.v1_properties.status.battery == 100
    assert device.v1_properties.status.clean_time == 1176

    # Verify arbitrary device features
    assert device.v1_properties.device_features.is_show_clean_finish_reason_supported
    assert device.v1_properties.device_features.is_customized_clean_supported
    assert not device.v1_properties.device_features.is_matter_supported

    # Close the device manager. We will test re-connecting and reusing the network
    # information and device discovery information from the cache.
    await device_manager.close()

    # Prepare local device responses.
    response_builder.seq_counter = 0
    local_response_queue.put_nowait(
        response_builder.build_v1(protocol=RoborockMessageProtocol.HELLO_RESPONSE, payload=b"ok")
    )
    local_response_queue.put_nowait(response_builder.build_v1_rpc(data={"id": 9101, "result": [mock_data.STATUS]}))

    device_manager = await device_manager_factory(user_params)

    # The mocked Home Data API returns a single v1 device
    devices = await device_manager.get_devices()
    assert len(devices) == 1
    device = devices[0]
    assert device.duid == "abc123"
    assert device.name == "Roborock S7 MaxV"
    assert device.is_connected
    assert device.is_local_connected

    # Verify arbitrary device features from cache
    assert device.v1_properties
    assert device.v1_properties.device_features
    assert device.v1_properties.device_features.is_show_clean_finish_reason_supported
    assert device.v1_properties.device_features.is_customized_clean_supported
    assert not device.v1_properties.device_features.is_matter_supported

    # Dock type is loaded from the cache, but status is refreshed during trait discovery
    # so AM dock capabilities can be evaluated.
    assert device.v1_properties
    assert device.v1_properties.status
    assert device.v1_properties.status.state_name == "charging"

    assert snapshot == log


async def test_l01_device(
    mock_rest: Any,
    local_response_queue: asyncio.Queue[bytes],
    local_received_requests: asyncio.Queue[bytes],
    log: CapturedRequestLog,
    snapshot: syrupy.SnapshotAssertion,
    device_manager_factory: Callable[[UserParams], Awaitable[DeviceManager]],
) -> None:
    """Test the device manager end to end flow with a l01 device."""
    # Prepare the device response sent through the real broker.
    mqtt_response_builder = ResponseBuilder()
    test_topic = TEST_TOPIC_FORMAT.format(duid="abc123")
    request_topic = TEST_REQUEST_TOPIC_FORMAT.format(duid="abc123")
    mqtt_responses = [mqtt_response_builder.build_v1_rpc(data={"id": 9090, "result": NETWORK_INFO})]

    # Prepare local device responses. The ids are deterministic based on deterministic_message_fixtures
    local_response_builder = ResponseBuilder()
    local_response_builder.version = LocalProtocolVersion.L01.value.encode()
    local_response_builder.connect_nonce = 9093
    local_responses: list[bytes] = [
        # Initial V1.0 Hello request will fail and cause a retry with L01
        b"\x00",
        # Queue HELLO response with L01
        local_response_builder.build_v1(protocol=RoborockMessageProtocol.HELLO_RESPONSE, payload=b"ok"),
    ]
    # Feature discovery requests are sent with an ack nonce based on the random sent in HELLO_RESPONSE
    local_response_builder.ack_nonce = TEST_RANDOM
    local_responses.extend(
        [
            local_response_builder.build_v1_rpc(data={"id": 9094, "result": [mock_data.APP_GET_INIT_STATUS]}),
            local_response_builder.build_v1_rpc(data={"id": 9097, "result": [mock_data.STATUS]}),
        ]
    )
    for payload in local_responses:
        local_response_queue.put_nowait(payload)

    # Create the device manager
    async with MqttResponder(request_topic, test_topic, mqtt_responses, log) as responder:
        device_manager = await device_manager_factory(TEST_USER_PARAMS)
        await responder.wait()

    # The mocked Home Data API returns a single v1 device
    devices = await device_manager.get_devices()
    assert len(devices) == 1
    device = devices[0]
    assert device.duid == "abc123"
    assert device.name == "Roborock S7 MaxV"
    assert device.is_connected
    assert device.is_local_connected

    # Verify GET_STATUS response based on mock_data.STATUS
    assert device.v1_properties
    assert device.v1_properties.status
    assert device.v1_properties.status.state_name == "charging"
    assert device.v1_properties.status.battery == 100
    assert device.v1_properties.status.clean_time == 1176

    # Verify arbitrary device features
    assert device.v1_properties.device_features.is_show_clean_finish_reason_supported
    assert device.v1_properties.device_features.is_customized_clean_supported
    assert not device.v1_properties.device_features.is_matter_supported

    assert snapshot == log


@pytest.mark.parametrize(
    "home_data",
    [
        (
            {
                **HOME_DATA_RAW,
                "devices": [mock_data.Q10_DEVICE_DATA],
                "products": [mock_data.SS07_PRODUCT_DATA],
            }
        )
    ],
)
async def test_q10_device(
    mock_rest: Any,
    log: CapturedRequestLog,
    device_manager_factory: Callable[[UserParams], Awaitable[DeviceManager]],
    home_data: dict[str, Any],
    snapshot: syrupy.SnapshotAssertion,
) -> None:
    """Test the device manager end to end flow with a B01 Q10 device."""
    request_topic = TEST_REQUEST_TOPIC_FORMAT.format(duid="device-id-def456")
    response_topic = TEST_TOPIC_FORMAT.format(duid="device-id-def456")
    async with MqttResponder(request_topic, response_topic, [None], log) as responder:
        device_manager = await device_manager_factory(TEST_USER_PARAMS)
        devices = await device_manager.get_devices()
        assert len(devices) == 1
        device = devices[0]
        assert device.duid == "device-id-def456"
        assert device.name == "Roborock Q10 S5+"
        assert device.is_connected
        assert not device.is_local_connected  # Q10 does not support local connections

        assert device.b01_q10_properties
        command = device.b01_q10_properties.command
        await command.send(B01_Q10_DP.REQUEST_DPS, params={})
        await responder.wait()

    assert snapshot == log


@pytest.mark.parametrize(
    "home_data",
    [
        (
            {
                **HOME_DATA_RAW,
                "devices": [mock_data.Q7_DEVICE_DATA],
                "products": [mock_data.SC01_PRODUCT_DATA],
            }
        )
    ],
)
async def test_q7_device(
    mock_rest: Any,
    log: CapturedRequestLog,
    device_manager_factory: Callable[[UserParams], Awaitable[DeviceManager]],
    home_data: dict[str, Any],
    snapshot: syrupy.SnapshotAssertion,
) -> None:
    """Test the device manager end to end flow with a B01 Q10 device."""
    response_builder = ResponseBuilder()
    response_builder.version = B01_VERSION
    test_topic = TEST_TOPIC_FORMAT.format(duid="device-id-q7")
    request_topic = TEST_REQUEST_TOPIC_FORMAT.format(duid="device-id-q7")
    mqtt_responses: list[bytes] = [
        response_builder.build_b01_q7_rpc({"status": 2}, msg_id=9090),
        response_builder.build_b01_q7_rpc("ok", msg_id=9093),
    ]
    async with MqttResponder(request_topic, test_topic, mqtt_responses, log) as responder:
        device_manager = await device_manager_factory(TEST_USER_PARAMS)
        devices = await device_manager.get_devices()
        assert len(devices) == 1
        device = devices[0]
        assert device.duid == "device-id-q7"
        assert device.name == "Roborock Q7"
        assert device.is_connected
        assert not device.is_local_connected  # Q7 does not support local connections

        assert device.b01_q7_properties
        props = await device.b01_q7_properties.query_values([RoborockB01Props.STATUS])
        assert props
        assert props.status == WorkStatusMapping.PAUSED
        await device.b01_q7_properties.start_clean()
        await responder.wait()

    assert snapshot == log


@pytest.mark.parametrize(
    "home_data",
    [
        (
            {
                **HOME_DATA_RAW,
                "devices": [mock_data.ZEO_ONE_DEVICE_DATA],
                "products": [mock_data.A102_PRODUCT_DATA],
            }
        )
    ],
)
async def test_a01_device(
    mock_rest: Any,
    log: CapturedRequestLog,
    device_manager_factory: Callable[[UserParams], Awaitable[DeviceManager]],
    home_data: dict[str, Any],
    snapshot: syrupy.SnapshotAssertion,
) -> None:
    """Test the device manager end to end flow with an A01 device."""
    response_builder = ResponseBuilder()
    response_builder.version = A01_VERSION
    test_topic = TEST_TOPIC_FORMAT.format(duid="zeo_duid")
    request_topic = TEST_REQUEST_TOPIC_FORMAT.format(duid="zeo_duid")
    mqtt_responses: list[bytes] = [
        response_builder.build_a01_rpc({"237": 1}),
        response_builder.build_a01_rpc({"203": 6}),
    ]
    async with MqttResponder(request_topic, test_topic, mqtt_responses, log) as responder:
        device_manager = await device_manager_factory(TEST_USER_PARAMS)
        devices = await device_manager.get_devices()
        assert len(devices) == 1
        device = devices[0]
        assert device.duid == "zeo_duid"
        assert device.name == "Zeo One"
        assert device.is_connected
        assert not device.is_local_connected  # Washing Machine does not support local connections

        assert device.zeo
        props: dict[RoborockZeoProtocol, Any] = await device.zeo.query_values([RoborockZeoProtocol.STATE])
        assert props
        assert props[RoborockZeoProtocol.STATE] == ZeoState.spinning.name
        await responder.wait()

    assert snapshot == log
