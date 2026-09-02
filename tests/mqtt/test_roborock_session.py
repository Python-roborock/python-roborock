"""Tests for the MQTT session module."""

import asyncio
import copy
import ssl
from collections.abc import AsyncIterator, Awaitable, Callable, Generator
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from zmqtt import MQTTConnectError, MQTTDisconnectedError, QoS, ReconnectConfig

from roborock.diagnostics import Diagnostics
from roborock.mqtt.roborock_session import RoborockMqttSession, create_mqtt_session
from roborock.mqtt.session import MqttQos, MqttSessionException, MqttSessionUnauthorized
from tests.fixtures.mqtt import TEST_MQTT_PARAMS, Subscriber, create_test_client


class MockSubscription:
    """Small public-API stand-in for focused session lifecycle tests."""

    def __init__(self, start_side_effect: BaseException | None = None) -> None:
        self.start = AsyncMock(side_effect=start_side_effect)
        self.stop = AsyncMock()
        self._messages: asyncio.Queue[SimpleNamespace | Exception] = asyncio.Queue()

    def __aiter__(self) -> AsyncIterator[SimpleNamespace]:
        return self

    async def __anext__(self) -> SimpleNamespace:
        item = await self._messages.get()
        if isinstance(item, Exception):
            raise item
        return item

    async def fail(self, error: Exception) -> None:
        """Surface a terminal zmqtt client failure to the consumer."""
        await self._messages.put(error)


class MockMqttClient:
    """Mock the zmqtt public client API without emulating protocol internals."""

    def __init__(self) -> None:
        self.connect = AsyncMock()
        self.disconnect = AsyncMock()
        self.publish = AsyncMock()
        self.subscribe = Mock(side_effect=self._subscribe)
        self.subscription_start_side_effect: BaseException | None = None
        self.subscriptions: list[MockSubscription] = []
        self.recovery_callback: Callable[[], Awaitable[None]] | None = None
        self.reconnect_config: ReconnectConfig | None = None
        self.tls: ssl.SSLContext | bool | None = None

    def _subscribe(self, topic: str) -> MockSubscription:
        del topic
        subscription = MockSubscription(self.subscription_start_side_effect)
        self.subscriptions.append(subscription)
        return subscription


@pytest.fixture(name="mqtt_client_lite")
def mqtt_client_lite_fixture() -> Generator[MockMqttClient, None, None]:
    """Patch only the public zmqtt client factory for error and lifecycle tests."""
    client = MockMqttClient()

    def client_factory(*args, **kwargs) -> MockMqttClient:
        del args
        client.recovery_callback = kwargs["on_connection_recovery_failed"]
        client.reconnect_config = kwargs["reconnect"]
        client.tls = kwargs["tls"]
        return client

    with patch("roborock.mqtt.roborock_session.create_client", side_effect=client_factory):
        yield client


async def test_session() -> None:
    """Receive broker messages and dispatch them only to matching listeners."""
    session = await create_mqtt_session(TEST_MQTT_PARAMS)
    assert session.connected

    subscriber1 = Subscriber()
    unsub1 = await session.subscribe("topic-1", subscriber1.append)
    subscriber2 = Subscriber()
    await session.subscribe("topic-2", subscriber2.append)

    async with create_test_client() as peer:
        await peer.publish("topic-1", b"12345")
        await subscriber1.wait()
        assert subscriber1.messages == [b"12345"]
        assert not subscriber2.messages

        await peer.publish("topic-2", b"67890")
        await subscriber2.wait()
        assert subscriber2.messages == [b"67890"]

        await peer.publish("topic-1", b"ABC")
        await subscriber1.wait()
        assert subscriber1.messages == [b"12345", b"ABC"]

        unsub1()
        await peer.publish("topic-1", b"ignored")
        await asyncio.sleep(0.05)
        assert subscriber1.messages == [b"12345", b"ABC"]

    await session.close()
    assert not session.connected


async def test_session_no_subscribers() -> None:
    """A session can connect and close without subscriptions."""
    session = await create_mqtt_session(TEST_MQTT_PARAMS)
    assert session.connected
    await session.close()
    assert not session.connected


