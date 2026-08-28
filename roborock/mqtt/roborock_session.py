"""An MQTT session for sending and receiving messages.

See create_mqtt_session for a factory function to create an MQTT session.

This is a thin wrapper around the async MQTT client that handles dispatching messages
from a topic to a callback function, since the async MQTT client does not
support this out of the box. It also handles the authentication process and
receiving messages from the vacuum cleaner.
"""

import asyncio
import datetime
import logging
import ssl
from collections.abc import Callable

from zmqtt import (
    MQTTClientV5,
    MQTTConnectError,
    MQTTError,
    QoS,
    ReconnectConfig,
    Subscription,
    create_client,
)

from roborock.callbacks import CallbackMap
from roborock.diagnostics import Diagnostics, redact_topic_name

from .health_manager import HealthManager
from .session import MqttParams, MqttQos, MqttSession, MqttSessionException, MqttSessionUnauthorized

_LOGGER = logging.getLogger(__name__)

CLIENT_KEEPALIVE = datetime.timedelta(seconds=45)

# Exponential backoff parameters
MIN_BACKOFF_INTERVAL = datetime.timedelta(seconds=10)
MAX_BACKOFF_INTERVAL = datetime.timedelta(hours=6)
BACKOFF_MULTIPLIER = 1.5
_RC_NOT_AUTHORIZED = 0x87


