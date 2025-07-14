import logging

from roborock.local_api import RoborockLocalClient

from .. import CommandVacuumError, DeviceData, RoborockCommand, RoborockException
from ..exceptions import VacuumError
from ..protocols.v1_protocol import encode_local_payload
from ..roborock_message import RoborockMessage, RoborockMessageProtocol
from ..util import RoborockLoggerAdapter
from .roborock_client_v1 import CLOUD_REQUIRED, RoborockClientV1

_LOGGER = logging.getLogger(__name__)


class RoborockLocalClientV1(RoborockLocalClient, RoborockClientV1):
    """Roborock local client for v1 devices."""

    def __init__(self, device_data: DeviceData, queue_timeout: int = 4):
        """Initialize the Roborock local client."""
        RoborockLocalClient.__init__(self, device_data)
        RoborockClientV1.__init__(self, device_data, "abc")
        self.queue_timeout = queue_timeout
        self._logger = RoborockLoggerAdapter(device_data.device.name, _LOGGER)

    async def _send_command(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
    ):
        if method in CLOUD_REQUIRED:
            raise RoborockException(f"Method {method} is not supported over local connection")

        roborock_message = encode_local_payload(method, params)
        self._logger.debug("Building message id %s for method %s", roborock_message.get_request_id(), method)
        return await self.send_message(roborock_message)

    async def send_message(self, roborock_message: RoborockMessage):
        await self.validate_connection()
        method = roborock_message.get_method()
        params = roborock_message.get_params()
        request_id: int | None
        if not method or not method.startswith("get"):
            request_id = roborock_message.seq
            response_protocol = request_id + 1
        else:
            request_id = roborock_message.get_request_id()
            response_protocol = RoborockMessageProtocol.GENERAL_REQUEST
        if request_id is None:
            raise RoborockException(f"Failed build message {roborock_message}")
        msg = self._encoder(roborock_message)
        if method:
            self._logger.debug(f"id={request_id} Requesting method {method} with {params}")
        # Send the command to the Roborock device
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
        if roborock_message.protocol == RoborockMessageProtocol.GENERAL_REQUEST:
            self._logger.debug(f"id={request_id} Response from method {roborock_message.get_method()}: {response}")
        if response == "retry":
            retry_id = roborock_message.get_retry_id()
            return self.send_command(
                RoborockCommand.RETRY_REQUEST, {"retry_id": retry_id, "retry_count": 8, "method": method}
            )
        return response
