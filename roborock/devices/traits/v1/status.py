from typing import Self

from roborock.containers import HomeDataProduct, Status, get_custom_status
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand


class StatusTrait(Status, common.V1TraitMixin):
    """Trait for managing the status of Roborock devices."""

    command = RoborockCommand.GET_STATUS

    def __init__(self, product_info: HomeDataProduct) -> None:
        """Initialize the StatusTrait."""
        self._product_info = product_info
        self._status_type = get_custom_status(self.device_info.device_features, self.device_info.region)

    def _parse_response(self, response: common.V1ResponseData) -> Self:
        """Parse the response from the device into a CleanSummary."""
        if isinstance(response, list):
            response = response[0]
        if isinstance(response, dict):
            return self._status_type.from_dict(response)
        raise ValueError(f"Unexpected status format: {response!r}")
