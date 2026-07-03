"""Common helpers for Q10 B01 traits.

Q10 devices push their full state as a single decoded DPS dictionary (see
``Q10PropertiesApi._subscribe_loop``). Each trait owns a small ``RoborockBase``
read-model whose fields are annotated with ``field(metadata={"dps": ...})`` and
only updates the fields it is responsible for, ignoring the rest.

The :class:`UpdatableTrait` base wires that read-model to the update lifecycle
and (for traits that also write) exposes the ``dpCommon`` (101) wrapper used by
Q10 setting writes.
"""

import logging
from typing import Any, ClassVar, cast

from roborock.data.b01_q10.b01_q10_code_mappings import B01_Q10_DP
from roborock.data.containers import RoborockBase
from roborock.devices.traits.common import DpsDataConverter, TraitUpdateListener

from .command import CommandTrait


class UpdatableTrait(TraitUpdateListener):
    """Base for Q10 traits backed by a read-model updated from the DPS stream.

    Concrete traits subclass both their ``RoborockBase`` read-model and this
    class, set the ``_CONVERTER`` class attribute, and initialize the read-model
    explicitly in their constructor, e.g.::

        class SoundVolumeTrait(SoundVolume, UpdatableTrait):
            _CONVERTER = DpsDataConverter.from_dataclass(SoundVolume)

            def __init__(self, command: CommandTrait) -> None:
                SoundVolume.__init__(self)
                UpdatableTrait.__init__(self, command, _LOGGER)

    The read-model init is called explicitly (rather than via ``super()``)
    because the read-model dataclass precedes this class in the MRO.

    Traits that also send commands receive a :class:`CommandTrait` and use the
    :meth:`_write` helper, which wraps the write in the ``dpCommon`` (101) data
    point as the device requires.
    """

    _CONVERTER: ClassVar[DpsDataConverter]

    def __init__(self, command: CommandTrait | None, logger: logging.Logger) -> None:
        """Initialize the update listener. The read-model is initialized by the subclass."""
        TraitUpdateListener.__init__(self, logger=logger)
        self._command = command

    def update_from_dps(self, decoded_dps: dict[B01_Q10_DP, Any]) -> None:
        """Update the trait's read-model from raw DPS data and notify listeners.

        Concrete traits also subclass a ``RoborockBase`` read-model, so the cast
        is always valid at runtime.
        """
        if self._CONVERTER.update_from_dps(cast(RoborockBase, self), decoded_dps):
            self._notify_update()

    async def _write(self, dp: B01_Q10_DP, value: int) -> None:
        """Write a single data point value via the dpCommon (101) wrapper.

        Q10 setting writes must be wrapped in ``dpCommon`` (101), e.g. setting
        the volume sends ``{"dps": {"101": {"26": <value>}}}``. Writing the bare
        data point (without the wrapper) is silently ignored by the device.
        """
        if self._command is None:
            raise ValueError("Trait is read-only; no command channel was provided")
        await self._command.send(B01_Q10_DP.COMMON, {str(dp.code): value})
