"""Modules for communicating with specific Roborock devices over MQTT."""

import asyncio
import logging
from collections.abc import Callable
from json import JSONDecodeError

from roborock.containers import RRiot
from roborock.exceptions import RoborockException
from roborock.mqtt.session import MqttParams, MqttSession
from roborock.protocol import create_mqtt_decoder, create_mqtt_encoder
from roborock.roborock_message import RoborockMessage

_LOGGER = logging.getLogger(__name__)


class MqttChannel:
    """Simple RPC-style channel for communicating with a device over MQTT.

    Handles request/response correlation and timeouts, but leaves message
    format most parsing to higher-level components.
    """

    def __init__(self, mqtt_session: MqttSession, duid: str, local_key: str, rriot: RRiot, mqtt_params: MqttParams):
        self._mqtt_session = mqtt_session
        self._duid = duid
        self._local_key = local_key
        self._rriot = rriot
        self._mqtt_params = mqtt_params

        # RPC support
        self._waiting_queue: dict[int, asyncio.Future[RoborockMessage]] = {}
        self._decoder = create_mqtt_decoder(local_key)
        self._encoder = create_mqtt_encoder(local_key)
        self._queue_lock = asyncio.Lock()

    @property
    def _publish_topic(self) -> str:
        """Topic to send commands to the device."""
        return f"rr/m/i/{self._rriot.u}/{self._mqtt_params.username}/{self._duid}"

    @property
    def _subscribe_topic(self) -> str:
        """Topic to receive responses from the device."""
        return f"rr/m/o/{self._rriot.u}/{self._mqtt_params.username}/{self._duid}"

    async def subscribe(self, callback: Callable[[RoborockMessage], None]) -> Callable[[], None]:
        """Subscribe to the device's response topic.

        The callback will be called with the message payload when a message is received.

        All messages received will be processed through the provided callback, even
        those sent in response to the `send_command` command.

        Returns a callable that can be used to unsubscribe from the topic.
        """

        def message_handler(payload: bytes) -> None:
            if not (messages := self._decoder(payload)):
                _LOGGER.warning("Failed to decode MQTT message: %s", payload)
                return
            for message in messages:
                _LOGGER.debug("Received message: %s", message)
                asyncio.create_task(self._resolve_future_with_lock(message))
                try:
                    callback(message)
                except Exception as e:
                    _LOGGER.exception("Uncaught error in message handler callback: %s", e)

        return await self._mqtt_session.subscribe(self._subscribe_topic, message_handler)

    async def _resolve_future_with_lock(self, message: RoborockMessage) -> None:
        """Resolve waiting future with proper locking."""
        if (request_id := message.get_request_id()) is None:
            _LOGGER.debug("Received message with no request_id")
            return
        async with self._queue_lock:
            if (future := self._waiting_queue.pop(request_id, None)) is not None:
                future.set_result(message)
            else:
                _LOGGER.debug("Received message with no waiting handler: request_id=%s", request_id)

    async def send_message(self, message: RoborockMessage, timeout: float = 10.0) -> RoborockMessage:
        """Send a command message and wait for the response message.

        Returns the raw response message - caller is responsible for parsing.
        """
        try:
            if (request_id := message.get_request_id()) is None:
                raise RoborockException("Message must have a request_id for RPC calls")
        except (ValueError, JSONDecodeError) as err:
            _LOGGER.exception("Error getting request_id from message: %s", err)
            raise RoborockException(f"Invalid message format, Message must have a request_id: {err}") from err

        future: asyncio.Future[RoborockMessage] = asyncio.Future()
        async with self._queue_lock:
            if request_id in self._waiting_queue:
                raise RoborockException(f"Request ID {request_id} already pending, cannot send command")
            self._waiting_queue[request_id] = future

        try:
            encoded_msg = self._encoder(message)
            await self._mqtt_session.publish(self._publish_topic, encoded_msg)

            return await asyncio.wait_for(future, timeout=timeout)

        except asyncio.TimeoutError as ex:
            async with self._queue_lock:
                self._waiting_queue.pop(request_id, None)
            raise RoborockException(f"Command timed out after {timeout}s") from ex
        except Exception:
            logging.exception("Uncaught error sending command")
            async with self._queue_lock:
                self._waiting_queue.pop(request_id, None)
            raise
