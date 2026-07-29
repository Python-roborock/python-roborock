from dataclasses import fields
from typing import Any

from roborock.data import AppInitStatus, HomeDataProduct, RoborockBase
from roborock.data.v1 import RoborockDockTypeCode
from roborock.data.v1.v1_containers import FieldNameBase
from roborock.device_features import DeviceFeatures, RoborockDockFeatures
from roborock.devices.cache import DeviceCache
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand

# Cache of metadata for each trait class
_metadata_cache: dict[type[RoborockBase], dict[str, dict[str, Any]]] = {}


def _get_field_metadata(cls: type[RoborockBase]) -> dict[str, Any]:
    """Helper to get metadata from either class properties or dataclass fields."""
    if cls not in _metadata_cache:
        metadata_map = {}
        # Inspect properties with @field_metadata
        for name in dir(cls):
            prop = getattr(cls, name, None)
            if isinstance(prop, property):
                metadata_map[name] = getattr(prop.fget, "_field_metadata", {})
        # Inspect dataclass fields metadata
        for f in fields(cls):
            metadata_map[f.name] = f.metadata
        _metadata_cache[cls] = metadata_map
    return _metadata_cache[cls]


class DeviceTraitsConverter(common.V1TraitDataConverter):
    """Converter for APP_GET_INIT_STATUS responses into DeviceFeatures."""

    def __init__(self, product: HomeDataProduct) -> None:
        """Initialize DeviceTraitsConverter."""
        self._product = product

    def convert(self, response: common.V1ResponseData) -> DeviceFeatures:
        """Parse an APP_GET_INIT_STATUS response into a DeviceFeatures instance."""
        if not isinstance(response, list):
            raise ValueError(f"Unexpected AppInitStatus response format: {type(response)}: {response!r}")
        app_status = AppInitStatus.from_dict(response[0])
        return DeviceFeatures.from_feature_flags(
            new_feature_info=app_status.new_feature_info,
            new_feature_info_str=app_status.new_feature_info_str,
            feature_info=app_status.feature_info,
            product_nickname=self._product.product_nickname,
        )


class DeviceFeaturesTrait(DeviceFeatures, common.V1TraitMixin):
    """Trait for managing supported features on Roborock devices."""

    command = RoborockCommand.APP_GET_INIT_STATUS
    converter: DeviceTraitsConverter

    def __init__(self, product: HomeDataProduct, device_cache: DeviceCache) -> None:  # pylint: disable=super-init-not-called
        """Initialize DeviceFeaturesTrait."""
        common.V1TraitMixin.__init__(self)
        self.converter = DeviceTraitsConverter(product)
        self._product = product
        self._device_cache = device_cache
        # Dock features are populated after device feature discovery
        # is triggered.
        self.dock_features: RoborockDockFeatures = RoborockDockFeatures.from_dock_type(RoborockDockTypeCode.o0_dock)
        # All fields of DeviceFeatures are required. Initialize them to False
        # so we have some known state.
        for field in fields(self):
            setattr(self, field.name, False)

    def is_field_supported(self, cls: type[RoborockBase], field_name: FieldNameBase) -> bool:
        """Determines if the specified field is supported by this device.

        We inspect the metadata defined for the field (either via dataclass field metadata
        or the `@field_metadata` decorator on properties). Supported checks include:

        - `feature`: Maps to a boolean capability property on `DeviceFeatures` / `DeviceFeaturesTrait`
          (e.g. `is_support_water_mode`).
        - `dock_feature`: Maps to a boolean capability property on `RoborockDockFeatures` (e.g. `is_washable`).
        - `dps`: Maps to a `RoborockDataProtocol` ID checked against the product's supported schema IDs.
        """
        if self.dock_features is None:
            raise ValueError("DeviceFeaturesTrait was invoked but was not fully initialized")
        metadata_map = _get_field_metadata(cls)
        if (field_metadata := metadata_map.get(field_name)) is not None:
            if (feature := field_metadata.get("feature")) is not None:
                return getattr(self, feature, False)
            if (dock_feature := field_metadata.get("dock_feature")) is not None:
                return getattr(self.dock_features, dock_feature, False)
            if (dps := field_metadata.get("dps")) is not None:
                return int(dps) in self._product.supported_schema_ids
        # No metadata, field is assumed always supported
        return True

    async def refresh(self) -> None:
        """Refresh the contents of this trait.

        This will use cached device features if available since they do not
        change often and this avoids unnecessary RPC calls. This would only
        ever change with a firmware update, so caching is appropriate.
        """
        cache_data = await self._device_cache.get()
        if cache_data.device_features is not None:
            common.merge_trait_values(self, cache_data.device_features)
            return
        # Save cached device features
        await super().refresh()
        cache_data.device_features = self
        await self._device_cache.set(cache_data)
