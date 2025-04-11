from __future__ import annotations

import asyncio
import dataclasses
import logging
from collections.abc import Coroutine
from typing import Callable, Self
from urllib.parse import urlparse

import aiomqtt
from aiomqtt import TLSParameters

from roborock import RoborockException, UserData
from roborock.protocol import MessageParser, md5hex

from .containers import DeviceData

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class ClientWrapper:
    publish_function: Coroutine[None]
    unsubscribe_function: Coroutine[None]
    subscribe_function: Coroutine[None]


class RoborockMqttManager:
    client_wrappers: dict[str, ClientWrapper] = {}
    _instance: Self = None

    def __new__(cls) -> RoborockMqttManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self, user_data: UserData):
        # Add some kind of lock so we don't try to connect if we are already trying to connect the same account.
        if user_data.rriot.u not in self.client_wrappers:
            loop = asyncio.get_event_loop()
            loop.create_task(self._new_connect(user_data))

    async def _new_connect(self, user_data: UserData):
        rriot = user_data.rriot
        mqtt_user = rriot.u
        hashed_user = md5hex(mqtt_user + ":" + rriot.k)[2:10]
        url = urlparse(rriot.r.m)
        if not isinstance(url.hostname, str):
            raise RoborockException("Url parsing returned an invalid hostname")
        mqtt_host = str(url.hostname)
        mqtt_port = url.port

        mqtt_password = rriot.s
        hashed_password = md5hex(mqtt_password + ":" + rriot.k)[16:]
        LOGGER.debug("Connecting to %s for %s", mqtt_host, mqtt_user)

        async with aiomqtt.Client(
            hostname=mqtt_host,
            port=mqtt_port,
            username=hashed_user,
            password=hashed_password,
            keepalive=60,
            tls_params=TLSParameters(),
        ) as client:
            # TODO: Handle logic for when client loses connection
            LOGGER.info("Connected to %s for %s", mqtt_host, mqtt_user)
            callbacks: dict[str, Callable] = {}
            device_map = {}

            async def publish(device: DeviceData, payload: bytes):
                await client.publish(f"rr/m/i/{mqtt_user}/{hashed_user}/{device.device.duid}", payload=payload)

            async def subscribe(device: DeviceData, callback):
                LOGGER.debug(f"Subscribing to rr/m/o/{mqtt_user}/{hashed_user}/{device.device.duid}")
                await client.subscribe(f"rr/m/o/{mqtt_user}/{hashed_user}/{device.device.duid}")
                LOGGER.debug(f"Subscribed to rr/m/o/{mqtt_user}/{hashed_user}/{device.device.duid}")
                callbacks[device.device.duid] = callback
                device_map[device.device.duid] = device
                return

            async def unsubscribe(device: DeviceData):
                await client.unsubscribe(f"rr/m/o/{mqtt_user}/{hashed_user}/{device.device.duid}")

            self.client_wrappers[user_data.rriot.u] = ClientWrapper(
                publish_function=publish, unsubscribe_function=unsubscribe, subscribe_function=subscribe
            )
            async for message in client.messages:
                try:
                    device_id = message.topic.value.split("/")[-1]
                    device = device_map[device_id]
                    message = MessageParser.parse(message.payload, device.device.local_key)
                    for m in message[0]:
                        callbacks[device_id](m)
                except Exception:
                    ...

    async def disconnect(self, user_data: UserData):
        await self.client_wrappers[user_data.rriot.u].disconnect()

    async def subscribe(self, user_data: UserData, device: DeviceData, callback):
        if user_data.rriot.u not in self.client_wrappers:
            await self.connect(user_data)
        # add some kind of lock to make sure we don't subscribe until the connection is successful
        await asyncio.sleep(2)
        await self.client_wrappers[user_data.rriot.u].subscribe_function(device, callback)

    async def unsubscribe(self):
        pass

    async def publish(self, user_data: UserData, device, payload: bytes):
        LOGGER.debug("Publishing topic for %s, Message: %s", device.device.duid, payload)
        if user_data.rriot.u not in self.client_wrappers:
            await self.connect(user_data)
        await self.client_wrappers[user_data.rriot.u].publish_function(device, payload)
