"""Trait for wash towel mode."""

from roborock.data import WashTowelMode
from roborock.device_features import is_wash_n_fill_dock
from roborock.devices.traits.v1 import common
from roborock.roborock_typing import RoborockCommand


class WashTowelModeTrait(WashTowelMode, common.V1TraitMixin):
    """Trait for wash towel mode."""

    command = RoborockCommand.GET_WASH_TOWEL_MODE
    requires_dock_type = is_wash_n_fill_dock
