from __future__ import annotations

import asyncio
import logging
import threading
from abc import ABC
from asyncio import Lock
from typing import Any

import paho.mqtt.client as mqtt

from .api import KEEPALIVE, RoborockClient
from .containers import DeviceData, UserData
from .exceptions import RoborockException, VacuumError
from .protocol import (
    Decoder,
    Encoder,
    create_mqtt_decoder,
    create_mqtt_encoder,
    create_mqtt_params,
)
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

    def __init__(self) -> None:
        """Initialize the MQTT client."""
        super().__init__(protocol=mqtt.MQTTv5)

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

    def __init__(self, user_data: UserData, device_info: DeviceData) -> None:
        """Initialize the Roborock MQTT client."""
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("Got no rriot data from user_data")
        RoborockClient.__init__(self, device_info)
        mqtt_params = create_mqtt_params(rriot)
        self._mqtt_user = rriot.u
        self._hashed_user = mqtt_params.username
        self._mqtt_host = mqtt_params.host
        self._mqtt_port = mqtt_params.port

        self._mqtt_client = _Mqtt()
        self._mqtt_client.on_connect = self._mqtt_on_connect
        self._mqtt_client.on_message = self._mqtt_on_message
        self._mqtt_client.on_disconnect = self._mqtt_on_disconnect
        if mqtt_params.tls:
            self._mqtt_client.tls_set()

        self._mqtt_client.username_pw_set(mqtt_params.username, mqtt_params.password)
        self._waiting_queue: dict[int, RoborockFuture] = {}
        self._mutex = Lock()
        self._decoder: Decoder = create_mqtt_decoder(device_info.device.local_key)
        self._encoder: Encoder = create_mqtt_encoder(device_info.device.local_key)

    def _mqtt_on_connect(self, *args, **kwargs):
        _, __, ___, rc, ____ = args
        connection_queue = self._waiting_queue.get(CONNECT_REQUEST_ID)
        if rc != mqtt.MQTT_ERR_SUCCESS:
            message = f"Failed to connect ({mqtt.error_string(rc)})"
            self._logger.error(message)
            if connection_queue:
                connection_queue.set_exception(VacuumError(message))
            else:
                self._logger.debug("Failed to notify connect future, not in queue")
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
            messages = self._decoder(msg.payload)
            super().on_message_received(messages)
        except Exception as ex:
            self._logger.exception(ex)

    def _mqtt_on_disconnect(self, *args, **kwargs):
        _, __, rc, ___ = args
        try:
            exc = RoborockException(mqtt.error_string(rc)) if rc != mqtt.MQTT_ERR_SUCCESS else None
            super().on_connection_lost(exc)
            connection_queue = self._waiting_queue.get(DISCONNECT_REQUEST_ID)
            if connection_queue:
                connection_queue.set_result(True)
        except Exception as ex:
            self._logger.exception(ex)

    def is_connected(self) -> bool:
        """Check if the mqtt client is connected."""
        return self._mqtt_client.is_connected()

    def _sync_disconnect(self) -> Any:
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

    def _sync_connect(self) -> Any:
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
            if disconnected_future := self._sync_disconnect():
                # There are no errors set on this future
                await disconnected_future
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._mqtt_client.loop_stop)

    async def async_connect(self) -> None:
        async with self._mutex:
            if connected_future := self._sync_connect():
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