class RoborockMqttSession(MqttSession):
    """An MQTT session for sending and receiving messages.

    You can start a session invoking the start() method which will connect to
    the MQTT broker. A caller may subscribe to a topic, and the session keeps
    track of which callbacks to invoke for each topic.

    zmqtt owns connection recovery, exponential backoff, and restoration of
    active subscriptions. This wrapper owns callback dispatch and the explicit
    administrative restart used by the health manager.
    """

    def __init__(self, params: MqttParams):
        self._params = params
        self._healthy = False
        self._client: MQTTClientV5 | None = None
        self._subscriptions: dict[str, tuple[Subscription, asyncio.Task[None]]] = {}
        self._terminal_failure_handled = False
        self._lifecycle_lock = asyncio.Lock()
        self._listeners: CallbackMap[str, bytes] = CallbackMap(_LOGGER)
        self._diagnostics = params.diagnostics
        self._health_manager = HealthManager(self.restart)
        self._unauthorized_hook = params.unauthorized_hook

    @property
    def connected(self) -> bool:
        """True if the session is connected to the broker."""
        return self._healthy

    @property
    def health_manager(self) -> HealthManager:
        """Return the health manager for the session."""
        return self._health_manager

    async def start(self) -> None:
        """Start the MQTT session.

        The initial attempt is bounded by the session timeout so failures can
        be returned to the caller. After it succeeds, zmqtt retries connection
        loss in the background according to its reconnect configuration.
        """
        self._diagnostics.increment("start_attempt")
        try:
            client = self._create_client()
            with self._diagnostics.timer("connection"):
                async with asyncio.timeout(self._params.timeout):
                    await client.connect()
        except MQTTConnectError as err:
            self._diagnostics.increment(f"start_failure:{err.return_code}")
            if err.return_code == _RC_NOT_AUTHORIZED:
                if self._unauthorized_hook:
                    self._unauthorized_hook()
                raise MqttSessionUnauthorized(f"Authorization error starting MQTT session: {err}") from err
            raise MqttSessionException(f"Error starting MQTT session: {err}") from err
        except (MQTTError, OSError, TimeoutError) as err:
            self._diagnostics.increment("start_failure:unknown")
            raise MqttSessionException(f"Error starting MQTT session: {err}") from err
        except Exception as err:
            self._diagnostics.increment("start_failure:uncaught")
            raise MqttSessionException(f"Unexpected error starting session: {err}") from err
        else:
            self._client = client
            self._healthy = True
            self._terminal_failure_handled = False
            self._diagnostics.increment("start_success")
            _LOGGER.debug("MQTT session started successfully")

    async def close(self) -> None:
        """Stop subscriptions and shut down the client library."""
        self._diagnostics.increment("close")
        self._healthy = False
        async with self._lifecycle_lock:
            client = self._client
            if client is None:
                return
            try:
                close_task = asyncio.create_task(self._close_client(client))
                await self._wait_for_lifecycle_task(close_task, "close")
            finally:
                self._client = None

    async def _close_client(self, client: MQTTClientV5) -> None:
        """Stop subscriptions before disconnecting the client."""
        try:
            # zmqtt must finish UNSUBSCRIBE before its run task is cancelled.
            await self._stop_subscriptions()
        finally:
            await client.disconnect()

    async def restart(self) -> None:
        """Force the session to disconnect and reconnect.

        This explicit health-manager operation is separate from unexpected
        connection loss, which zmqtt recovers automatically.

        Once the restart begins, cancellation is deferred until the client and
        its subscriptions reach a consistent state.
        """
        _LOGGER.info("Forcing MQTT session restart")
        self._diagnostics.increment("restart")
        async with self._lifecycle_lock:
            client = self._client
            if client is None:
                _LOGGER.debug("No MQTT client to restart")
                return

            restart_task = asyncio.create_task(self._restart_client(client))
            await self._wait_for_lifecycle_task(restart_task, "restart")

    @staticmethod
    async def _wait_for_lifecycle_task(task: asyncio.Task[None], operation: str) -> None:
        """Defer caller cancellation until an MQTT lifecycle operation finishes."""
        cancellation: asyncio.CancelledError | None = None
        while not task.done():
            try:
                await asyncio.wait((task,))
            except asyncio.CancelledError as err:
                cancellation = err

        if cancellation is not None:
            try:
                task.result()
            except asyncio.CancelledError:
                pass
            except Exception as err:
                _LOGGER.warning("MQTT %s failed while handling cancellation: %s", operation, err)
            raise cancellation
        task.result()

    async def _restart_client(self, client: MQTTClientV5) -> None:
        """Restart a client without exposing partially updated subscription state."""
        self._healthy = False
        topics = list(self._subscriptions)
        topics.extend(topic for topic in self._listeners.keys() if topic not in self._subscriptions)
        try:
            await self._stop_subscriptions()
            await client.disconnect()
            async with asyncio.timeout(self._params.timeout):
                await client.connect()
            for topic in topics:
                self._diagnostics.increment("resubscribe")
                _LOGGER.debug("Re-establishing subscription to topic %s", redact_topic_name(topic))
                await self._start_subscription(topic, client)
        except (MQTTError, OSError, TimeoutError) as err:
            await self._stop_subscriptions()
            await client.disconnect()
            raise MqttSessionException(f"Error restarting MQTT session: {err}") from err
        self._healthy = True
        self._terminal_failure_handled = False

    def _create_client(self) -> MQTTClientV5:
        """Create a zmqtt client configured to own connection recovery."""
        params = self._params
        _LOGGER.debug("Connecting to %s:%s for %s", params.host, params.port, params.username)
        tls: ssl.SSLContext | bool = params.tls
        if params.tls and not params.verify_tls:
            tls = ssl.create_default_context()
            tls.check_hostname = False
            tls.verify_mode = ssl.CERT_NONE

        return create_client(
            params.host,
            port=params.port,
            username=params.username,
            password=params.password,
            keepalive=int(CLIENT_KEEPALIVE.total_seconds()),
            version="5.0",
            tls=tls,
            reconnect=ReconnectConfig(
                enabled=True,
                initial_delay=MIN_BACKOFF_INTERVAL.total_seconds(),
                max_delay=MAX_BACKOFF_INTERVAL.total_seconds(),
                backoff_factor=BACKOFF_MULTIPLIER,
                max_attempts=None,
            ),
            on_connection_recovery_failed=self._connection_recovery_failed,
            mqtt_connect_timeout=params.timeout,
        )

    async def _connection_recovery_failed(self) -> None:
        """Mark the session unhealthy after zmqtt exhausts recovery."""
        self._healthy = False
        self._diagnostics.increment("connection_recovery_failed")
        _LOGGER.error("MQTT connection recovery failed")

    async def _start_subscription(self, topic: str, client: MQTTClientV5) -> None:
        """Start a zmqtt subscription and its message consumer."""
        subscription = client.subscribe(topic)
        try:
            async with asyncio.timeout(self._params.timeout):
                await subscription.start()
        except BaseException:
            try:
                async with asyncio.timeout(self._params.timeout):
                    await subscription.stop()
            except Exception as err:
                _LOGGER.warning("Error cleaning up subscription to topic %s: %s", redact_topic_name(topic), err)
            raise
        consumer = asyncio.create_task(self._consume_messages(topic, subscription))
        self._subscriptions[topic] = (subscription, consumer)

    async def _consume_messages(self, topic: str, subscription: Subscription) -> None:
        """Dispatch messages from a zmqtt subscription to topic listeners."""
        try:
            async for message in subscription:
                _LOGGER.debug(
                    "Received MQTT message on topic %s (%d bytes)",
                    redact_topic_name(topic),
                    len(message.payload),
                )
                with self._diagnostics.timer("dispatch_message"):
                    self._listeners(topic, message.payload)
        except asyncio.CancelledError:
            raise
        except Exception as err:
            self._handle_terminal_failure(err)

    def _handle_terminal_failure(self, err: BaseException) -> None:
        """Handle the shared zmqtt terminal failure exactly once."""
        if self._terminal_failure_handled:
            return
        self._terminal_failure_handled = True
        self._healthy = False
        if isinstance(err, MQTTConnectError):
            self._diagnostics.increment(f"connect_failure:{err.return_code}")
            if err.return_code == _RC_NOT_AUTHORIZED and self._unauthorized_hook:
                self._unauthorized_hook()
            _LOGGER.error("MQTT connection recovery failed: %s", err)
        elif isinstance(err, (MQTTError, OSError, TimeoutError)):
            self._diagnostics.increment("connect_failure:unknown")
            _LOGGER.error("MQTT connection recovery failed: %s", err)
        else:
            self._diagnostics.increment("connect_failure:uncaught")
            _LOGGER.exception("Uncaught error consuming MQTT messages: %s", err, exc_info=err)

    async def _stop_subscription(self, topic: str) -> None:
        """Stop a subscription before cancelling its consumer task."""
        active = self._subscriptions.pop(topic, None)
        if active is None:
            return
        subscription, consumer = active
        try:
            async with asyncio.timeout(self._params.timeout):
                await subscription.stop()
        finally:
            consumer.cancel()
            await asyncio.gather(consumer, return_exceptions=True)

    async def _stop_subscriptions(self) -> None:
        """Stop all active subscriptions for the current connection."""
        for topic in list(self._subscriptions):
            try:
                await self._stop_subscription(topic)
            except Exception as err:
                _LOGGER.warning("Error stopping subscription to topic %s: %s", redact_topic_name(topic), err)

    async def subscribe(self, topic: str, callback: Callable[[bytes], None]) -> Callable[[], None]:
        """Subscribe to messages on the specified topic and invoke the callback for new messages.

        The callback will be called with the message payload as a bytes object. The callback
        should not block since it runs in the async loop. It should not raise any exceptions.

        The returned callable stops invoking this callback. The broker subscription
        is shared by all callbacks for the topic and remains active until the session
        closes, avoiding repeated SUBSCRIBE/UNSUBSCRIBE traffic between RPCs.
        """
        _LOGGER.debug("Subscribing to topic %s", redact_topic_name(topic))

        async with self._lifecycle_lock:
            unsub = self._listeners.add_callback(topic, callback)
            if topic not in self._subscriptions:
                if self._client is None:
                    unsub()
                    raise MqttSessionException("Could not subscribe to topic, MQTT client not connected")
                _LOGGER.debug("Establishing subscription to topic %s", redact_topic_name(topic))
                try:
                    with self._diagnostics.timer("subscribe"):
                        await self._start_subscription(topic, self._client)
                except BaseException as err:
                    unsub()
                    if isinstance(err, (MQTTError, OSError, TimeoutError)):
                        raise MqttSessionException(f"Error subscribing to topic: {err}") from err
                    raise

        def unsubscribe() -> None:
            self._diagnostics.increment("unsubscribe")
            unsub()

        return unsubscribe

    async def publish(self, topic: str, message: bytes, qos: MqttQos = MqttQos.AT_MOST_ONCE) -> None:
        """Publish a message on the topic.

        Args:
            topic: The MQTT topic to publish to.
            message: The message payload.
            qos: The MQTT QoS level. Defaults to AT_MOST_ONCE.
        """
        _LOGGER.debug("Sending MQTT message to topic %s (%d bytes)", redact_topic_name(topic), len(message))
        client = self._client
        if client is None:
            raise MqttSessionException("Could not publish message, MQTT client not connected")
        try:
            with self._diagnostics.timer("publish"):
                async with asyncio.timeout(self._params.timeout):
                    await client.publish(topic, message, qos=QoS(qos))
        except (MQTTError, OSError, TimeoutError) as err:
            raise MqttSessionException(f"Error publishing message: {err}") from err


