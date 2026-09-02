"""Helpers for tests that use the real EMQX broker."""

import asyncio
import os
from collections.abc import Iterable

from zmqtt import MQTTClientV5, Subscription, create_client

from roborock.mqtt.session import MqttParams
from roborock.roborock_message import RoborockMessage

from .logging import CapturedRequestLog

MQTT_HOST = os.getenv("ROBOROCK_TEST_MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("ROBOROCK_TEST_MQTT_PORT", "1888"))


TEST_MQTT_PARAMS = MqttParams(
    host=MQTT_HOST,
    port=MQTT_PORT,
    tls=False,
    username="username",
    password="password",
    timeout=2.0,
)


def create_test_client() -> MQTTClientV5:
    """Create an MQTT 5 client connected to the test EMQX broker."""
    return create_client(MQTT_HOST, MQTT_PORT, version="5.0", mqtt_connect_timeout=2.0)


class MqttResponder:
    """Act as a device through the real broker for scripted request/response tests."""

    def __init__(
        self,
        request_topic: str,
        response_topic: str,
        responses: Iterable[bytes | None],
        log: CapturedRequestLog | None = None,
    ) -> None:
        self._request_topic = request_topic
        self._response_topic = response_topic
        self._responses = list(responses)
        self._log = log
        self._client = create_test_client()
        self._subscription: Subscription
        self._task: asyncio.Task[None] | None = None
        self.requests: list[bytes] = []

    async def __aenter__(self) -> "MqttResponder":
        await self._client.connect()
        self._subscription = self._client.subscribe(self._request_topic)
        await self._subscription.start()
        self._task = asyncio.create_task(self._respond())
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._subscription.stop()
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        await self._client.disconnect()

    async def _respond(self) -> None:
        for response in self._responses:
            message = await self._subscription.get_message()
            self.requests.append(message.payload)
            if self._log is not None:
                self._log.add_log_entry("[mqtt >]", message.payload)
            if response is not None:
                if self._log is not None:
                    self._log.add_log_entry("[mqtt <]", response)
                await self._client.publish(self._response_topic, response)

    async def wait(self) -> None:
        """Wait until all scripted requests have been handled."""
        if self._task is not None:
            await asyncio.wait_for(asyncio.shield(self._task), timeout=2.0)


class Subscriber:
    """Mock subscriber class.

    We use this to hold on to received messages for verification.
    """

    def __init__(self) -> None:
        self.messages: list[RoborockMessage | bytes] = []
        self._event = asyncio.Event()

    def append(self, message: RoborockMessage | bytes) -> None:
        self.messages.append(message)
        self._event.set()

    async def wait(self) -> None:
        await asyncio.wait_for(self._event.wait(), timeout=1.0)
        self._event.clear()
