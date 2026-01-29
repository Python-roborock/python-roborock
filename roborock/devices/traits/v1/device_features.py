from dataclasses import Field, fields

from roborock.data import AppInitStatus, HomeDataProduct, RoborockBase
from roborock.data.v1.v1_containers import FieldNameBase
from roborock.device_features import DeviceFeatures
from roborock.devices.cache import DeviceCache
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand


class DeviceFeaturesTrait(DeviceFeatures, common.V1TraitMixin):
    """Trait for managing supported features on Roborock devices."""

    command = RoborockCommand.APP_GET_INIT_STATUS

    def __init__(self, product: HomeDataProduct, device_cache: DeviceCache) -> None:  # pylint: disable=super-init-not-called
        """Initialize DeviceFeaturesTrait."""
        self._product = product
        self._nickname = product.product_nickname
        self._device_cache = device_cache
        # All fields of DeviceFeatures are required. Initialize them to False
        # so we have some known state.
        for field in fields(self):
            setattr(self, field.name, False)

    def is_field_supported(self, cls: type[RoborockBase], field_name: FieldNameBase) -> bool:
        """Determines if the specified field is supported by this device.

        We use dataclass attributes on the field to specify the schema code that is required
        for the field to be supported and it is compared against the list of
        supported schema codes for the device returned in the product information.
        """
        dataclass_field: Field | None = None
        for field in fields(cls):
            if field.name == field_name:
                dataclass_field = field
                break
        if dataclass_field is None:
            raise ValueError(f"Field {field_name} not found in {cls}")

        requires_schema_code = dataclass_field.metadata.get("requires_schema_code", None)
        if requires_schema_code is None:
            # We assume the field is supported
            return True
        # If the field requires a protocol that is not supported, we return False
        return requires_schema_code in self._product.supported_schema_codes

    async def refresh(self) -> None:
        """Refresh the contents of this trait.

        This will use cached device features if available since they do not
        change often and this avoids unnecessary RPC calls. This would only
        ever change with a firmware update, so caching is appropriate.
        """
        cache_data = await self._device_cache.get()
        if cache_data.device_features is not None:
            self._update_trait_values(cache_data.device_features)
            return
        # Save cached device features
        await super().refresh()
        cache_data.device_features = self
        await self._device_cache.set(cache_data)

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
