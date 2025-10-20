"""Trait for smart wash parameters."""

from roborock.data import SmartWashParams
from roborock.device_features import is_wash_n_fill_dock
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand


class SmartWashParamsTrait(SmartWashParams, common.V1TraitMixin):
    """Trait for smart wash parameters."""

    command = RoborockCommand.GET_SMART_WASH_PARAMS
    requires_dock_type = is_wash_n_fill_dock