async def test_publish_command() -> None:
    """Publish through the session to a real broker subscription."""
    session = await create_mqtt_session(TEST_MQTT_PARAMS)
    async with create_test_client() as peer:
        async with peer.subscribe("topic-publish") as subscription:
            await session.publish("topic-publish", message=b"payload")
            message = await asyncio.wait_for(subscription.get_message(), timeout=1.0)
            assert message.payload == b"payload"
    await session.close()


async def test_publish_failure(mqtt_client_lite: MockMqttClient) -> None:
    """Translate a zmqtt publish error into the session exception."""
    session = await create_mqtt_session(TEST_MQTT_PARAMS)
    mqtt_client_lite.publish.side_effect = MQTTDisconnectedError("Connection failed")

    with pytest.raises(MqttSessionException, match="Error publishing message"):
        await session.publish("topic-1", message=b"payload")

    await session.close()


async def test_publish_maps_public_qos(mqtt_client_lite: MockMqttClient) -> None:
    """Map the public Roborock QoS enum to zmqtt without changing the API."""
    session = await create_mqtt_session(TEST_MQTT_PARAMS)

    await session.publish("topic-1", message=b"payload", qos=MqttQos.AT_LEAST_ONCE)

    mqtt_client_lite.publish.assert_awaited_once_with("topic-1", b"payload", qos=QoS.AT_LEAST_ONCE)
    await session.close()


async def test_subscribe_failure(mqtt_client_lite: MockMqttClient) -> None:
    """Translate a zmqtt subscription error and clean up the callback."""
    mqtt_client_lite.subscription_start_side_effect = MQTTDisconnectedError("Connection failed")
    session = await create_mqtt_session(TEST_MQTT_PARAMS)
    subscriber = Subscriber()

    with pytest.raises(MqttSessionException, match="Error subscribing to topic"):
        await session.subscribe("topic-1", subscriber.append)

    assert not subscriber.messages
    await session.close()


async def test_cancelled_subscribe_removes_callback(mqtt_client_lite: MockMqttClient) -> None:
    """Roll back callback state when subscription startup is cancelled."""
    mqtt_client_lite.subscription_start_side_effect = asyncio.CancelledError()
    session = await create_mqtt_session(TEST_MQTT_PARAMS)

    with pytest.raises(asyncio.CancelledError):
        await session.subscribe("topic-cancelled", Subscriber().append)

    assert "topic-cancelled" not in session._listeners.keys()  # type: ignore[attr-defined]
    mqtt_client_lite.subscriptions[-1].stop.assert_awaited_once()
    await session.close()


async def test_cancelled_subscribe_waiting_for_lifecycle_lock_does_not_add_callback(
    mqtt_client_lite: MockMqttClient,
) -> None:
    """Do not register a callback before a cancellable lifecycle-lock wait."""
    session = await create_mqtt_session(TEST_MQTT_PARAMS)
    await session._lifecycle_lock.acquire()  # type: ignore[attr-defined]
    subscribe_task = asyncio.create_task(session.subscribe("topic-lock-cancelled", Subscriber().append))
    await asyncio.sleep(0)

    subscribe_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await subscribe_task

    assert "topic-lock-cancelled" not in session._listeners.keys()  # type: ignore[attr-defined]
    session._lifecycle_lock.release()  # type: ignore[attr-defined]
    await session.close()


async def test_restart() -> None:
    """Force a fresh connection and restore active subscriptions."""
    session = await create_mqtt_session(TEST_MQTT_PARAMS)
    subscriber = Subscriber()
    await session.subscribe("topic-restart", subscriber.append)

    async with create_test_client() as peer:
        await peer.publish("topic-restart", b"before")
        await subscriber.wait()

        await session.restart()
        assert session.connected

        await peer.publish("topic-restart", b"after")
        await subscriber.wait()

    assert subscriber.messages == [b"before", b"after"]
    await session.close()


