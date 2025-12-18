import asyncio
import io
import logging
import re
from asyncio import Protocol
from collections.abc import AsyncGenerator, Callable, Generator
from queue import Queue
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aioresponses import aioresponses

from roborock import HomeData, UserData
from roborock.data import DeviceData
from roborock.mqtt.health_manager import HealthManager
from roborock.protocols.v1_protocol import LocalProtocolVersion
from roborock.roborock_message import RoborockMessage
from roborock.version_1_apis.roborock_local_client_v1 import RoborockLocalClientV1
from roborock.version_1_apis.roborock_mqtt_client_v1 import RoborockMqttClientV1
from tests.mock_data import HOME_DATA_RAW, HOME_DATA_SCENES_RAW, TEST_LOCAL_API_HOST, USER_DATA

# Fixtures for the newer APIs in subdirectories
pytest_plugins = [
    "tests.mqtt_fixtures",
]

_LOGGER = logging.getLogger(__name__)


# Used by fixtures to handle incoming requests and prepare responses
RequestHandler = Callable[[bytes], bytes | None]
QUEUE_TIMEOUT = 10

# Fixed timestamp for deterministic tests for asserting on message contents
FAKE_TIMESTAMP = 1755750946.721395


class CapturedRequestLog:
    """Log of requests and responses for snapshot assertions.

    The log captures the raw bytes of each request and response along with
    a label indicating the direction of the message.
    """

    def __init__(self) -> None:
        """Initialize the request log."""
        self.entries: list[tuple[str, bytes]] = []

    def add_log_entry(self, label: str, data: bytes) -> None:
        """Add a request entry."""
        self.entries.append((label, data))

    def __repr__(self):
        """Return a string representation of the log entries.

        This assumes that the client will behave in a request-response manner,
        so each request is followed by a response. If a test uses non-deterministic
        message order, this may not be accurate and the test would need to decode
        the raw messages and remove any ordering assumptions.
        """
        lines = []
        for label, data in self.entries:
            lines.append(label)
            lines.extend(self._hexdump(data))
        return "\n".join(lines)

    def _hexdump(self, data: bytes, bytes_per_line: int = 16) -> list[str]:
        """Print a hexdump of the given bytes object in a tcpdump/hexdump -C style.

        This makes the packets easier to read and compare in test snapshots.

        Args:
            data: The bytes object to print.
            bytes_per_line: The number of bytes to display per line (default is 16).
        """

        # Use '.' for non-printable characters (ASCII < 32 or > 126)
        def to_printable_ascii(byte_val):
            return chr(byte_val) if 32 <= byte_val <= 126 else "."

        offset = 0
        lines = []
        while offset < len(data):
            chunk = data[offset : offset + bytes_per_line]
            # Format the hex values, space-padded to ensure alignment
            hex_values = " ".join(f"{byte:02x}" for byte in chunk)
            # Pad hex string to a fixed width so ASCII column lines up
            # 3 chars per byte ('xx ') for a full line of 16 bytes
            padded_hex = f"{hex_values:<{bytes_per_line * 3}}"
            # Format the ASCII values
            ascii_values = "".join(to_printable_ascii(byte) for byte in chunk)
            lines.append(f"{offset:08x}  {padded_hex} |{ascii_values}|")
            offset += bytes_per_line
        return lines


@pytest.fixture
def deterministic_message_fixtures() -> Generator[None, None, None]:
    """Fixture to use predictable get_next_int and timestamp values for each test.

    This test mocks out the functions used to generate requests that have some
    entropy such as the nonces, timestamps, and request IDs. This makes the
    generated messages deterministic so we can snapshot them in a test.
    """

    # Pick an arbitrary sequence number used for outgoing requests
    next_int = 9090

    def get_next_int(min_value: int, max_value: int) -> int:
        nonlocal next_int
        result = next_int
        next_int += 1
        if next_int > max_value:
            next_int = min_value
        return result

    # Pick an arbitrary timestamp used for the message encryption
    timestamp = FAKE_TIMESTAMP

    def get_timestamp() -> int:
        """Get a monotonically increasing timestamp for testing."""
        nonlocal timestamp
        timestamp += 1
        return int(timestamp)

    # Use predictable seeds for token_bytes
    token_chr = "A"

    def get_token_bytes(n: int) -> bytes:
        nonlocal token_chr
        result = token_chr.encode() * n
        # Cycle to the next character
        token_chr = chr(ord(token_chr) + 1)
        if token_chr > "Z":
            token_chr = "A"
        return result

    with (
        patch("roborock.api.get_next_int", side_effect=get_next_int),
        patch("roborock.devices.local_channel.get_next_int", side_effect=get_next_int),
        patch("roborock.protocols.v1_protocol.get_next_int", side_effect=get_next_int),
        patch("roborock.protocols.v1_protocol.get_timestamp", side_effect=get_timestamp),
        patch("roborock.protocols.v1_protocol.secrets.token_bytes", side_effect=get_token_bytes),
        patch("roborock.version_1_apis.roborock_local_client_v1.get_next_int", side_effect=get_next_int),
        patch("roborock.roborock_message.get_next_int", side_effect=get_next_int),
        patch("roborock.roborock_message.get_timestamp", side_effect=get_timestamp),
    ):
        yield


