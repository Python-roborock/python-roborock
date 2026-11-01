"""Wire models for the V1 dynamic map diff commands.

These dataclasses describe the JSON results of ``get_dynamic_map_diff`` and
``get_dynamic_data`` after ordinary command-response decoding, plus the
snapshot metadata a full map result can carry. Field names match the wire keys
so ``RoborockBase.from_dict`` maps them directly.

The models are deliberately passive. They decode base64 and answer the spec's
success predicate, but they hold no element state and make no merge decisions.
That logic lives with the dynamic element state machine.
"""

import base64
import binascii
from dataclasses import dataclass

from roborock.exceptions import RoborockException

from ..code_mappings import RoborockEnum
from ..containers import RoborockBase

__all__ = [
    "DynamicMapResult",
    "DynamicMapDiffEntry",
    "DynamicMapDiffResponse",
    "DynamicDataResponse",
    "DynamicMapSnapshotEntry",
    "DynamicMapSnapshot",
    "dynamic_map_diff_params",
    "dynamic_data_params",
]


class DynamicMapResult(RoborockEnum):
    """Application-level status returned by the dynamic map commands.

    For ``get_dynamic_map_diff`` a ``nonce_mismatch`` means the requested base
    map is no longer current. For ``get_dynamic_data`` it means the requested
    element generation is no longer current. Neither establishes a new
    generation by itself; the accompanying nonce does.
    """

    unknown = -1
    ok = 0
    nonce_mismatch = 1
    full_map_required = 2


def _decode_base64(value: str | None, field_name: str) -> bytes | None:
    """Decode standard or URL-safe base64, or return ``None`` when absent."""
    if value is None:
        return None
    try:
        return base64.b64decode(value, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as err:
        raise RoborockException(f"Dynamic map field '{field_name}' is not valid base64") from err


def _validated_nonce(nonce: int) -> int:
    """Validate a 32-bit identity without changing its wire representation."""
    if not -(1 << 31) <= nonce <= 0xFFFFFFFF:
        raise ValueError("nonce must fit a signed or unsigned 32-bit integer")
    return nonce


@dataclass
class DynamicMapDiffEntry(RoborockBase):
    """One element entry inside a ``get_dynamic_map_diff`` result.

    Refresh indicators (charger, map image, ...) carry only ``count``. Dynamic
    elements carry ``nonce`` and ``max_len``; the path element can also carry
    an inline page via ``start``, ``len``, and ``data``.
    """

    count: int | None = None
    """Change indicator since the base-map snapshot. Not an item or byte count."""

    result: DynamicMapResult | None = None
    """Optional page status; inline captures normally use ``count`` instead."""

    nonce: int | None = None
    """Element generation identity."""

    max_len: int | None = None
    """Total logical length currently available for this generation."""

    start: int | None = None
    """Zero-based logical offset of an inline page."""

    len: int | None = None
    """Logical item count of an inline page."""

    data: str | None = None
    """Base64 block sequence of an inline page."""

    obstacle: int | None = None
    """Obstacle component of the main map image count, when reported."""

    space: int | None = None
    """Space component of the main map image count, when reported."""

    @property
    def decoded_data(self) -> bytes | None:
        """The inline page blocks, base64-decoded."""
        return _decode_base64(self.data, "data")

    @property
    def has_inline_page(self) -> bool:
        """Whether the inline range and data fields are present."""
        return self.start is not None and self.len is not None and self.data is not None

    @property
    def is_success(self) -> bool:
        """App acceptance predicate for a page: ``result == 0 or count == 0``."""
        return self.result is DynamicMapResult.ok or self.count == 0


@dataclass
class DynamicMapDiffResponse(RoborockBase):
    """Result object of ``get_dynamic_map_diff``."""

    result: DynamicMapResult | None = None
    """Application status. ``None`` when the device omitted it."""

    nonce: int | None = None
    """Map nonce the diff was computed against."""

    diff: dict[int, DynamicMapDiffEntry] | None = None
    """Element entries keyed by element id. An omitted element has no update."""

    robot_data: str | None = None
    """Base64 block sequence that updates the robot without adding path points."""

    @property
    def decoded_robot_data(self) -> bytes | None:
        """The robot-only blocks, base64-decoded."""
        return _decode_base64(self.robot_data, "robot_data")

    def is_for_map(self, map_nonce: int) -> bool:
        """Whether ``diff`` may be applied to the base map identified by ``map_nonce``."""
        if self.result is not DynamicMapResult.ok or self.nonce is None or self.diff is None:
            return False
        try:
            return (_validated_nonce(self.nonce) & 0xFFFFFFFF) == (_validated_nonce(map_nonce) & 0xFFFFFFFF)
        except ValueError:
            return False


@dataclass
class DynamicDataResponse(RoborockBase):
    """Result object of ``get_dynamic_data``: one page of one element generation."""

    result: DynamicMapResult | None = None
    count: int | None = None
    """Optional inline-page indicator accepted by the app's shared page handler."""

    nonce: int | None = None
    """Element nonce the page belongs to."""

    data_id: int | None = None
    start: int | None = None
    len: int | None = None
    """Actual logical range returned, which may be shorter than requested."""

    max_len: int | None = None
    """Total available length, which may have changed since it was announced."""

    data: str | None = None

    @property
    def decoded_data(self) -> bytes | None:
        """The page blocks, base64-decoded."""
        return _decode_base64(self.data, "data")

    @property
    def is_success(self) -> bool:
        """App acceptance predicate for a page: ``result == 0 or count == 0``."""
        return self.result is DynamicMapResult.ok or self.count == 0


@dataclass
class DynamicMapSnapshotEntry(RoborockBase):
    """Snapshot metadata for one element, supplied alongside a full map."""

    nonce: int | None = None
    limit_len: int | None = None
    """Page limit for the element when it has no configured limit."""


@dataclass
class DynamicMapSnapshot(RoborockBase):
    """Top-level ``nonce`` and per-element ``snapshot`` carried by a full map result."""

    nonce: int | None = None
    snapshot: dict[int, DynamicMapSnapshotEntry] | None = None


def dynamic_map_diff_params(map_nonce: int, round_marker: int | None = None) -> dict[str, int]:
    """Build ``get_dynamic_map_diff`` params for the cached base map.

    ``round_marker`` is an opaque request marker, commonly the current time in
    milliseconds. It can be omitted and is not a version, offset, or merge key.
    Preserve signed or unsigned nonce representations supplied by the caller.
    """
    params = {"nonce": _validated_nonce(map_nonce)}
    if round_marker is not None:
        params["round"] = round_marker
    return params


def dynamic_data_params(element_nonce: int, data_id: int, start: int, length: int) -> dict[str, int]:
    """Build ``get_dynamic_data`` params for one element range.

    ``length`` of zero asks for the remaining available items, capped by the
    element limit. Nonces retain the caller's signed or unsigned representation.
    """
    if start < 0 or length < 0:
        raise ValueError("start and length must be nonnegative")
    if data_id <= 0:
        raise ValueError("data_id must be positive")
    return {"nonce": _validated_nonce(element_nonce), "data_id": data_id, "start": start, "len": length}