class LazyMqttSession(MqttSession):
    """An MQTT session that is started on first attempt to subscribe.

    This is a wrapper around an existing MqttSession that will only start
    the underlying session when the first attempt to subscribe or publish
    is made.
    """

    def __init__(self, session: RoborockMqttSession, diagnostics: Diagnostics) -> None:
        """Initialize the lazy session with an existing session."""
        self._lock = asyncio.Lock()
        self._started = False
        self._session = session
        self._diagnostics = diagnostics

    @property
    def connected(self) -> bool:
        """True if the session is connected to the broker."""
        return self._session.connected

    @property
    def health_manager(self) -> HealthManager:
        """Return the health manager for the session."""
        return self._session.health_manager

    async def _maybe_start(self) -> None:
        """Start the MQTT session if not already started."""
        async with self._lock:
            if not self._started:
                self._diagnostics.increment("start")
                await self._session.start()
                self._started = True

    async def subscribe(self, device_id: str, callback: Callable[[bytes], None]) -> Callable[[], None]:
        """Invoke the callback when messages are received on the topic.

        The returned callable stops invoking this callback.
        """
        await self._maybe_start()
        return await self._session.subscribe(device_id, callback)

    async def publish(self, topic: str, message: bytes, qos: MqttQos = MqttQos.AT_MOST_ONCE) -> None:
        """Publish a message on the specified topic.

        This will raise an exception if the message could not be sent.
        """
        await self._maybe_start()
        return await self._session.publish(topic, message, qos=qos)

    async def close(self) -> None:
        """Close the underlying MQTT session.

        This will close the underlying session and will not allow it to be
        restarted again.
        """
        await self._session.close()

    async def restart(self) -> None:
        """Force the session to disconnect and reconnect."""
        await self._session.restart()


async def create_mqtt_session(params: MqttParams) -> MqttSession:
    """Create an MQTT session.

    This function is a factory for creating an MQTT session. This will
    raise an exception if initial attempt to connect fails. Once connected,
    the session will retry connecting on failure in the background.
    """
    session = RoborockMqttSession(params)
    await session.start()
    return session


async def create_lazy_mqtt_session(params: MqttParams) -> MqttSession:
    """Create a lazy MQTT session.

    This function is a factory for creating an MQTT session that will
    only connect when the first attempt to subscribe or publish is made.
    """
    return LazyMqttSession(RoborockMqttSession(params), diagnostics=params.diagnostics.subkey("lazy_mqtt"))