async def test_cancelled_restart_finishes_lifecycle_transition(mqtt_client_lite: MockMqttClient) -> None:
    """Defer restart cancellation until subscriptions are consistent again."""
    session = await create_mqtt_session(TEST_MQTT_PARAMS)
    await session.subscribe("topic-restart-cancelled", Subscriber().append)
    subscription = mqtt_client_lite.subscriptions[-1]
    stop_started = asyncio.Event()
    allow_stop = asyncio.Event()

    async def stop_subscription() -> None:
        stop_started.set()
        await allow_stop.wait()

    subscription.stop.side_effect = stop_subscription
    restart_task = asyncio.create_task(session.restart())
    await stop_started.wait()
    restart_task.cancel()
    await asyncio.sleep(0)
    assert not restart_task.done()
    restart_task.cancel()
    await asyncio.sleep(0)
    assert not restart_task.done()

    allow_stop.set()
    with pytest.raises(asyncio.CancelledError):
        await restart_task

    assert session.connected
    assert "topic-restart-cancelled" in session._subscriptions  # type: ignore[attr-defined]
    await session.close()


async def test_restart_after_failed_restart_restores_callback_topics(mqtt_client_lite: MockMqttClient) -> None:
    """Retain logical callback topics when an intermediate restart fails."""
    session = await create_mqtt_session(TEST_MQTT_PARAMS)
    subscriber = Subscriber()
    await session.subscribe("topic-restart-retry", subscriber.append)
    mqtt_client_lite.connect.side_effect = MQTTDisconnectedError("Connection failed")

    with pytest.raises(MqttSessionException, match="Error restarting MQTT session"):
        await session.restart()

    assert not session._subscriptions  # type: ignore[attr-defined]
    mqtt_client_lite.connect.side_effect = None
    await session.restart()
    restored = mqtt_client_lite.subscriptions[-1]
    await restored._messages.put(SimpleNamespace(payload=b"restored"))
    await subscriber.wait()

    assert subscriber.messages == [b"restored"]
    await session.close()


async def test_restart_restores_retained_subscription() -> None:
    """Restore a session-owned subscription even when it has no callbacks."""
    session = RoborockMqttSession(TEST_MQTT_PARAMS)
    await session.start()
    unsub = await session.subscribe("topic-restart-retained", Subscriber().append)
    previous = session._subscriptions["topic-restart-retained"][0]  # type: ignore[attr-defined]
    unsub()

    await session.restart()
    restored = session._subscriptions["topic-restart-retained"][0]  # type: ignore[attr-defined]
    assert restored is not previous

    subscriber = Subscriber()
    await session.subscribe("topic-restart-retained", subscriber.append)
    async with create_test_client() as peer:
        await peer.publish("topic-restart-retained", b"restored")
        await subscriber.wait()
    assert subscriber.messages == [b"restored"]
    await session.close()


async def test_unsubscribe_keeps_subscription_for_reuse() -> None:
    """Remove a callback without broker subscription churn between RPCs."""
    session = RoborockMqttSession(TEST_MQTT_PARAMS)
    await session.start()
    first = Subscriber()
    unsub = await session.subscribe("topic-reuse", first.append)
    subscription = session._subscriptions["topic-reuse"][0]  # type: ignore[attr-defined]
    unsub()

    async with create_test_client() as peer:
        await peer.publish("topic-reuse", b"ignored")
        await asyncio.sleep(0.05)
        assert not first.messages

        second = Subscriber()
        await session.subscribe("topic-reuse", second.append)
        assert session._subscriptions["topic-reuse"][0] is subscription  # type: ignore[attr-defined]

        await peer.publish("topic-reuse", b"reused")
        await second.wait()
    assert second.messages == [b"reused"]
    await session.close()


async def test_subscription_fans_out_to_active_callbacks() -> None:
    """Use one broker subscription for multiple independently removable callbacks."""
    session = RoborockMqttSession(TEST_MQTT_PARAMS)
    await session.start()
    first = Subscriber()
    second = Subscriber()
    unsub1 = await session.subscribe("topic-fanout", first.append)
    await session.subscribe("topic-fanout", second.append)

    async with create_test_client() as peer:
        await peer.publish("topic-fanout", b"both")
        await first.wait()
        await second.wait()
        assert first.messages == [b"both"]
        assert second.messages == [b"both"]

        unsub1()
        await peer.publish("topic-fanout", b"second-only")
        await second.wait()
        await asyncio.sleep(0)
        assert first.messages == [b"both"]
        assert second.messages == [b"both", b"second-only"]
    await session.close()


