"""Test the MQTT session and channel over TCP with a real broker."""

import asyncio
import json
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from zmqtt import MQTTClientV5, QoS, ReconnectConfig, create_client

from roborock.data import UserData
from roborock.devices.transport.mqtt_channel import MqttChannel
from roborock.mqtt.roborock_session import create_lazy_mqtt_session, create_mqtt_session
from roborock.mqtt.session import MqttParams, MqttQos, MqttSession, MqttSessionException
from roborock.protocol import MessageParser
from roborock.roborock_message import RoborockMessage, RoborockMessageProtocol
from tests.mock_data import LOCAL_KEY, USER_DATA

pytestmark = pytest.mark.mqtt_broker


@pytest.fixture(name="mqtt_params")
def mqtt_params_fixture() -> MqttParams:
    """Use the broker exposed by Docker Compose or GitHub Actions."""
    return MqttParams(
        host="127.0.0.1",
        port=1888,
        tls=False,
        username="username",
        password="password",
        timeout=5.0,
    )


@pytest.fixture(name="session")
async def session_fixture(mqtt_params: MqttParams) -> AsyncGenerator[MqttSession, None]:
    """Create and close the production MQTT session."""
    session = await create_mqtt_session(mqtt_params)
    try:
        assert session.connected
        yield session
    finally:
        await session.close()


@pytest.fixture(name="peer")
async def peer_fixture(mqtt_params: MqttParams) -> AsyncGenerator[MQTTClientV5, None]:
    """Represent a device using an independent MQTT client."""
    async with create_client(
        mqtt_params.host,
        mqtt_params.port,
        version="5.0",
        mqtt_connect_timeout=mqtt_params.timeout,
        reconnect=ReconnectConfig(enabled=False),
    ) as peer:
        yield peer


@pytest.fixture(name="topic")
def topic_fixture() -> str:
    """Isolate each test's traffic on the shared broker."""
    return f"roborock-tests/{uuid4().hex}"


async def test_receive_message(session: MqttSession, peer: MQTTClientV5, topic: str) -> None:
    """Deliver an encrypted Roborock response to the session callback."""
    messages: asyncio.Queue[bytes] = asyncio.Queue()
    await session.subscribe(topic, messages.put_nowait)
    response = RoborockMessage(
        protocol=RoborockMessageProtocol.RPC_RESPONSE,
        payload=b'{"result":"ok"}',
        seq=123,
    )
    payload = MessageParser.build(response, local_key=LOCAL_KEY, prefixed=False)

    await peer.publish(topic, payload)
    received = await asyncio.wait_for(messages.get(), timeout=5)

    assert received == payload
    parsed, remaining = MessageParser.parse(received, local_key=LOCAL_KEY)
    assert not remaining
    assert len(parsed) == 1
    assert parsed[0].protocol == response.protocol
    assert parsed[0].seq == response.seq
    assert parsed[0].payload == response.payload


@pytest.mark.parametrize("qos", list(MqttQos))
async def test_publish_message(session: MqttSession, peer: MQTTClientV5, topic: str, qos: MqttQos) -> None:
    """Deliver the full payload and requested QoS to another MQTT client."""
    payload = MessageParser.build(
        RoborockMessage(protocol=RoborockMessageProtocol.RPC_REQUEST, payload=b'{"method":"get_status"}'),
        local_key=LOCAL_KEY,
        prefixed=False,
    )
    async with peer.subscribe(topic, qos=QoS.EXACTLY_ONCE) as subscription:
        await session.publish(topic, payload, qos=qos)
        received = await asyncio.wait_for(subscription.get_message(), timeout=5)

    assert received.topic == topic
    assert received.payload == payload
    assert received.qos == qos


async def test_subscriber_lifecycle(session: MqttSession, peer: MQTTClientV5, topic: str) -> None:
    """Fan out messages, remove callbacks, and reuse an idle subscription."""
    first: asyncio.Queue[bytes] = asyncio.Queue()
    second: asyncio.Queue[bytes] = asyncio.Queue()
    unsub_first = await session.subscribe(topic, first.put_nowait)
    unsub_second = await session.subscribe(topic, second.put_nowait)

    await peer.publish(topic, b"both")
    assert await asyncio.wait_for(first.get(), timeout=5) == b"both"
    assert await asyncio.wait_for(second.get(), timeout=5) == b"both"

    unsub_first()
    await peer.publish(topic, b"second only")
    assert await asyncio.wait_for(second.get(), timeout=5) == b"second only"
    assert first.empty()

    unsub_second()
    await session.subscribe(topic, first.put_nowait)
    await peer.publish(topic, b"first again")
    assert await asyncio.wait_for(first.get(), timeout=5) == b"first again"
    assert first.empty()
    assert second.empty()


