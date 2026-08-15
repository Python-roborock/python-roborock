"""Read-only typed state for Zeo (washing machine / dryer) devices.

This module provides ``ZeoStatusTrait``, a single typed trait holding the
read-only DPs reported by the device (state, errors, timers, tank levels,
etc.).
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from roborock.data.containers import RoborockBase
from roborock.data.zeo.zeo_code_mappings import (
    ZeoDirtDetectionStatus,
    ZeoDryerStartError,
    ZeoError,
    ZeoState,
)
from roborock.data.zeo.zeo_containers import ZeoWashLog
from roborock.devices.traits.common import DpsDataConverter, TraitUpdateListener
from roborock.roborock_message import RoborockZeoProtocol

_LOGGER = logging.getLogger(__name__)


@dataclass(init=False)
class ZeoStatusTrait(RoborockBase, TraitUpdateListener):
    """Read-only state of a Zeo device, updated from the MQTT push stream.

    Fields are populated by :meth:`update_from_dps` from the device-reported
    data (no setters — everything here is read-only). Fields that a given
    device family does not report simply remain ``None``.
    """

    # Shared state (both washers and dryers).
    state: ZeoState | None = field(default=None, metadata={"dps": RoborockZeoProtocol.STATE})
    error: ZeoError | None = field(default=None, metadata={"dps": RoborockZeoProtocol.ERROR})
    washing_left: int | None = field(default=None, metadata={"dps": RoborockZeoProtocol.WASHING_LEFT})
    doorlock_state: bool | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.DOORLOCK_STATE}
    )
    times_after_clean: int | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.TIMES_AFTER_CLEAN}
    )
    app_authorization: bool | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.APP_AUTHORIZATION}
    )

    # Washer-specific status (None on dryers).
    dirt_detection_status: ZeoDirtDetectionStatus | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.DIRT_DETECTION_STATUS}
    )
    detergent_empty: bool | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.DETERGENT_EMPTY}
    )
    softener_empty: bool | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.SOFTENER_EMPTY}
    )

    # Dryer-specific status (None on washers).
    total_time: int | None = field(default=None, metadata={"dps": RoborockZeoProtocol.TOTAL_TIME})
    cloth_put_in: bool | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.CLOTH_PUT_IN}
    )
    cloth_ready_to_dry_count_down: int | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.CLOTH_READY_TO_DRY_COUNT_DOWN}
    )
    start_dryer_error: ZeoDryerStartError | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.START_DRYER_ERROR}
    )

    # Smart-hosting status.
    smart_hosting_time: int | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.SMART_HOSTING_TIME}
    )
    smart_hosting_waited_time: int | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.SMART_HOSTING_WAITED_TIME}
    )
    is_need_fluff_clean: bool | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.IS_NEED_FLUFF_CLEAN}
    )

    # Other read-only status.
    custom_program_cleaning_time: int | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.CUSTOM_PROGRAM_CLEANING_TIME}
    )
    panel_program_params_set_result: int | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.PANEL_PROGRAM_PARAMS_SET_RESULT}
    )
    panel_timing_program_params: int | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.PANEL_TIMING_PROGRAM_PARAMS}
    )
    steam_care_time: int | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.STEAM_CARE_TIME}
    )
    device_bound: bool | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.DEVICE_BOUND}
    )

    # Meta — device-reported JSON documents (read-only).
    product_info: dict[str, Any] | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.PRODUCT_INFO}
    )
    washing_log: ZeoWashLog | None = field(
        default=None, metadata={"dps": RoborockZeoProtocol.WASHING_LOG}
    )

    def __init__(self) -> None:
        """Initialize the status trait."""
        TraitUpdateListener.__init__(self, _LOGGER)
        self._converter = DpsDataConverter.from_dataclass(type(self))

    def update_from_dps(self, decoded_dps: dict[int, Any]) -> bool:
        """Update trait fields from raw device DPS data.

        Meta fields that arrive as JSON strings (``product_info``,
        ``washing_log``) are parsed before conversion. Returns True if any
        field changed (and notifies update listeners).
        """
        # JSON-string meta fields: parse them into dicts so the converter can
        # build the typed containers / dicts from them.
        for dp in (RoborockZeoProtocol.PRODUCT_INFO, RoborockZeoProtocol.WASHING_LOG):
            raw = decoded_dps.get(int(dp))
            if isinstance(raw, str):
                try:
                    decoded_dps[int(dp)] = json.loads(raw)
                except ValueError:
                    _LOGGER.debug("Failed to parse JSON for DP %s", dp, exc_info=True)

        if self._converter.update_from_dps(self, decoded_dps):
            self._notify_update()
            return True
        return False