async def test_concurrent_subscribe_reuses_subscription() -> None:
    """Serialize concurrent first subscribers without duplicate broker state."""
    session = RoborockMqttSession(TEST_MQTT_PARAMS)
    await session.start()
    first = Subscriber()
    second = Subscriber()

    await asyncio.gather(
        session.subscribe("topic-concurrent", first.append),
        session.subscribe("topic-concurrent", second.append),
    )

    assert list(session._subscriptions) == ["topic-concurrent"]  # type: ignore[attr-defined]
    async with create_test_client() as peer:
        await peer.publish("topic-concurrent", b"both")
        await first.wait()
        await second.wait()
    assert first.messages == [b"both"]
    assert second.messages == [b"both"]
    await session.close()


async def test_close_stops_subscription_before_cancelling_consumer(mqtt_client_lite: MockMqttClient) -> None:
    """Allow zmqtt to complete UNSUBSCRIBE before cancelling the consumer."""
    session = RoborockMqttSession(TEST_MQTT_PARAMS)
    await session.start()
    unsub = await session.subscribe("topic1", Mock())
    unsub()
    subscription = mqtt_client_lite.subscriptions[-1]
    consumer = session._subscriptions["topic1"][1]  # type: ignore[attr-defined]

    async def assert_consumer_running() -> None:
        assert not consumer.done()

    subscription.stop.side_effect = assert_consumer_running
    await session.close()
    subscription.stop.assert_awaited_once()
    assert consumer.cancelled()


async def test_cancelled_close_finishes_all_subscription_cleanup(mqtt_client_lite: MockMqttClient) -> None:
    """Defer close cancellation until every subscription consumer is stopped."""
    session = RoborockMqttSession(TEST_MQTT_PARAMS)
    await session.start()
    await session.subscribe("topic-close-a", Mock())
    await session.subscribe("topic-close-b", Mock())
    consumers = [consumer for _, consumer in session._subscriptions.values()]  # type: ignore[attr-defined]
    stop_started = asyncio.Event()
    allow_stop = asyncio.Event()

    async def stop_first_subscription() -> None:
        stop_started.set()
        await allow_stop.wait()

    mqtt_client_lite.subscriptions[0].stop.side_effect = stop_first_subscription
    close_task = asyncio.create_task(session.close())
    await stop_started.wait()
    close_task.cancel()
    await asyncio.sleep(0)
    assert not close_task.done()

    allow_stop.set()
    with pytest.raises(asyncio.CancelledError):
        await close_task

    assert session._client is None  # type: ignore[attr-defined]
    assert not session._subscriptions  # type: ignore[attr-defined]
    assert all(consumer.cancelled() for consumer in consumers)
    mqtt_client_lite.disconnect.assert_awaited_once()


@pytest.mark.parametrize(
    ("side_effect", "expected_exception", "match"),
    [
        (MQTTDisconnectedError("Connection failed"), MqttSessionException, "Error starting MQTT session"),
        (MQTTConnectError(135), MqttSessionUnauthorized, "Authorization error starting MQTT session"),
        (MQTTConnectError(128), MqttSessionException, "Error starting MQTT session"),
        (ValueError("Unexpected"), MqttSessionException, "Unexpected error starting session"),
    ],
)
async def test_connect_failure(
    mqtt_client_lite: MockMqttClient,
    side_effect: Exception,
    expected_exception: type[Exception],
    match: str,
) -> None:
    """Map initial connection failures to the public session exceptions."""
    mqtt_client_lite.connect.side_effect = side_effect
    with pytest.raises(expected_exception, match=match):
        await create_mqtt_session(TEST_MQTT_PARAMS)


async def test_client_creation_failure_is_mapped() -> None:
    """Map client configuration errors through the public session exception."""
    params = copy.deepcopy(TEST_MQTT_PARAMS)
    params.timeout = 0

    with pytest.raises(MqttSessionException, match="Unexpected error starting session"):
        await create_mqtt_session(params)


