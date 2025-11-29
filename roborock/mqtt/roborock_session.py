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
from aiomqtt import MqttError, TLSParameters

from roborock.callbacks import CallbackMap

from .session import MqttParams, MqttSession, MqttSessionException

_LOGGER = logging.getLogger(__name__)
_MQTT_LOGGER = logging.getLogger(f"{__name__}.aiomqtt")

KEEPALIVE = 60

# Exponential backoff parameters
MIN_BACKOFF_INTERVAL = datetime.timedelta(seconds=10)
MAX_BACKOFF_INTERVAL = datetime.timedelta(minutes=30)
BACKOFF_MULTIPLIER = 1.5


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

    def __init__(self, params: MqttParams):
        self._params = params
        self._reconnect_task: asyncio.Task[None] | None = None
        self._healthy = False
        self._stop = False
        self._backoff = MIN_BACKOFF_INTERVAL
        self._client: aiomqtt.Client | None = None
        self._client_lock = asyncio.Lock()
        self._listeners: CallbackMap[str, bytes] = CallbackMap(_LOGGER)
        self._connection_task: asyncio.Task[None] | None = None

    @property
    def connected(self) -> bool:
        """True if the session is connected to the broker."""
        return self._healthy

    async def start(self) -> None:
        """Start the MQTT session.

        This has special behavior for the first connection attempt where any
        failures are raised immediately. This is to allow the caller to
        handle the failure and retry if desired itself. Once connected,
        the session will retry connecting in the background.
        """
        start_future: asyncio.Future[None] = asyncio.Future()
        loop = asyncio.get_event_loop()
        self._reconnect_task = loop.create_task(self._run_reconnect_loop(start_future))
        try:
            await start_future
        except MqttError as err:
            raise MqttSessionException(f"Error starting MQTT session: {err}") from err
        except Exception as err:
            raise MqttSessionException(f"Unexpected error starting session: {err}") from err
        else:
            _LOGGER.debug("MQTT session started successfully")

    async def close(self) -> None:
        """Cancels the MQTT loop and shutdown the client library."""
        self._stop = True
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        self._healthy = False

    async def restart(self) -> None:
        """Force the session to disconnect and reconnect.

        The active connection task will be cancelled and restarted in the background, retried by
        the reconnect loop. This is a no-op if there is no active connection.
        """
        _LOGGER.info("Forcing MQTT session restart")
        if self._connection_task:
            self._connection_task.cancel()
        else:
            _LOGGER.debug("No message loop task to cancel")

    async def _run_reconnect_loop(self, start_future: asyncio.Future[None] | None) -> None:
        """Run the MQTT loop."""
        _LOGGER.info("Starting MQTT session")
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
            if self._stop:
                _LOGGER.debug("MQTT session closed, stopping retry loop")
                return
            _LOGGER.info("MQTT session disconnected, retrying in %s seconds", self._backoff.total_seconds())
            await asyncio.sleep(self._backoff.total_seconds())
            self._backoff = min(self._backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF_INTERVAL)

    async def _run_connection(self, start_future: asyncio.Future[None] | None) -> None:
        """Connect to the MQTT broker and listen for messages.

        This is the primary connection loop for the MQTT session that is
        long running and processes incoming messages. If the connection
        is lost, this method will exit.
        """
        try:
            async with self._mqtt_client(self._params) as client:
                self._backoff = MIN_BACKOFF_INTERVAL
                self._healthy = True
                _LOGGER.info("MQTT Session connected.")
                if start_future and not start_future.done():
                    start_future.set_result(None)

                _LOGGER.debug("Processing MQTT messages")
                async for message in client.messages:
                    _LOGGER.debug("Received message: %s", message)
                    self._listeners(message.topic.value, message.payload)
        except MqttError as err:
            if start_future and not start_future.done():
                _LOGGER.info("MQTT error starting session: %s", err)
                start_future.set_exception(err)
            else:
                _LOGGER.info("MQTT error: %s", err)
            raise
        except Exception as err:
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
                keepalive=KEEPALIVE,
                protocol=aiomqtt.ProtocolVersion.V5,
                tls_params=TLSParameters() if params.tls else None,
                timeout=params.timeout,
                logger=_MQTT_LOGGER,
            ) as client:
                _LOGGER.debug("Connected to MQTT broker")
                # Re-establish any existing subscriptions
                async with self._client_lock:
                    self._client = client
                    for topic in self._listeners.keys():
                        _LOGGER.debug("Re-establishing subscription to topic %s", topic)
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

        The returned callable unsubscribes from the topic when called.
        """
        _LOGGER.debug("Subscribing to topic %s", topic)
        unsub = self._listeners.add_callback(topic, callback)

        async with self._client_lock:
            if self._client:
                _LOGGER.debug("Establishing subscription to topic %s", topic)
                try:
                    await self._client.subscribe(topic)
                except MqttError as err:
                    raise MqttSessionException(f"Error subscribing to topic: {err}") from err
            else:
                _LOGGER.debug("Client not connected, will establish subscription later")

        return unsub

    async def publish(self, topic: str, message: bytes) -> None:
        """Publish a message on the topic."""
        _LOGGER.debug("Sending message to topic %s: %s", topic, message)
        client: aiomqtt.Client
        async with self._client_lock:
            if self._client is None:
                raise MqttSessionException("Could not publish message, MQTT client not connected")
            client = self._client
        try:
            await client.publish(topic, message)
        except MqttError as err:
            raise MqttSessionException(f"Error publishing message: {err}") from err


class LazyMqttSession(MqttSession):
    """An MQTT session that is started on first attempt to subscribe.

    This is a wrapper around an existing MqttSession that will only start
    the underlying session when the first attempt to subscribe or publish
    is made.
    """

    def __init__(self, session: RoborockMqttSession) -> None:
        """Initialize the lazy session with an existing session."""
        self._lock = asyncio.Lock()
        self._started = False
        self._session = session

    @property
    def connected(self) -> bool:
        """True if the session is connected to the broker."""
        return self._session.connected

    async def _maybe_start(self) -> None:
        """Start the MQTT session if not already started."""
        async with self._lock:
            if not self._started:
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
    return LazyMqttSession(RoborockMqttSession(params))
