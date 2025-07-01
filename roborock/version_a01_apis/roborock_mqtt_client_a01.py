import asyncio
import json
import logging
import typing

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from roborock.cloud_api import RoborockMqttClient
from roborock.containers import DeviceData, RoborockCategory, UserData
from roborock.exceptions import RoborockException
from roborock.roborock_message import (
    RoborockDyadDataProtocol,
    RoborockMessage,
    RoborockMessageProtocol,
    RoborockZeoProtocol,
)

from ..util import RoborockLoggerAdapter
from .roborock_client_a01 import RoborockClientA01

_LOGGER = logging.getLogger(__name__)


class RoborockMqttClientA01(RoborockMqttClient, RoborockClientA01):
    """Roborock mqtt client for A01 devices."""

    def __init__(
        self, user_data: UserData, device_info: DeviceData, category: RoborockCategory, queue_timeout: int = 10
    ) -> None:
        """Initialize the Roborock mqtt client."""
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("Got no rriot data from user_data")

        RoborockMqttClient.__init__(self, user_data, device_info)
        RoborockClientA01.__init__(self, device_info, category)
        self.queue_timeout = queue_timeout
        self._logger = RoborockLoggerAdapter(device_info.device.name, _LOGGER)

    async def send_message(self, roborock_message: RoborockMessage):
        await self.validate_connection()
        response_protocol = RoborockMessageProtocol.RPC_RESPONSE

        m = self._encoder(roborock_message)
        # self._logger.debug(f"id={request_id} Requesting method {method} with {params}")
        payload = json.loads(unpad(roborock_message.payload, AES.block_size))
        futures = []
        if "10000" in payload["dps"]:
            for dps in json.loads(payload["dps"]["10000"]):
                futures.append(self._async_response(dps, response_protocol))
        self._send_msg_raw(m)
        responses = await asyncio.gather(*futures, return_exceptions=True)
        dps_responses: dict[int, typing.Any] = {}
        if "10000" in payload["dps"]:
            for i, dps in enumerate(json.loads(payload["dps"]["10000"])):
                response = responses[i]
                if isinstance(response, BaseException):
                    self._logger.warning("Timed out get req for %s after %s s", dps, self.queue_timeout)
                    dps_responses[dps] = None
                else:
                    dps_responses[dps] = response
        return dps_responses

    async def update_values(
        self, dyad_data_protocols: list[RoborockDyadDataProtocol | RoborockZeoProtocol]
    ) -> dict[RoborockDyadDataProtocol | RoborockZeoProtocol, typing.Any]:
        payload = {"dps": {RoborockDyadDataProtocol.ID_QUERY: str([int(protocol) for protocol in dyad_data_protocols])}}
        return await self.send_message(
            RoborockMessage(
                protocol=RoborockMessageProtocol.RPC_REQUEST,
                version=b"A01",
                payload=pad(json.dumps(payload).encode("utf-8"), AES.block_size),
            )
        )

    async def set_value(
        self, protocol: RoborockDyadDataProtocol | RoborockZeoProtocol, value: typing.Any
    ) -> dict[int, typing.Any]:
        """Set a value for a specific protocol on the A01 device."""
        payload = {"dps": {int(protocol): value}}
        return await self.send_message(
            RoborockMessage(
                protocol=RoborockMessageProtocol.RPC_REQUEST,
                version=b"A01",
                payload=pad(json.dumps(payload).encode("utf-8"), AES.block_size),
            )
        )