@pytest.fixture(name="log")
def log_fixture(deterministic_message_fixtures: None) -> CapturedRequestLog:
    """Fixture that creates a captured request log."""
    return CapturedRequestLog()


class FakeSocketHandler:
    """Fake socket used by the test to simulate a connection to the broker.

    The socket handler is used to intercept the socket send and recv calls and
    populate the response buffer with data to be sent back to the client. The
    handle request callback handles the incoming requests and prepares the responses.
    """

    def __init__(self, handle_request: RequestHandler, response_queue: Queue[bytes], log: CapturedRequestLog) -> None:
        self.response_buf = io.BytesIO()
        self.handle_request = handle_request
        self.response_queue = response_queue
        self.log = log

    def pending(self) -> int:
        """Return the number of bytes in the response buffer."""
        return len(self.response_buf.getvalue())

    def handle_socket_recv(self, read_size: int) -> bytes:
        """Intercept a client recv() and populate the buffer."""
        if self.pending() == 0:
            raise BlockingIOError("No response queued")

        self.response_buf.seek(0)
        data = self.response_buf.read(read_size)
        _LOGGER.debug("Response: 0x%s", data.hex())
        # Consume the rest of the data in the buffer
        remaining_data = self.response_buf.read()
        self.response_buf = io.BytesIO(remaining_data)
        return data

    def handle_socket_send(self, client_request: bytes) -> int:
        """Receive an incoming request from the client."""
        _LOGGER.debug("Request: 0x%s", client_request.hex())
        self.log.add_log_entry("[mqtt >]", client_request)
        if (response := self.handle_request(client_request)) is not None:
            # Enqueue a response to be sent back to the client in the buffer.
            # The buffer will be emptied when the client calls recv() on the socket
            _LOGGER.debug("Queued: 0x%s", response.hex())
            self.log.add_log_entry("[mqtt <]", response)
            self.response_buf.write(response)
        return len(client_request)

    def push_response(self) -> None:
        """Push a response to the client."""
        if not self.response_queue.empty():
            response = self.response_queue.get()
            # Enqueue a response to be sent back to the client in the buffer.
            # The buffer will be emptied when the client calls recv() on the socket
            _LOGGER.debug("Queued: 0x%s", response.hex())
            self.response_buf.write(response)


@pytest.fixture(name="received_requests")
def received_requests_fixture() -> Queue[bytes]:
    """Fixture that provides access to the received requests."""
    return Queue()


@pytest.fixture(name="response_queue")
def response_queue_fixture() -> Generator[Queue[bytes], None, None]:
    """Fixture that provides access to the received requests."""
    response_queue: Queue[bytes] = Queue()
    yield response_queue
    assert response_queue.empty(), "Not all fake responses were consumed"


@pytest.fixture(name="request_handler")
def request_handler_fixture(received_requests: Queue[bytes], response_queue: Queue[bytes]) -> RequestHandler:
    """Fixture records incoming requests and replies with responses from the queue."""

    def handle_request(client_request: bytes) -> bytes | None:
        """Handle an incoming request from the client."""
        received_requests.put(client_request)

        # Insert a prepared response into the response buffer
        if not response_queue.empty():
            return response_queue.get()
        return None

    return handle_request


@pytest.fixture(name="fake_socket_handler")
def fake_socket_handler_fixture(
    request_handler: RequestHandler, response_queue: Queue[bytes], log: CapturedRequestLog
) -> FakeSocketHandler:
    """Fixture that creates a fake MQTT broker."""
    return FakeSocketHandler(request_handler, response_queue, log)


@pytest.fixture(name="mock_sock")
def mock_sock_fixture(fake_socket_handler: FakeSocketHandler) -> Mock:
    """Fixture that creates a mock socket connection and wires it to the handler."""
    mock_sock = Mock()
    mock_sock.recv = fake_socket_handler.handle_socket_recv
    mock_sock.send = fake_socket_handler.handle_socket_send
    mock_sock.pending = fake_socket_handler.pending
    return mock_sock


