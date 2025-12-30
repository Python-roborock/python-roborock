"""End-to-end tests for MQTT session.

These tests use a fake MQTT broker to verify the session implementation. We
mock out the lower level socket connections to simulate a broker which gets us
close to an "end to end" test without needing an actual MQTT broker server.

These are higher level tests than the similar tests in tests/mqtt/test_roborock_session.py
which use mocks to verify specific behaviors.
"""

import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

import pytest
import syrupy

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.containers import UserData
from roborock.devices.cache import Cache, InMemoryCache
from roborock.devices.device_manager import DeviceManager, UserParams, create_device_manager
from roborock.protocol import MessageParser
from roborock.protocols.v1_protocol import LocalProtocolVersion
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from roborock.web_api import RoborockApiClient
from tests import mock_data, mqtt_packet
from tests.fixtures.logging import CapturedRequestLog
from tests.mock_data import HOME_DATA_RAW, LOCAL_KEY

TEST_USERNAME = "user@example.com"
TEST_CODE = 1234

# The topic used for the user + device. This is determined from the fake Home
# data API response.
TEST_TOPIC = "rr/m/o/user123/19648f94/abc123"
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
TEST_USER_PARAMS = UserParams(
    username=TEST_USERNAME,
    user_data=UserData.from_dict(mock_data.USER_DATA),
    base_url=mock_data.BASE_URL,
)
MQTT_DEFAULT_RESPONSES: list[bytes] = [
    # MQTT connection response
    mqtt_packet.gen_connack(rc=0, flags=2),
    # ACK the request to subscribe to the topic
    mqtt_packet.gen_suback(mid=1),
]


@pytest.fixture(autouse=True)
def auto_mock_mqtt_client(mock_aiomqtt_client: None) -> None:
    """Automatically use the mock mqtt client fixture."""


@pytest.fixture(autouse=True)
def auto_fast_backoff(fast_backoff_fixture: None) -> None:
    """Automatically use the fast backoff fixture."""


@pytest.fixture(autouse=True)
def mqtt_server_fixture(mock_paho_mqtt_create_connection: None, mock_paho_mqtt_select: None) -> None:
    """Fixture to mock the MQTT connection.

    This is here to pull in the mock socket fixtures into all tests used here.
    """


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
        self.version = LocalProtocolVersion.V1

    def build(
        self,
        payload: bytes,
        protocol: RoborockMessageProtocol | None = None,
    ) -> bytes:
        """Build an encoded response message."""
        self.seq_counter += 1
        return MessageParser.build(
            RoborockMessage(
                protocol=protocol if protocol is not None else self.protocol,
                random=TEST_RANDOM,
                seq=self.seq_counter,
                payload=payload,
                version=self.version.value.encode(),
            ),
            local_key=LOCAL_KEY,
            connect_nonce=self.connect_nonce,
            ack_nonce=self.ack_nonce,
        )

    def build_rpc(
        self,
        data: dict[str, Any],
        protocol: RoborockMessageProtocol | None = None,
    ) -> bytes:
        """Build an encoded RPC response message."""
        self.timestamp_counter += 1
        return self.build(
            payload=json.dumps(
                {
                    "t": self.timestamp_counter,
                    "dps": {
                        "102": json.dumps(data),
                    },
                }
            ).encode(),
            protocol=protocol,
        )


