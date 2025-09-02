"""Modules for communicating with specific Roborock devices over MQTT."""

import logging
from collections.abc import Callable

from roborock.callbacks import decoder_callback
from roborock.containers import HomeDataDevice, RRiot, UserData
from roborock.exceptions import RoborockException
from roborock.mqtt.session import MqttParams, MqttSession, MqttSessionException
from roborock.protocol import create_mqtt_decoder, create_mqtt_encoder
from roborock.roborock_message import RoborockMessage

from .channel import Channel

_LOGGER = logging.getLogger(__name__)


class MqttChannel(Channel):
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

        self._decoder = create_mqtt_decoder(local_key)
        self._encoder = create_mqtt_encoder(local_key)

    @property
    def is_connected(self) -> bool:
        """Return true if the channel is connected.

        This passes through the underlying MQTT session's connected state.
        """
        return self._mqtt_session.connected

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

        Returns a callable that can be used to unsubscribe from the topic.
        """
        dispatch = decoder_callback(self._decoder, callback, _LOGGER)
        return await self._mqtt_session.subscribe(self._subscribe_topic, dispatch)

    async def publish(self, message: RoborockMessage) -> None:
        """Publish a command message.

        The caller is responsible for handling any responses and associating them
        with the incoming request.
        """
        try:
            encoded_msg = self._encoder(message)
        except Exception as e:
            _LOGGER.exception("Error encoding MQTT message: %s", e)
            raise RoborockException(f"Failed to encode MQTT message: {e}") from e
        try:
            return await self._mqtt_session.publish(self._publish_topic, encoded_msg)
        except MqttSessionException as e:
            _LOGGER.exception("Error publishing MQTT message: %s", e)
            raise RoborockException(f"Failed to publish MQTT message: {e}") from e


def create_mqtt_channel(
    user_data: UserData, mqtt_params: MqttParams, mqtt_session: MqttSession, device: HomeDataDevice
) -> MqttChannel:
    """Create a V1Channel for the given device."""
    return MqttChannel(mqtt_session, device.duid, device.local_key, user_data.rriot, mqtt_params)