@pytest.fixture(name="mock_create_connection")
def create_connection_fixture(mock_sock: Mock) -> Generator[None, None, None]:
    """Fixture that overrides the MQTT socket creation to wire it up to the mock socket."""
    with patch("paho.mqtt.client.socket.create_connection", return_value=mock_sock):
        yield


@pytest.fixture(name="mock_select")
def select_fixture(mock_sock: Mock, fake_socket_handler: FakeSocketHandler) -> Generator[None, None, None]:
    """Fixture that overrides the MQTT client select calls to make select work on the mock socket.

    This patch select to activate our mock socket when ready with data. Internal mqtt sockets are
    always ready since they are used internally to wake the select loop. Ours is ready if there
    is data in the buffer.
    """

    def is_ready(sock: Any) -> bool:
        return sock is not mock_sock or (fake_socket_handler.pending() > 0)

    def handle_select(rlist: list, wlist: list, *args: Any) -> list:
        return [list(filter(is_ready, rlist)), list(filter(is_ready, wlist))]

    with patch("paho.mqtt.client.select.select", side_effect=handle_select):
        yield


@pytest.fixture(name="mqtt_client")
async def mqtt_client(mock_create_connection: None, mock_select: None) -> AsyncGenerator[RoborockMqttClientV1, None]:
    user_data = UserData.from_dict(USER_DATA)
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(
        device=home_data.devices[0],
        model=home_data.products[0].model,
    )
    client = RoborockMqttClientV1(user_data, device_info, queue_timeout=QUEUE_TIMEOUT)
    try:
        yield client
    finally:
        if not client.is_connected():
            try:
                await client.async_release()
            except Exception:
                pass


@pytest.fixture(name="mock_rest", autouse=True)
def mock_rest() -> aioresponses:
    """Mock all rest endpoints so they won't hit real endpoints"""
    with aioresponses() as mocked:
        # Match the base URL and allow any query params
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/getUrlByEmail.*"),
            status=200,
            payload={
                "code": 200,
                "data": {"country": "US", "countrycode": "1", "url": "https://usiot.roborock.com"},
                "msg": "success",
            },
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/login.*"),
            status=200,
            payload={"code": 200, "data": USER_DATA, "msg": "success"},
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/loginWithCode.*"),
            status=200,
            payload={"code": 200, "data": USER_DATA, "msg": "success"},
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/sendEmailCode.*"),
            status=200,
            payload={"code": 200, "data": None, "msg": "success"},
        )
        mocked.get(
            re.compile(r"https://.*iot\.roborock\.com/api/v1/getHomeDetail.*"),
            status=200,
            payload={
                "code": 200,
                "data": {"deviceListOrder": None, "id": 123456, "name": "My Home", "rrHomeId": 123456, "tuyaHomeId": 0},
                "msg": "success",
            },
        )
        mocked.get(
            re.compile(r"https://api-.*\.roborock\.com/v2/user/homes*"),
            status=200,
            payload={"api": None, "code": 200, "result": HOME_DATA_RAW, "status": "ok", "success": True},
        )
        mocked.post(
            re.compile(r"https://api-.*\.roborock\.com/nc/prepare"),
            status=200,
            payload={
                "api": None,
                "result": {"r": "US", "s": "ffffff", "t": "eOf6d2BBBB"},
                "status": "ok",
                "success": True,
            },
        )

        mocked.get(
            re.compile(r"https://api-.*\.roborock\.com/user/devices/newadd/*"),
            status=200,
            payload={
                "api": "获取新增设备信息",
                "result": {
                    "activeTime": 1737724598,
                    "attribute": None,
                    "cid": None,
                    "createTime": 0,
                    "deviceStatus": None,
                    "duid": "rand_duid",
                    "extra": "{}",
                    "f": False,
                    "featureSet": "0",
                    "fv": "02.16.12",
                    "iconUrl": "",
                    "lat": None,
                    "localKey": "random_lk",
                    "lon": None,
                    "name": "S7",
                    "newFeatureSet": "0000000000002000",
                    "online": True,
                    "productId": "rand_prod_id",
                    "pv": "1.0",
                    "roomId": None,
                    "runtimeEnv": None,
                    "setting": None,
                    "share": False,
                    "shareTime": None,
                    "silentOtaSwitch": False,
                    "sn": "Rand_sn",
                    "timeZoneId": "America/New_York",
                    "tuyaMigrated": False,
                    "tuyaUuid": None,
                },
                "status": "ok",
                "success": True,
            },
        )
        mocked.get(
            re.compile(r"https://api-.*\.roborock\.com/user/scene/device/.*"),
            status=200,
            payload={"api": None, "code": 200, "result": HOME_DATA_SCENES_RAW, "status": "ok", "success": True},
        )
        mocked.post(
            re.compile(r"https://api-.*\.roborock\.com/user/scene/.*/execute"),
            status=200,
            payload={"api": None, "code": 200, "result": None, "status": "ok", "success": True},
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v4/email/code/send.*"),
            status=200,
            payload={"code": 200, "data": None, "msg": "success"},
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v3/key/sign.*"),
            status=200,
            payload={"code": 200, "data": {"k": "mock_k"}, "msg": "success"},
        )
        mocked.post(
            re.compile(r"https://.*iot\.roborock\.com/api/v4/auth/email/login/code.*"),
            status=200,
            payload={"code": 200, "data": USER_DATA, "msg": "success"},
        )
        yield mocked


