from roborock import AppInitStatus, RoborockProductNickname
from roborock.device_features import DeviceFeatures
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand


class DeviceFeaturesTrait(DeviceFeatures, common.V1TraitMixin):
    """Trait for managing Do Not Disturb (DND) settings on Roborock devices."""

    command = RoborockCommand.APP_GET_INIT_STATUS

    def __init__(self, product_nickname: RoborockProductNickname) -> None:
        """Initialize MapContentTrait."""
        self._nickname = product_nickname

    def _parse_response(self, response: common.V1ResponseData) -> DeviceFeatures:
        """Parse the response from the device into a MapContentTrait instance."""
        if not isinstance(response, list):
            raise ValueError(f"Unexpected AppInitStatus response format: {type(response)}")
        app_status = AppInitStatus.from_dict(response[0])
        return DeviceFeatures.from_feature_flags(
            new_feature_info=app_status.new_feature_info,
            new_feature_info_str=app_status.new_feature_info_str,
            feature_info=app_status.feature_info,
            product_nickname=self._nickname,
        )
