"""End-to-end tests for MQTT session.

These tests use a real EMQX broker to verify the session implementation over
TCP, including the actual zmqtt protocol and subscription lifecycle.

These are higher level tests than the similar tests in tests/mqtt/test_roborock_session.py
which use mocks to verify specific behaviors.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
import syrupy

from roborock.mqtt.roborock_session import create_mqtt_session
from roborock.mqtt.session import MqttSession
from roborock.protocol import MessageParser
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.fixtures.logging import CapturedRequestLog
from tests.fixtures.mqtt import TEST_MQTT_PARAMS, Subscriber, create_test_client
from tests.mock_data import LOCAL_KEY


@pytest.fixture(name="session")
async def session_fixture() -> AsyncGenerator[MqttSession, None]:
    """Fixture to create a new connected MQTT session."""
    session = await create_mqtt_session(TEST_MQTT_PARAMS)
    assert session.connected
    try:
        yield session
    finally:
        await session.close()


async def test_session_e2e_receive_message(
    session: MqttSession,
    log: CapturedRequestLog,
    snapshot: syrupy.SnapshotAssertion,
) -> None:
    """Test receiving a real Roborock message through the session."""
    assert session.connected

    # Subscribe to the topic. We'll next publish a message through EMQX.
    subscriber = Subscriber()
    await session.subscribe("topic-1", subscriber.append)

    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=b'{"result":"ok"}',
        seq=123,
    )
    payload = MessageParser.build(msg, local_key=LOCAL_KEY, prefixed=False)

    async with create_test_client() as peer:
        await peer.publish("topic-1", payload)
    log.add_log_entry("[mqtt <]", payload)

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
    session: MqttSession,
    log: CapturedRequestLog,
    snapshot: syrupy.SnapshotAssertion,
) -> None:
    """Test publishing a real Roborock message."""

    # Publish a message to the broker
    msg = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_REQUEST,
        payload=b'{"method":"get_status"}',
        seq=456,
    )
    payload = MessageParser.build(msg, local_key=LOCAL_KEY, prefixed=False)

    async with create_test_client() as peer:
        async with peer.subscribe("topic-1") as subscription:
            await session.publish("topic-1", payload)
            message = await asyncio.wait_for(subscription.get_message(), timeout=1.0)

    assert message.payload == payload
    log.add_log_entry("[mqtt >]", message.payload)

    assert snapshot == log