@pytest.fixture(autouse=True)
def skip_rate_limit():
    """Don't rate limit tests as they aren't actually hitting the api."""
    with (
        patch("roborock.web_api.RoborockApiClient._login_limiter.try_acquire"),
        patch("roborock.web_api.RoborockApiClient._home_data_limiter.try_acquire"),
    ):
        yield


@pytest.fixture(name="mock_create_local_connection")
def create_local_connection_fixture(
    request_handler: RequestHandler, log: CapturedRequestLog
) -> Generator[None, None, None]:
    """Fixture that overrides the transport creation to wire it up to the mock socket."""

    async def create_connection(protocol_factory: Callable[[], Protocol], *args) -> tuple[Any, Any]:
        protocol = protocol_factory()

        def handle_write(data: bytes) -> None:
            _LOGGER.debug("Received: %s", data)
            response = request_handler(data)
            log.add_log_entry("[local >]", data)
            if response is not None:
                _LOGGER.debug("Replying with %s", response)
                log.add_log_entry("[local <]", response)
                loop = asyncio.get_running_loop()
                loop.call_soon(protocol.data_received, response)

        closed = asyncio.Event()

        mock_transport = Mock()
        mock_transport.write = handle_write
        mock_transport.close = closed.set
        mock_transport.is_reading = lambda: not closed.is_set()

        return (mock_transport, "proto")

    with patch("roborock.version_1_apis.roborock_local_client_v1.get_running_loop") as mock_loop:
        mock_loop.return_value.create_connection.side_effect = create_connection
        yield


@pytest.fixture(name="local_client")
async def local_client_fixture(mock_create_local_connection: None) -> AsyncGenerator[RoborockLocalClientV1, None]:
    home_data = HomeData.from_dict(HOME_DATA_RAW)
    device_info = DeviceData(
        device=home_data.devices[0],
        model=home_data.products[0].model,
        host=TEST_LOCAL_API_HOST,
    )
    client = RoborockLocalClientV1(device_info, queue_timeout=QUEUE_TIMEOUT)
    try:
        yield client
    finally:
        if not client.is_connected():
            try:
                await client.async_release()
            except Exception:
                pass


class FakeChannel:
    """A fake channel that handles publish and subscribe calls."""

    def __init__(self):
        """Initialize the fake channel."""
        self.subscribers: list[Callable[[RoborockMessage], None]] = []
        self.published_messages: list[RoborockMessage] = []
        self.response_queue: list[RoborockMessage] = []
        self._is_connected = False
        self.publish_side_effect: Exception | None = None
        self.publish = AsyncMock(side_effect=self._publish)
        self.subscribe = AsyncMock(side_effect=self._subscribe)
        self.connect = AsyncMock(side_effect=self._connect)
        self.close = MagicMock(side_effect=self._close)
        self.protocol_version = LocalProtocolVersion.V1
        self.restart = AsyncMock()
        self.health_manager = HealthManager(self.restart)

    async def _connect(self) -> None:
        self._is_connected = True

    def _close(self) -> None:
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Return true if connected."""
        return self._is_connected

    async def _publish(self, message: RoborockMessage) -> None:
        """Simulate publishing a message and triggering a response."""
        self.published_messages.append(message)
        if self.publish_side_effect:
            raise self.publish_side_effect
        # When a message is published, simulate a response
        if self.response_queue:
            response = self.response_queue.pop(0)
            # Give a chance for the subscriber to be registered
            for subscriber in list(self.subscribers):
                subscriber(response)

    async def _subscribe(self, callback: Callable[[RoborockMessage], None]) -> Callable[[], None]:
        """Simulate subscribing to messages."""
        self.subscribers.append(callback)
        return lambda: self.subscribers.remove(callback)
