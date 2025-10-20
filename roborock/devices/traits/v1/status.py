from typing import Self

from roborock.data import HomeDataProduct, ModelStatus, S7MaxVStatus, Status
from roborock.devices.traits.v1 import common
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
