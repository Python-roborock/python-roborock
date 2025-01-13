from __future__ import annotations

import logging
import threading
import uuid
from abc import ABC
from asyncio import Lock
from typing import Any
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from .api import KEEPALIVE, RoborockClient
from .containers import DeviceData, UserData
from .exceptions import RoborockException, VacuumError
from .protocol import MessageParser, md5hex
from .roborock_future import RoborockFuture

_LOGGER = logging.getLogger(__name__)
CONNECT_REQUEST_ID = 0
DISCONNECT_REQUEST_ID = 1


class _Mqtt(mqtt.Client):
    """Internal MQTT client.

    This is a subclass of the Paho MQTT client that adds some additional functionality
    for error cases where things get stuck.
    """

    _thread: threading.Thread
    _client_id: str

    def __init__(self) -> None:
        """Initialize the MQTT client."""
        super().__init__(protocol=mqtt.MQTTv5)
        self.reset_client_id()

    def reset_client_id(self):
        """Generate a new client id to make a new session when reconnecting."""
        self._client_id = mqtt.base62(uuid.uuid4().int, padding=22)

    def maybe_restart_loop(self) -> None:
        """Ensure that the MQTT loop is running in case it previously exited."""
        if not self._thread or not self._thread.is_alive():
            if self._thread:
                _LOGGER.info("Stopping mqtt loop")
                super().loop_stop()
            _LOGGER.info("Starting mqtt loop")
            super().loop_start()


class RoborockMqttClient(RoborockClient, ABC):
    """Roborock MQTT client base class."""

    def __init__(self, user_data: UserData, device_info: DeviceData, queue_timeout: int = 10) -> None:
        """Initialize the Roborock MQTT client."""
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("Got no rriot data from user_data")
        RoborockClient.__init__(self, device_info, queue_timeout)
        self._mqtt_user = rriot.u
        self._hashed_user = md5hex(self._mqtt_user + ":" + rriot.k)[2:10]
        url = urlparse(rriot.r.m)
        if not isinstance(url.hostname, str):
            raise RoborockException("Url parsing returned an invalid hostname")
        self._mqtt_host = str(url.hostname)
        self._mqtt_port = url.port
        self._mqtt_ssl = url.scheme == "ssl"

        self._mqtt_client = _Mqtt()
        self._mqtt_client.on_connect = self._mqtt_on_connect
        self._mqtt_client.on_message = self._mqtt_on_message
        self._mqtt_client.on_disconnect = self._mqtt_on_disconnect
        if self._mqtt_ssl:
            self._mqtt_client.tls_set()

        self._mqtt_password = rriot.s
        self._hashed_password = md5hex(self._mqtt_password + ":" + rriot.k)[16:]
        self._mqtt_client.username_pw_set(self._hashed_user, self._hashed_password)
        self._waiting_queue: dict[int, RoborockFuture] = {}
        self._mutex = Lock()

    def _mqtt_on_connect(self, *args, **kwargs):
        _, __, ___, rc, ____ = args
        connection_queue = self._waiting_queue.get(CONNECT_REQUEST_ID)
        if rc != mqtt.MQTT_ERR_SUCCESS:
            message = f"Failed to connect ({mqtt.error_string(rc)})"
            self._logger.error(message)
            if connection_queue:
                connection_queue.set_exception(VacuumError(message))
            return
        self._logger.info(f"Connected to mqtt {self._mqtt_host}:{self._mqtt_port}")
        topic = f"rr/m/o/{self._mqtt_user}/{self._hashed_user}/{self.device_info.device.duid}"
        (result, mid) = self._mqtt_client.subscribe(topic)
        if result != 0:
            message = f"Failed to subscribe ({mqtt.error_string(rc)})"
            self._logger.error(message)
            if connection_queue:
                connection_queue.set_exception(VacuumError(message))
            return
        self._logger.info(f"Subscribed to topic {topic}")
        if connection_queue:
            connection_queue.set_result(True)

    def _mqtt_on_message(self, *args, **kwargs):
        client, __, msg = args
        try:
            messages, _ = MessageParser.parse(msg.payload, local_key=self.device_info.device.local_key)
            super().on_message_received(messages)
        except Exception as ex:
            self._logger.exception(ex)

    def _mqtt_on_disconnect(self, *args, **kwargs):
        _, __, rc, ___ = args
        try:
            exc = RoborockException(mqtt.error_string(rc)) if rc != mqtt.MQTT_ERR_SUCCESS else None
            super().on_connection_lost(exc)
            if rc == mqtt.MQTT_ERR_PROTOCOL:
                self._mqtt_client.reset_client_id()
            connection_queue = self._waiting_queue.get(DISCONNECT_REQUEST_ID)
            if connection_queue:
                connection_queue.set_result(True)
        except Exception as ex:
            self._logger.exception(ex)

    def is_connected(self) -> bool:
        """Check if the mqtt client is connected."""
        return self._mqtt_client.is_connected()

    def sync_disconnect(self) -> Any:
        if not self.is_connected():
            return None

        self._logger.info("Disconnecting from mqtt")
        disconnected_future = self._async_response(DISCONNECT_REQUEST_ID)
        rc = self._mqtt_client.disconnect()

        if rc == mqtt.MQTT_ERR_NO_CONN:
            disconnected_future.cancel()
            return None

        if rc != mqtt.MQTT_ERR_SUCCESS:
            disconnected_future.cancel()
            raise RoborockException(f"Failed to disconnect ({mqtt.error_string(rc)})")

        return disconnected_future

    def sync_connect(self) -> Any:
        if self.is_connected():
            self._mqtt_client.maybe_restart_loop()
            return None

        if self._mqtt_port is None or self._mqtt_host is None:
            raise RoborockException("Mqtt information was not entered. Cannot connect.")

        self._logger.debug("Connecting to mqtt")
        connected_future = self._async_response(CONNECT_REQUEST_ID)
        self._mqtt_client.connect(host=self._mqtt_host, port=self._mqtt_port, keepalive=KEEPALIVE)
        self._mqtt_client.maybe_restart_loop()
        return connected_future

    async def async_disconnect(self) -> None:
        async with self._mutex:
            if disconnected_future := self.sync_disconnect():
                try:
                    await disconnected_future
                except VacuumError as err:
                    raise RoborockException(err) from err

    async def async_connect(self) -> None:
        async with self._mutex:
            if connected_future := self.sync_connect():
                try:
                    await connected_future
                except VacuumError as err:
                    raise RoborockException(err) from err

    def _send_msg_raw(self, msg: bytes) -> None:
        info = self._mqtt_client.publish(
            f"rr/m/i/{self._mqtt_user}/{self._hashed_user}/{self.device_info.device.duid}", msg
        )
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RoborockException(f"Failed to publish ({mqtt.error_string(info.rc)})")
