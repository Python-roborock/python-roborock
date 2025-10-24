from dataclasses import fields
from typing import Self

from roborock.data import AppInitStatus, RoborockProductNickname
from roborock.device_features import DeviceFeatures
from roborock.devices.cache import Cache
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand


class DeviceFeaturesTrait(DeviceFeatures, common.V1TraitMixin):
    """Trait for managing Do Not Disturb (DND) settings on Roborock devices."""

    command = RoborockCommand.APP_GET_INIT_STATUS

    def __init__(self, product_nickname: RoborockProductNickname, cache: Cache) -> None:
        """Initialize MapContentTrait."""
        self._nickname = product_nickname
        self._cache = cache
        # All fields of DeviceFeatures are required. Initialize them to False
        # so we have some known state.
        for field in fields(self):
            setattr(self, field.name, False)

    async def refresh(self) -> Self:
        """Refresh the contents of this trait.

        This will use cached device features if available since they do not
        change often and this avoids unnecessary RPC calls. This would only
        ever change with a firmware update, so caching is appropriate.
        """
        cache_data = await self._cache.get()
        if cache_data.device_features is not None:
            self._update_trait_values(cache_data.device_features)
            return self
        # Save cached device features
        device_features = await super().refresh()
        cache_data.device_features = device_features
        await self._cache.set(cache_data)
        return device_features

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
