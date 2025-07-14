import base64
import logging

from vacuum_map_parser_base.config.color import ColorsPalette
from vacuum_map_parser_base.config.image_config import ImageConfig
from vacuum_map_parser_base.config.size import Sizes
from vacuum_map_parser_roborock.map_data_parser import RoborockMapDataParser

from roborock.cloud_api import RoborockMqttClient

from ..containers import DeviceData, UserData
from ..exceptions import CommandVacuumError, RoborockException, VacuumError
from ..protocol import Utils
from ..protocols.v1_protocol import SecurityData, create_mqtt_payload_encoder
from ..roborock_message import (
    RoborockMessage,
    RoborockMessageProtocol,
)
from ..roborock_typing import RoborockCommand
from ..util import RoborockLoggerAdapter
from .roborock_client_v1 import COMMANDS_SECURED, CUSTOM_COMMANDS, RoborockClientV1

_LOGGER = logging.getLogger(__name__)


class RoborockMqttClientV1(RoborockMqttClient, RoborockClientV1):
    """Roborock mqtt client for v1 devices."""

    def __init__(self, user_data: UserData, device_info: DeviceData, queue_timeout: int = 10) -> None:
        """Initialize the Roborock mqtt client."""
        rriot = user_data.rriot
        if rriot is None:
            raise RoborockException("Got no rriot data from user_data")
        endpoint = base64.b64encode(Utils.md5(rriot.k.encode())[8:14]).decode()

        RoborockMqttClient.__init__(self, user_data, device_info)
        RoborockClientV1.__init__(self, device_info, endpoint)
        self.queue_timeout = queue_timeout
        self._logger = RoborockLoggerAdapter(device_info.device.name, _LOGGER)
        self._payload_encoder = create_mqtt_payload_encoder(
            SecurityData(endpoint=self._endpoint, nonce=self._nonce),
        )

    async def send_message(self, roborock_message: RoborockMessage):
        await self.validate_connection()
        method = roborock_message.get_method()
        params = roborock_message.get_params()
        request_id = roborock_message.get_request_id()
        if request_id is None:
            raise RoborockException(f"Failed build message {roborock_message}")
        response_protocol = (
            RoborockMessageProtocol.MAP_RESPONSE if method in COMMANDS_SECURED else RoborockMessageProtocol.RPC_RESPONSE
        )
        msg = self._encoder(roborock_message)
        self._logger.debug(f"id={request_id} Requesting method {method} with {params}")
        async_response = self._async_response(request_id, response_protocol)
        self._send_msg_raw(msg)
        diagnostic_key = method if method is not None else "unknown"
        try:
            response = await async_response
        except VacuumError as err:
            self._diagnostic_data[diagnostic_key] = {
                "params": roborock_message.get_params(),
                "error": err,
            }
            raise CommandVacuumError(method, err) from err
        self._diagnostic_data[diagnostic_key] = {
            "params": roborock_message.get_params(),
            "response": response,
        }
        if response_protocol == RoborockMessageProtocol.MAP_RESPONSE:
            self._logger.debug(f"id={request_id} Response from {method}: {len(response)} bytes")
        else:
            self._logger.debug(f"id={request_id} Response from {method}: {response}")
        return response

    async def _send_command(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
    ):
        if method in CUSTOM_COMMANDS:
            # When we have more custom commands do something more complicated here
            return await self._get_calibration_points()

        roborock_message = self._payload_encoder(method, params)
        self._logger.debug("Building message id %s for method %s", roborock_message.get_request_id, method)
        return await self.send_message(roborock_message)

    async def _get_calibration_points(self):
        map: bytes = await self.send_command(RoborockCommand.GET_MAP_V1)
        parser = RoborockMapDataParser(ColorsPalette(), Sizes(), [], ImageConfig(), [])
        parsed_map = parser.parse(map)
        calibration = parsed_map.calibration()
        self._logger.info(parsed_map.calibration())
        return calibration

    async def get_map_v1(self) -> bytes | None:
        return await self.send_command(RoborockCommand.GET_MAP_V1)
