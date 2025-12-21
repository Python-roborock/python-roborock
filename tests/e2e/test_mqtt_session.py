"""End-to-end tests for MQTT session.

These tests use a fake MQTT broker to verify the session implementation. We
mock out the lower level socket connections to simulate a broker which gets us
close to an "end to end" test without needing an actual MQTT broker server.

These are higher level tests that the similar tests in tests/mqtt/test_roborock_session.py
which use mocks to verify specific behaviors.
"""

from collections.abc import AsyncGenerator, Callable
from queue import Queue

import pytest
import syrupy

from roborock.mqtt.roborock_session import create_mqtt_session
from roborock.mqtt.session import MqttSession
from roborock.protocol import MessageParser
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests import mqtt_packet
from tests.fixtures.mqtt import FAKE_PARAMS, Subscriber
from tests.fixtures.logging import CapturedRequestLog
from tests.mock_data import LOCAL_KEY


@pytest.fixture(autouse=True)
def auto_mock_mqtt_client(mock_aiomqtt_client: None) -> None:
    """Automatically use the mock mqtt client fixture."""


@pytest.fixture(autouse=True)
def auto_fast_backoff(fast_backoff_fixture: None) -> None:
    """Automatically use the fast backoff fixture."""


@pytest.fixture(autouse=True)
def mqtt_server_fixture(mock_paho_mqtt_create_connection: None, mock_paho_mqtt_select: None) -> None:
    """Fixture to mock the MQTT connection.

    This is here to pull in the mock socket pixtures into all tests used here.
    """


@pytest.fixture(name="session")
async def session_fixture(
    push_mqtt_response: Callable[[bytes], None],
) -> AsyncGenerator[MqttSession, None]:
    """Fixture to create a new connected MQTT session."""
    push_mqtt_response(mqtt_packet.gen_connack(rc=0, flags=2))
    session = await create_mqtt_session(FAKE_PARAMS)
    assert session.connected
    try:
        yield session
    finally:
        await session.close()


async def test_session_e2e_receive_message(
    push_mqtt_response: Callable[[bytes], None],
    session: MqttSession,
    log: CapturedRequestLog,
    snapshot: syrupy.SnapshotAssertion,
) -> None:
    """Test receiving a real Roborock message through the session."""
    assert session.connected

    # Subscribe to the topic. We'll next construct and push a message.
    push_mqtt_response(mqtt_packet.gen_suback(mid=1))
    subscriber = Subscriber()
    await session.subscribe("topic-1", subscriber.append)

    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=b'{"result":"ok"}',
        seq=123,
    )
    payload = MessageParser.build(msg, local_key=LOCAL_KEY, prefixed=False)

    # Simulate receiving the message from the broker
    push_mqtt_response(mqtt_packet.gen_publish("topic-1", mid=2, payload=payload))

    # Verify it was dispatched to the subscriber
    await subscriber.wait()
    assert len(subscriber.messages) == 1
    received_payload = subscriber.messages[0]
    assert isinstance(received_payload, bytes)
    assert received_payload == payload

    # Verify the message payload contents
    parsed_msgs, _ = MessageParser.parse(received_payload, local_key=LOCAL_KEY)
    assert len(parsed_msgs) == 1
    parsed_msg = parsed_msgs[0]
    assert parsed_msg.protocol == RoborockMessageProtocol.RPC_RESPONSE
    assert parsed_msg.seq == 123
    # The payload in parsed_msg should be the decrypted bytes
    assert parsed_msg.payload == b'{"result":"ok"}'

    assert snapshot == log


async def test_session_e2e_publish_message(
    push_mqtt_response: Callable[[bytes], None],
    mqtt_received_requests: Queue,
    session: MqttSession,
    log: CapturedRequestLog,
    snapshot: syrupy.SnapshotAssertion,
) -> None:
    """Test publishing a real Roborock message."""

    # Publish a message to the brokwer
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        payload=b'{"method":"get_status"}',
        seq=456,
    )
    payload = MessageParser.build(msg, local_key=LOCAL_KEY, prefixed=False)

    await session.publish("topic-1", payload)

    # Verify what was sent to the broker
    # We expect the payload to be present in the sent bytes
    found = False
    while not mqtt_received_requests.empty():
        request = mqtt_received_requests.get()
        if payload in request:
            found = True
            break

    assert found, "Published payload not found in sent requests"

    assert snapshot == log