async def test_topic_routing(session: MqttSession, peer: MQTTClientV5, topic: str) -> None:
    """Keep messages for different devices separate in a shared session."""
    first: asyncio.Queue[bytes] = asyncio.Queue()
    second: asyncio.Queue[bytes] = asyncio.Queue()
    await session.subscribe(f"{topic}/first", first.put_nowait)
    await session.subscribe(f"{topic}/second", second.put_nowait)

    await peer.publish(f"{topic}/first", b"first")
    await peer.publish(f"{topic}/second", b"second")

    assert await asyncio.wait_for(first.get(), timeout=5) == b"first"
    assert await asyncio.wait_for(second.get(), timeout=5) == b"second"
    assert first.empty()
    assert second.empty()


async def test_restart_restores_subscriptions(session: MqttSession, peer: MQTTClientV5, topic: str) -> None:
    """Restore message delivery after the session reconnects."""
    messages: asyncio.Queue[bytes] = asyncio.Queue()
    await session.subscribe(topic, messages.put_nowait)
    await peer.publish(topic, b"before restart")
    assert await asyncio.wait_for(messages.get(), timeout=5) == b"before restart"

    await session.restart()
    async with asyncio.timeout(20):
        while session.connected:
            await asyncio.sleep(0.01)
        while not session.connected:
            await asyncio.sleep(0.01)

    await peer.publish(topic, b"after restart")
    assert await asyncio.wait_for(messages.get(), timeout=5) == b"after restart"
    async with peer.subscribe(topic) as subscription:
        await session.publish(topic, b"outbound after restart")
        received = await asyncio.wait_for(subscription.get_message(), timeout=5)
        assert received.payload == b"outbound after restart"


async def test_close(session: MqttSession, topic: str) -> None:
    """Close a connected session and reject further publications."""
    await session.close()

    assert not session.connected
    with pytest.raises(MqttSessionException):
        await session.publish(topic, b"closed")


async def test_lazy_session_subscribe(mqtt_params: MqttParams, peer: MQTTClientV5, topic: str) -> None:
    """Connect a lazy session on its first subscription and receive a message."""
    session = await create_lazy_mqtt_session(mqtt_params)
    assert not session.connected

    messages: asyncio.Queue[bytes] = asyncio.Queue()
    await session.subscribe(topic, messages.put_nowait)
    assert session.connected

    await peer.publish(topic, b"inbound")
    assert await asyncio.wait_for(messages.get(), timeout=5) == b"inbound"

    await session.close()
    assert not session.connected


async def test_lazy_session_publish(mqtt_params: MqttParams, peer: MQTTClientV5, topic: str) -> None:
    """Connect a lazy session on its first publication and deliver a message."""
    session = await create_lazy_mqtt_session(mqtt_params)
    assert not session.connected

    async with peer.subscribe(topic) as subscription:
        await session.publish(topic, b"outbound")
        assert session.connected
        received = await asyncio.wait_for(subscription.get_message(), timeout=5)
        assert received.payload == b"outbound"

    await session.close()
    assert not session.connected


async def test_channel_request_response(session: MqttSession, mqtt_params: MqttParams, peer: MQTTClientV5) -> None:
    """Exchange encrypted commands and responses on the device's Roborock topics."""
    user_data = UserData.from_dict(USER_DATA)
    duid = uuid4().hex
    channel = MqttChannel(session, duid, LOCAL_KEY, user_data.rriot, mqtt_params)
    request_topic = f"rr/m/i/{user_data.rriot.u}/{mqtt_params.username}/{duid}"
    response_topic = f"rr/m/o/{user_data.rriot.u}/{mqtt_params.username}/{duid}"
    messages: asyncio.Queue[RoborockMessage] = asyncio.Queue()
    unsub = await channel.subscribe(messages.put_nowait)
    async with peer.subscribe(request_topic) as subscription:
        command = RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_REQUEST,
            payload=json.dumps({"dps": {"101": json.dumps({"id": 123, "method": "get_status"})}}).encode(),
            seq=456,
        )
        await channel.publish(command)
        request = await asyncio.wait_for(subscription.get_message(), timeout=5)
        parsed, remaining = MessageParser.parse(request.payload, local_key=LOCAL_KEY)
        assert request.topic == request_topic
        assert not remaining
        assert len(parsed) == 1
        assert parsed[0].protocol == RoborockMessageProtocol.RPC_REQUEST
        assert parsed[0].seq == 456
        assert parsed[0].payload == command.payload

        response = RoborockMessage(
            protocol=RoborockMessageProtocol.RPC_RESPONSE,
            payload=json.dumps({"dps": {"102": json.dumps({"id": 123, "result": [{"state": 8}]})}}).encode(),
        )
        await peer.publish(response_topic, MessageParser.build(response, local_key=LOCAL_KEY, prefixed=False))
        received = await asyncio.wait_for(messages.get(), timeout=5)
        assert received.protocol == response.protocol
        assert received.payload == response.payload
    unsub()