async def test_v1_device(
    mock_rest: Any,
    push_mqtt_response: Callable[[bytes], None],
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

    # Prepare MQTT requests
    response_builder = ResponseBuilder()
    mqtt_responses: list[bytes] = [
        *MQTT_DEFAULT_RESPONSES,
        # ACK the GET_NETWORK_INFO call. id is deterministic based on deterministic_message_fixtures
        mqtt_packet.gen_publish(
            TEST_TOPIC, mid=2, payload=response_builder.build_rpc(data={"id": 9090, "result": NETWORK_INFO})
        ),
    ]
    for response in mqtt_responses:
        push_mqtt_response(response)

    # Prepare local device responses. The ids are deterministic based on deterministic_message_fixtures
    response_builder.seq_counter = 0
    local_responses: list[bytes] = [
        # Queue HELLO response
        response_builder.build(protocol=RoborockMessageProtocol.HELLO_RESPONSE, payload=b"ok"),
        # Feature discovery part 1 & 2
        response_builder.build_rpc(data={"id": 9094, "result": [mock_data.APP_GET_INIT_STATUS]}),
        response_builder.build_rpc(data={"id": 9097, "result": [mock_data.STATUS]}),
    ]
    for payload in local_responses:
        local_response_queue.put_nowait(payload)

    # Create the device manager
    user_params = UserParams(
        username=TEST_USERNAME,
        user_data=user_data,
        base_url=await web_api.base_url,
    )
    device_manager = await device_manager_factory(user_params)

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

    mqtt_responses = [
        *MQTT_DEFAULT_RESPONSES,
        # No network info call this time since it should be cached
    ]
    for response in mqtt_responses:
        push_mqtt_response(response)

    # Prepare local device responses.
    response_builder.seq_counter = 0
    local_response_queue.put_nowait(
        response_builder.build(protocol=RoborockMessageProtocol.HELLO_RESPONSE, payload=b"ok")
    )

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

    # In the previous test, the dock information is fetched and has the side effect of
    # populating the status trait. This test gets dock information from the cache so
    # we have to manually refresh status the first time (like other traits).
    assert device.v1_properties
    assert device.v1_properties.status
    assert device.v1_properties.status.state_name is None

    # Exercise a GET_STATUS call. id is deterministic based on deterministic_message_fixtures
    local_response_queue.put_nowait(response_builder.build_rpc(data={"id": 9101, "result": [mock_data.STATUS]}))

    # Verify GET_STATUS response
    await device.v1_properties.status.refresh()
    assert device.v1_properties.status.state_name == "charging"

    assert snapshot == log


async def test_l01_device(
    mock_rest: Any,
    push_mqtt_response: Callable[[bytes], None],
    local_response_queue: asyncio.Queue[bytes],
    local_received_requests: asyncio.Queue[bytes],
    log: CapturedRequestLog,
    snapshot: syrupy.SnapshotAssertion,
    device_manager_factory: Callable[[UserParams], Awaitable[DeviceManager]],
) -> None:
    """Test the device manager end to end flow with a l01 device."""
    # Prepare MQTT requests
    mqtt_response_builder = ResponseBuilder()
    mqtt_responses: list[bytes] = [
        *MQTT_DEFAULT_RESPONSES,
        # ACK the GET_NETWORK_INFO call. id is deterministic based on deterministic_message_fixtures
        mqtt_packet.gen_publish(
            TEST_TOPIC, mid=2, payload=mqtt_response_builder.build_rpc(data={"id": 9090, "result": NETWORK_INFO})
        ),
    ]
    for response in mqtt_responses:
        push_mqtt_response(response)

    # Prepare local device responses. The ids are deterministic based on deterministic_message_fixtures
    local_response_builder = ResponseBuilder()
    local_response_builder.version = LocalProtocolVersion.L01
    local_response_builder.connect_nonce = 9093
    local_responses: list[bytes] = [
        # Initial V01 Hello request will fail and cause a retry with L01
        b"\x00",
        # Queue HELLO response with L01
        local_response_builder.build(protocol=RoborockMessageProtocol.HELLO_RESPONSE, payload=b"ok"),
    ]
    # Feature discovery requests are sent with an ack nonce based on the random sent in HELLO_RESPONSE
    local_response_builder.ack_nonce = TEST_RANDOM
    local_responses.extend(
        [
            local_response_builder.build_rpc(data={"id": 9094, "result": [mock_data.APP_GET_INIT_STATUS]}),
            local_response_builder.build_rpc(data={"id": 9097, "result": [mock_data.STATUS]}),
        ]
    )
    for payload in local_responses:
        local_response_queue.put_nowait(payload)

    # Create the device manager
    device_manager = await device_manager_factory(TEST_USER_PARAMS)

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
    push_mqtt_response: Callable[[bytes], None],
    log: CapturedRequestLog,
    device_manager_factory: Callable[[UserParams], Awaitable[DeviceManager]],
    home_data: dict[str, Any],
    snapshot: syrupy.SnapshotAssertion,
) -> None:
    """Test the device manager end to end flow with a B01 Q10 device."""
    # Prepare MQTT requests
    for response in MQTT_DEFAULT_RESPONSES:
        push_mqtt_response(response)

    # Create the device manager
    device_manager = await device_manager_factory(TEST_USER_PARAMS)

    # The mocked Home Data API returns a single v1 device
    devices = await device_manager.get_devices()
    assert len(devices) == 1
    device = devices[0]
    assert device.duid == "device-id-def456"
    assert device.name == "Roborock Q10 S5+"
    assert device.is_connected
    assert not device.is_local_connected  # Q10 does not support local connections

    # Send a command. We don't block any response, but just use this to verify
    # against the golden byte stream snapshot.
    assert device.b01_q10_properties
    command = device.b01_q10_properties.command
    await command.send(B01_Q10_DP.REQUETDPS, params={})

    # In the future here we can verify receiving requests from the device

    assert snapshot == log