async def test_diagnostics_data() -> None:
    """Record connection, subscription, dispatch, and close diagnostics."""
    diagnostics = Diagnostics()
    params = copy.deepcopy(TEST_MQTT_PARAMS)
    params.diagnostics = diagnostics
    session = await create_mqtt_session(params)
    subscriber1 = Subscriber()
    subscriber2 = Subscriber()
    unsub1 = await session.subscribe("diagnostics/1", subscriber1.append)
    await session.subscribe("diagnostics/2", subscriber2.append)

    async with create_test_client() as peer:
        await peer.publish("diagnostics/1", b"one")
        await subscriber1.wait()
        await peer.publish("diagnostics/2", b"two")
        await subscriber2.wait()
        await peer.publish("diagnostics/1", b"three")
        await subscriber1.wait()

    data = diagnostics.as_dict()
    assert data.get("start_attempt") == 1
    assert data.get("start_success") == 1
    assert data.get("subscribe_count") == 2
    assert data.get("dispatch_message_count") == 3

    unsub1()
    await session.close()
    assert diagnostics.as_dict().get("close") == 1


async def test_session_unauthorized_hook(mqtt_client_lite: MockMqttClient) -> None:
    """Invoke the unauthorized hook when the initial connection is rejected."""
    unauthorized = asyncio.Event()
    params = copy.deepcopy(TEST_MQTT_PARAMS)
    params.unauthorized_hook = unauthorized.set
    mqtt_client_lite.connect.side_effect = MQTTConnectError(135)

    with pytest.raises(MqttSessionUnauthorized):
        await create_mqtt_session(params)
    assert unauthorized.is_set()


async def test_session_unauthorized_after_start(mqtt_client_lite: MockMqttClient) -> None:
    """Handle a shared terminal failure once across all subscriptions."""
    unauthorized = Mock()
    params = copy.deepcopy(TEST_MQTT_PARAMS)
    params.diagnostics = Diagnostics()
    params.unauthorized_hook = unauthorized
    session = await create_mqtt_session(params)
    await session.subscribe("topic-1", Subscriber().append)
    await session.subscribe("topic-2", Subscriber().append)
    assert mqtt_client_lite.recovery_callback is not None
    await mqtt_client_lite.recovery_callback()
    await mqtt_client_lite.subscriptions[0].fail(MQTTConnectError(135))
    await mqtt_client_lite.subscriptions[1].fail(MQTTConnectError(135))

    try:
        await asyncio.sleep(0)
        unauthorized.assert_called_once_with()
        assert not session.connected
        assert params.diagnostics.as_dict().get("connect_failure:135") == 1
    finally:
        await session.close()


async def test_zmqtt_owns_connection_recovery(mqtt_client_lite: MockMqttClient) -> None:
    """Delegate reconnect backoff and retries to the zmqtt client."""
    session = await create_mqtt_session(TEST_MQTT_PARAMS)
    assert mqtt_client_lite.reconnect_config == ReconnectConfig(
        enabled=True,
        initial_delay=10.0,
        max_delay=21600.0,
        backoff_factor=1.5,
        max_attempts=None,
    )
    assert mqtt_client_lite.recovery_callback is not None
    await mqtt_client_lite.recovery_callback()

    try:
        assert mqtt_client_lite.connect.await_count == 1
        assert not session.connected
        assert TEST_MQTT_PARAMS.diagnostics.as_dict().get("connection_recovery_failed", 0) >= 1
    finally:
        await session.close()


@pytest.mark.parametrize("verify_tls", [True, False])
async def test_tls_configuration(mqtt_client_lite: MockMqttClient, verify_tls: bool) -> None:
    """Delegate verified TLS defaults to zmqtt and configure opt-out explicitly."""
    params = copy.deepcopy(TEST_MQTT_PARAMS)
    params.tls = True
    params.verify_tls = verify_tls
    session = await create_mqtt_session(params)

    if verify_tls:
        assert mqtt_client_lite.tls is True
    else:
        assert isinstance(mqtt_client_lite.tls, ssl.SSLContext)
        assert not mqtt_client_lite.tls.check_hostname
        assert mqtt_client_lite.tls.verify_mode == ssl.CERT_NONE

    await session.close()
