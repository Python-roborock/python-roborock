from typing import Any, Self

from roborock.data import HomeDataProduct, ModelStatus, RoborockErrorCode, RoborockStateCode, S7MaxVStatus, Status
from roborock.devices.traits.v1 import common
from roborock.roborock_message import RoborockDataProtocol
from roborock.roborock_typing import RoborockCommand


class StatusTrait(Status, common.V1TraitMixin):
    """Trait for managing the status of Roborock devices."""

    command = RoborockCommand.GET_STATUS

    def __init__(self, product_info: HomeDataProduct) -> None:
        """Initialize the StatusTrait."""
        self._product_info = product_info

    def _parse_response(self, response: common.V1ResponseData) -> Self:
        """Parse the response from the device into a CleanSummary."""
        status_type: type[Status] = ModelStatus.get(self._product_info.model, S7MaxVStatus)
        if isinstance(response, list):
            response = response[0]
        if isinstance(response, dict):
            return status_type.from_dict(response)
        raise ValueError(f"Unexpected status format: {response!r}")

    def handle_protocol_update(self, protocol: RoborockDataProtocol, data_point: Any) -> bool:
        """Handle a protocol update for a specific data protocol."""
        match protocol:
            case RoborockDataProtocol.ERROR_CODE:
                self.error_code = RoborockErrorCode(data_point)
            case RoborockDataProtocol.STATE:
                self.state = RoborockStateCode(data_point)
            case RoborockDataProtocol.BATTERY:
                self.battery = data_point
            case RoborockDataProtocol.CHARGE_STATUS:
                self.charge_status = data_point
            case _:
                # There is also fan power and water box mode, but for now those are skipped
                return False
        return True
