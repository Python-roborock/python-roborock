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
from collections.abc import Callable
from contextlib import asynccontextmanager

import aiomqtt
from aiomqtt import MqttCodeError, MqttError, TLSParameters

from roborock.callbacks import CallbackMap
from roborock.diagnostics import Diagnostics, redact_topic_name

from .health_manager import HealthManager
from .session import MqttParams, MqttSession, MqttSessionException, MqttSessionUnauthorized

_LOGGER = logging.getLogger(__name__)
_MQTT_LOGGER = logging.getLogger(f"{__name__}.aiomqtt")

CLIENT_KEEPALIVE = datetime.timedelta(seconds=60)
TOPIC_KEEPALIVE = datetime.timedelta(seconds=60)

# Exponential backoff parameters
MIN_BACKOFF_INTERVAL = datetime.timedelta(seconds=10)
MAX_BACKOFF_INTERVAL = datetime.timedelta(hours=6)
BACKOFF_MULTIPLIER = 1.5


class MqttReasonCode:
    """MQTT Reason Codes used by Roborock devices.

    This is a subset of paho.mqtt.reasoncodes.ReasonCode where we would like
    different error handling behavior.
    """

    RC_ERROR_UNAUTHORIZED = 135


class RoborockMqttSession(MqttSession):
    """An MQTT session for sending and receiving messages.

    You can start a session invoking the start() method which will connect to
    the MQTT broker. A caller may subscribe to a topic, and the session keeps
    track of which callbacks to invoke for each topic.

    The client is run as a background task that will run until shutdown. Once
    connected, the client will wait for messages to be received in a loop. If
    the connection is lost, the client will be re-created and reconnected. There
    is backoff to avoid spamming the broker with connection attempts. The client
    will automatically re-establish any subscriptions when the connection is
    re-established.
    """

    def __init__(
        self,
        params: MqttParams,
        topic_idle_timeout: datetime.timedelta = TOPIC_KEEPALIVE,
    ):
        self._params = params
        self._reconnect_task: asyncio.Task[None] | None = None
        self._healthy = False
        self._stop = False
        self._backoff = MIN_BACKOFF_INTERVAL
        self._client: aiomqtt.Client | None = None
        self._client_subscribed_topics: set[str] = set()
        self._client_lock = asyncio.Lock()
        self._listeners: CallbackMap[str, bytes] = CallbackMap(_LOGGER)
        self._connection_task: asyncio.Task[None] | None = None
        self._topic_idle_timeout = topic_idle_timeout
        self._idle_timers: dict[str, asyncio.Task[None]] = {}
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

        This has special behavior for the first connection attempt where any
        failures are raised immediately. This is to allow the caller to
        handle the failure and retry if desired itself. Once connected,
        the session will retry connecting in the background.
        """
        self._diagnostics.increment("start_attempt")
        start_future: asyncio.Future[None] = asyncio.Future()
        loop = asyncio.get_event_loop()
        self._reconnect_task = loop.create_task(self._run_reconnect_loop(start_future))
        try:
            await start_future
        except MqttCodeError as err:
            self._diagnostics.increment(f"start_failure:{err.rc}")
            if err.rc == MqttReasonCode.RC_ERROR_UNAUTHORIZED:
                raise MqttSessionUnauthorized(f"Authorization error starting MQTT session: {err}") from err
            raise MqttSessionException(f"Error starting MQTT session: {err}") from err
        except MqttError as err:
            self._diagnostics.increment("start_failure:unknown")
            raise MqttSessionException(f"Error starting MQTT session: {err}") from err
        except Exception as err:
            self._diagnostics.increment("start_failure:uncaught")
            raise MqttSessionException(f"Unexpected error starting session: {err}") from err
        else:
            self._diagnostics.increment("start_success")
            _LOGGER.debug("MQTT session started successfully")

    async def close(self) -> None:
        """Cancels the MQTT loop and shutdown the client library."""
        self._diagnostics.increment("close")
        self._stop = True
        tasks = [task for task in [self._connection_task, self._reconnect_task, *self._idle_timers.values()] if task]
        self._connection_task = None
        self._reconnect_task = None
        self._idle_timers.clear()

        for task in tasks:
            task.cancel()
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            pass

        self._healthy = False

    async def restart(self) -> None:
        """Force the session to disconnect and reconnect.

        The active connection task will be cancelled and restarted in the background, retried by
        the reconnect loop. This is a no-op if there is no active connection.
        """
        _LOGGER.info("Forcing MQTT session restart")
        self._diagnostics.increment("restart")
        if self._connection_task:
            self._connection_task.cancel()
        else:
            _LOGGER.debug("No message loop task to cancel")

    async def _run_reconnect_loop(self, start_future: asyncio.Future[None] | None) -> None:
        """Run the MQTT loop."""
        _LOGGER.info("Starting MQTT session")
        self._diagnostics.increment("start_loop")
        while True:
            try:
                self._connection_task = asyncio.create_task(self._run_connection(start_future))
                await self._connection_task
            except asyncio.CancelledError:
                _LOGGER.debug("MQTT connection task cancelled")
            except Exception:
                # Exceptions are logged and handled in _run_connection.
                # There is a special case for exceptions on startup where we return
                # immediately. Otherwise, we let the reconnect loop retry with
                # backoff when the reconnect loop is active.
                if start_future and start_future.done() and start_future.exception():
                    return

            self._healthy = False
            start_future = None
            if self._stop:
                _LOGGER.debug("MQTT session closed, stopping retry loop")
                return
            _LOGGER.info("MQTT session disconnected, retrying in %s seconds", self._backoff.total_seconds())
            self._diagnostics.increment("reconnect_wait")
            await asyncio.sleep(self._backoff.total_seconds())
            self._backoff = min(self._backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF_INTERVAL)

    async def _run_connection(self, start_future: asyncio.Future[None] | None) -> None:
        """Connect to the MQTT broker and listen for messages.

        This is the primary connection loop for the MQTT session that is
        long running and processes incoming messages. If the connection
        is lost, this method will exit.
        """
        try:
            with self._diagnostics.timer("connection"):
                async with self._mqtt_client(self._params) as client:
                    self._backoff = MIN_BACKOFF_INTERVAL
                    self._healthy = True
                    _LOGGER.info("MQTT Session connected.")
                    if start_future and not start_future.done():
                        start_future.set_result(None)

                    _LOGGER.debug("Processing MQTT messages")
                    async for message in client.messages:
                        _LOGGER.debug("Received message: %s", message)
                        with self._diagnostics.timer("dispatch_message"):
                            self._listeners(message.topic.value, message.payload)
        except MqttCodeError as err:
            self._diagnostics.increment(f"connect_failure:{err.rc}")
            if start_future and not start_future.done():
                _LOGGER.debug("MQTT error starting session: %s", err)
                start_future.set_exception(err)
            else:
                _LOGGER.debug("MQTT error: %s", err)
            if err.rc == MqttReasonCode.RC_ERROR_UNAUTHORIZED and self._unauthorized_hook:
                _LOGGER.info("MQTT unauthorized/rate-limit error received, setting backoff to maximum")
                self._unauthorized_hook()
                self._backoff = MAX_BACKOFF_INTERVAL
            raise
        except MqttError as err:
            self._diagnostics.increment("connect_failure:unknown")
            if start_future and not start_future.done():
                _LOGGER.info("MQTT error starting session: %s", err)
                start_future.set_exception(err)
            else:
                _LOGGER.info("MQTT error: %s", err)
            raise
        except Exception as err:
            self._diagnostics.increment("connect_failure:uncaught")
            # This error is thrown when the MQTT loop is cancelled
            # and the generator is not stopped.
            if "generator didn't stop" in str(err) or "generator didn't yield" in str(err):
                _LOGGER.debug("MQTT loop was cancelled")
                return
            if start_future and not start_future.done():
                _LOGGER.error("Uncaught error starting MQTT session: %s", err)
                start_future.set_exception(err)
            else:
                _LOGGER.exception("Uncaught error during MQTT session: %s", err)
            raise

    @asynccontextmanager
    async def _mqtt_client(self, params: MqttParams) -> aiomqtt.Client:
        """Connect to the MQTT broker and listen for messages."""
        _LOGGER.debug("Connecting to %s:%s for %s", params.host, params.port, params.username)
        try:
            async with aiomqtt.Client(
                hostname=params.host,
                port=params.port,
                username=params.username,
                password=params.password,
                keepalive=int(CLIENT_KEEPALIVE.total_seconds()),
                protocol=aiomqtt.ProtocolVersion.V5,
                tls_params=TLSParameters() if params.tls else None,
                timeout=params.timeout,
                logger=_MQTT_LOGGER,
            ) as client:
                _LOGGER.debug("Connected to MQTT broker")
                # Re-establish any existing subscriptions
                async with self._client_lock:
                    self._client = client
                    for topic in self._client_subscribed_topics:
                        self._diagnostics.increment("resubscribe")
                        _LOGGER.debug("Re-establishing subscription to topic %s", redact_topic_name(topic))
                        # TODO: If this fails it will break the whole connection. Make
                        # this retry again in the background with backoff.
                        await client.subscribe(topic)

                yield client
        finally:
            async with self._client_lock:
                self._client = None

    async def subscribe(self, topic: str, callback: Callable[[bytes], None]) -> Callable[[], None]:
        """Subscribe to messages on the specified topic and invoke the callback for new messages.

        The callback will be called with the message payload as a bytes object. The callback
        should not block since it runs in the async loop. It should not raise any exceptions.

        The returned callable unsubscribes from the topic when called, but will delay actual
        unsubscription for the idle timeout period. If a new subscription comes in during the
        timeout, the timer is cancelled and the subscription is reused.
        """
        _LOGGER.debug("Subscribing to topic %s", redact_topic_name(topic))

        # If there is an idle timer for this topic, cancel it (reuse subscription)
        if idle_timer := self._idle_timers.pop(topic, None):
            self._diagnostics.increment("unsubscribe_idle_cancel")
            idle_timer.cancel()
            _LOGGER.debug("Cancelled idle timer for topic %s (reused subscription)", redact_topic_name(topic))

        unsub = self._listeners.add_callback(topic, callback)

        async with self._client_lock:
            if topic not in self._client_subscribed_topics:
                self._client_subscribed_topics.add(topic)
                if self._client:
                    _LOGGER.debug("Establishing subscription to topic %s", topic)
                    try:
                        with self._diagnostics.timer("subscribe"):
                            await self._client.subscribe(topic)
                    except MqttError as err:
                        # Clean up the callback if subscription fails
                        unsub()
                        self._client_subscribed_topics.discard(topic)
                        raise MqttSessionException(f"Error subscribing to topic: {err}") from err
                else:
                    self._diagnostics.increment("subscribe_pending")
                    _LOGGER.debug("Client not connected, will establish subscription later")

        def schedule_unsubscribe() -> None:
            async def idle_unsubscribe():
                try:
                    await asyncio.sleep(self._topic_idle_timeout.total_seconds())
                    # Only unsubscribe if there are no callbacks left for this topic
                    if not self._listeners.get_callbacks(topic):
                        async with self._client_lock:
                            # Check again if we have listeners, in case a subscribe happened
                            # while we were waiting for the lock or after we popped the timer.
                            if self._listeners.get_callbacks(topic):
                                _LOGGER.debug("Skipping unsubscribe for %s, new listeners added", topic)
                                return

                            self._idle_timers.pop(topic, None)
                            self._client_subscribed_topics.discard(topic)

                            if self._client:
                                _LOGGER.debug("Idle timeout expired, unsubscribing from topic %s", topic)
                                try:
                                    await self._client.unsubscribe(topic)
                                except MqttError as err:
                                    _LOGGER.warning("Error unsubscribing from topic %s: %s", topic, err)
                except asyncio.CancelledError:
                    _LOGGER.debug("Idle unsubscribe for topic %s cancelled", topic)

            # Start the idle timer task
            task = asyncio.create_task(idle_unsubscribe())
            self._idle_timers[topic] = task

        def delayed_unsub():
            self._diagnostics.increment("unsubscribe")
            unsub()  # Remove the callback from CallbackMap
            # If no more callbacks for this topic, start idle timer
            if not self._listeners.get_callbacks(topic):
                self._diagnostics.increment("unsubscribe_idle_start")
                schedule_unsubscribe()
            else:
                _LOGGER.debug("Unsubscribing topic %s, still have active callbacks", topic)

        return delayed_unsub

    async def publish(self, topic: str, message: bytes) -> None:
        """Publish a message on the topic."""
        _LOGGER.debug("Sending message to topic %s: %s", topic, message)
        client: aiomqtt.Client
        async with self._client_lock:
            if self._client is None:
                raise MqttSessionException("Could not publish message, MQTT client not connected")
            client = self._client
        try:
            with self._diagnostics.timer("publish"):
                await client.publish(topic, message)
        except MqttError as err:
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

        The returned callable unsubscribes from the topic when called.
        """
        await self._maybe_start()
        return await self._session.subscribe(device_id, callback)

    async def publish(self, topic: str, message: bytes) -> None:
        """Publish a message on the specified topic.

        This will raise an exception if the message could not be sent.
        """
        await self._maybe_start()
        return await self._session.publish(topic, message)

    async def close(self) -> None:
        """Cancels the mqtt loop.

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
