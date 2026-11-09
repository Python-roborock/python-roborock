"""Plan updates to individual V1 dynamic map elements.

Each element has a generation nonce and a cursor counting accepted logical
records. Announcements and pages produce new cursors and merge decisions;
these helpers neither fetch data nor mutate cached map bytes. Whole-map
orchestration and byte merging are separate steps.
"""

import struct
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Self

from roborock.data.v1.dynamic_map import DynamicDataResponse, DynamicMapDiffEntry, DynamicMapResult
from roborock.exceptions import RoborockException

from .dynamic_blocks import MapBlock, find_block

PATH_ELEMENT_ID = 3

FLOOR_MAP_ELEMENT_ID = 24

PATH_BLOCK_TYPE = 3

POSE_BLOCK_TYPE = 8

MOP_FLAGS_BLOCK_TYPE = 18

PATH_ARGS_BLOCK_TYPE = 57

PAGE_LIMITS: dict[int, int] = {
    3: 500,
    6: 50,
    11: 50,
    15: 80,
    16: 80,
    21: 50,
    24: 32,
    25: 100,
    27: 5,
    29: 50,
    30: 50,
    31: 50,
    32: 32,
    36: 50,
    37: 50,
    38: 50,
    42: 50,
    44: 50,
    45: 50,
    46: 50,
    50: 50,
    51: 50,
    52: 50,
    53: 50,
    58: 50,
    60: 50,
}

_STANDARD_NUM_HEADER_LEN = 12

_PATH_HEADER_LEN = 20

_U32 = struct.Struct("<I")

_STANDARD_NUM_ELEMENTS = frozenset({6, 11, 15, 16, 21, 25, 27, 29, 30, 31, 36, 42, 44, 45, 46, 50, 51, 52, 53, 60})

MERGEABLE_ELEMENTS = frozenset({PATH_ELEMENT_ID, FLOOR_MAP_ELEMENT_ID}) | _STANDARD_NUM_ELEMENTS


def page_limit(element_id: int) -> int:
    """Records per page, or zero for an element whose content is unsupported."""
    if element_id not in MERGEABLE_ELEMENTS:
        return 0
    return PAGE_LIMITS.get(element_id, 0)


@dataclass(frozen=True)
class ElementState:
    """Generation and accepted logical-record count for one map element."""

    nonce: int | None = None
    """Generation identity, or ``None`` before any generation is known."""

    offset: int = 0
    """Next unread logical record, equal to the number of records cached."""

    known_total: int = 0
    """Advertised total for this generation, refreshed by accepted pages."""

    limit: int = 0
    """Maximum records per page. Zero means the element is never requested."""

    replacement_pending: bool = False
    """Whether the next accepted page must replace the cached content first."""

    reset_streak: int = 0
    """Consecutive generation resets, used to stop an endless retry loop."""

    @property
    def next_request_count(self) -> int:
        """Unread logical records, capped by the element's page limit."""
        return max(0, min(self.known_total - self.offset, self.limit))

    @property
    def is_complete(self) -> bool:
        """Whether every advertised record of this generation has been accepted."""
        return self.offset >= self.known_total


@dataclass(frozen=True)
class DynamicPage:
    """An inline diff page or a fetched element page, with decoded blocks."""

    element_id: int
    nonce: int | None
    start: int | None
    length: int | None
    max_len: int | None
    blocks: tuple[MapBlock, ...]
    success: bool
    """Whether the page reports success: ``result == 0`` or ``count == 0``."""

    generation_reset: bool = False
    """Whether an unsuccessful page reports a generation mismatch."""

    @classmethod
    def from_diff_entry(cls, element_id: int, entry: DynamicMapDiffEntry, blocks: Sequence[MapBlock]) -> Self:
        """Build a page from an inline diff entry. Inline entries never reset."""
        return cls(
            element_id=element_id,
            nonce=entry.nonce,
            start=entry.start,
            length=entry.len,
            max_len=entry.max_len,
            blocks=tuple(blocks),
            success=entry.is_success,
        )

    @classmethod
    def from_data_response(cls, response: DynamicDataResponse, blocks: Sequence[MapBlock]) -> Self:
        """Build a page from a fetched ``get_dynamic_data`` result."""
        return cls(
            element_id=response.data_id or 0,
            nonce=response.nonce,
            start=response.start,
            length=response.len,
            max_len=response.max_len,
            blocks=tuple(blocks),
            success=response.is_success,
            generation_reset=response.result is DynamicMapResult.nonce_mismatch and not response.is_success,
        )


class PageOutcome(StrEnum):
    """What the merge layer should do with a page."""

    APPEND = "append"
    """Append ``append_count`` records after discarding ``discard_leading``."""

    NO_RECORDS = "no_records"
    """Accepted, but no records move. A supplied robot pose still applies."""

    SKIP = "skip"
    """Nothing is merged and no cursor moves."""

    RESET = "reset"
    """Our generation is stale. Clear the element and restart from offset zero."""


@dataclass(frozen=True)
class PageMergePlan:
    """Instructions for merging one page, plus the resulting cursor."""

    element_id: int
    outcome: PageOutcome
    state: ElementState
    reason: str
    discard_leading: int = 0
    """Leading records of the incoming page already cached, to drop before appending."""

    append_count: int = 0
    """Records to append after discarding, equal to the cursor advance."""

    replace_content: bool = False
    """Whether cached content must be cleared before this page is applied."""

    retry_now: bool = False
    """Whether a reset should be followed by one immediate refetch."""


@dataclass(frozen=True)
class AnnouncementOutcome:
    """Result of reconciling one element announcement."""

    state: ElementState
    reason: str
    clear_content: bool = False
    """Whether the element's cached content must be dropped now."""

    full_map_required: bool = False
    """Whether this element can only be brought up to date by a full map."""


def count_path_points(block: MapBlock) -> int:
    """Count path records using their byte stride, independently of header num."""
    if block.header_length < _PATH_HEADER_LEN:
        raise RoborockException("Path block header is shorter than 20 bytes")
    (record_size,) = _U32.unpack_from(block.extra_header, _U32.size)
    if record_size == 0:
        raise RoborockException("Path block declares a zero record size")
    if len(block.payload) % record_size:
        raise RoborockException("Path block payload is not a whole number of records")
    return len(block.payload) // record_size


def _standard_num(block: MapBlock) -> int:
    """Read the ``num`` field shared by most object blocks."""
    if block.header_length < _STANDARD_NUM_HEADER_LEN:
        raise RoborockException(f"Block {block.block_type} header is shorter than 12 bytes")
    (num,) = _U32.unpack_from(block.extra_header, 0)
    return num


def element_record_count(element_id: int, blocks: Sequence[MapBlock]) -> int | None:
    """Count cached records, or return None for absent or unmeasurable elements."""
    if element_id == PATH_ELEMENT_ID:
        if (block := find_block(blocks, PATH_BLOCK_TYPE)) is None:
            return None
        return count_path_points(block)
    if element_id not in _STANDARD_NUM_ELEMENTS:
        return None
    if (block := find_block(blocks, element_id)) is None:
        return None
    return _standard_num(block)


def validate_page_content(element_id: int, blocks: Sequence[MapBlock]) -> str | None:
    """Reason the page's binary content is unusable, or ``None`` when it is usable.

    A page that fails this check must not advance a logical offset. For the
    path, points and mop flags are required together and must agree in length;
    path arguments are optional. Every other element needs its own block.
    """
    if element_id == PATH_ELEMENT_ID:
        path = find_block(blocks, PATH_BLOCK_TYPE)
        mop = find_block(blocks, MOP_FLAGS_BLOCK_TYPE)
        if path is None:
            return "path page is missing its path point block"
        if mop is None:
            return "path page is missing its mop flag block"
        try:
            points = count_path_points(path)
        except RoborockException as err:
            return str(err)
        flags = len(mop.payload)
        if not points or not flags:
            return "path page has an empty path point or mop flag array"
        if points != flags:
            return f"path page has {points} path points but {flags} mop flags"
        return None
    if (block := find_block(blocks, element_id)) is None:
        return f"page is missing the block for element {element_id}"
    if element_id in _STANDARD_NUM_ELEMENTS:
        try:
            _standard_num(block)
        except RoborockException as err:
            return str(err)
    return None


def _valid_nonce(nonce: int | None) -> bool:
    return nonce is not None and -(1 << 31) <= nonce <= 0xFFFFFFFF


def _same_nonce(left: int | None, right: int | None) -> bool:
    if left is None or right is None or not _valid_nonce(left) or not _valid_nonce(right):
        return False
    return left & 0xFFFFFFFF == right & 0xFFFFFFFF


def reconcile_announcement(
    element_id: int, state: ElementState, nonce: int | None, max_len: int | None
) -> AnnouncementOutcome:
    """Reconcile an advertised generation and total without mutating the cursor."""
    if nonce is None or max_len is None:
        return AnnouncementOutcome(state, "announcement lacks a nonce or max_len")
    if not _valid_nonce(nonce) or max_len < 0:
        return AnnouncementOutcome(state, "announcement has an invalid nonce or max_len")

    if not _same_nonce(nonce, state.nonce):
        # A replacement path longer than one page costs more round trips than a
        # full map, so we take the map instead of rebuilding the path by pages.
        if element_id == PATH_ELEMENT_ID and max_len > state.limit:
            return AnnouncementOutcome(
                state,
                f"replacement path of {max_len} points exceeds the {state.limit} point page limit",
                full_map_required=True,
            )
        if max_len == 0:
            return AnnouncementOutcome(
                replace(state, nonce=nonce, offset=0, known_total=0, replacement_pending=False, reset_streak=0),
                "new generation is empty",
                clear_content=True,
            )
        return AnnouncementOutcome(
            replace(state, nonce=nonce, offset=0, known_total=max_len, replacement_pending=True, reset_streak=0),
            f"new generation {nonce} with {max_len} records",
        )

    if max_len == state.known_total and max_len <= state.offset:
        return AnnouncementOutcome(state, "element is already complete")

    if max_len == 0 and state.known_total > 0:
        return AnnouncementOutcome(
            replace(state, offset=0, known_total=0, replacement_pending=False),
            "generation emptied",
            clear_content=True,
        )

    # Keep the generation and the offset. A total that went down does not
    # truncate records we already hold, so the known total never rolls back.
    return AnnouncementOutcome(
        replace(state, known_total=max(max_len, state.known_total)),
        "more data may be available",
    )


def _skip(page: DynamicPage, state: ElementState, reason: str) -> PageMergePlan:
    """A page that merges nothing and leaves the cursor exactly where it was."""
    return PageMergePlan(element_id=page.element_id, outcome=PageOutcome.SKIP, state=state, reason=reason)


def plan_page_merge(state: ElementState, page: DynamicPage) -> PageMergePlan:
    """Plan a page update; rejected content leaves its cursor unchanged."""
    if page.element_id not in MERGEABLE_ELEMENTS:
        return _skip(page, state, "element content is unsupported")
    if not _valid_nonce(page.nonce) or (page.max_len is not None and page.max_len < 0):
        return _skip(page, state, "page has an invalid nonce or max_len")
    if page.generation_reset:
        if page.max_len is None:
            return _skip(page, state, "generation reset lacks max_len")
        # Our generation is stale. Adopt what the device reports and restart.
        # One immediate refetch is allowed; a second consecutive reset is not,
        # so a device that keeps rejecting us cannot spin the client.
        return PageMergePlan(
            element_id=page.element_id,
            outcome=PageOutcome.RESET,
            state=replace(
                state,
                nonce=page.nonce,
                offset=0,
                known_total=page.max_len,
                replacement_pending=False,
                reset_streak=state.reset_streak + 1,
            ),
            reason=f"device reset element generation to {page.nonce}",
            replace_content=True,
            retry_now=state.reset_streak == 0,
        )

    if not page.success:
        return _skip(page, state, "page did not report success")
    if not _same_nonce(page.nonce, state.nonce):
        return _skip(page, state, f"page belongs to generation {page.nonce}, not {state.nonce}")
    if page.start is None or page.length is None:
        return _skip(page, state, "page lacks a start or length")

    start, length, offset = page.start, page.length, state.offset
    if start < 0 or length < 0:
        return _skip(page, state, "page has a negative start or length")
    if length and (problem := validate_page_content(page.element_id, page.blocks)) is not None:
        return _skip(page, state, problem)
    if length and page.element_id == PATH_ELEMENT_ID:
        path = find_block(page.blocks, PATH_BLOCK_TYPE)
        if path is None or count_path_points(path) != length:
            return _skip(page, state, "path record count differs from the returned length")

    # Accepting a page adopts the total it reports, which may differ from the
    # total announced earlier.
    accepted_total = page.max_len if page.max_len is not None else state.known_total

    if start == offset and length > 0:
        return PageMergePlan(
            element_id=page.element_id,
            outcome=PageOutcome.APPEND,
            state=replace(
                state,
                offset=offset + length,
                known_total=accepted_total,
                replacement_pending=False,
                reset_streak=0,
            ),
            reason=f"appending {length} records at offset {offset}",
            append_count=length,
            replace_content=state.replacement_pending,
        )

    if start == offset:
        # An empty page at the cursor still refreshes the total, and for the
        # path it may carry a robot pose. No records move either way.
        return PageMergePlan(
            element_id=page.element_id,
            outcome=PageOutcome.NO_RECORDS,
            state=replace(state, known_total=accepted_total, reset_streak=0),
            reason="page carries no records",
        )

    if start < offset < start + length:
        if page.element_id != PATH_ELEMENT_ID:
            return _skip(page, state, "overlapping pages are only accepted for the path")
        discard = offset - start
        return PageMergePlan(
            element_id=page.element_id,
            outcome=PageOutcome.APPEND,
            state=replace(
                state,
                offset=start + length,
                known_total=accepted_total,
                replacement_pending=False,
                reset_streak=0,
            ),
            reason=f"accepting the {length - discard} unseen records of an overlapping page",
            discard_leading=discard,
            append_count=length - discard,
            replace_content=state.replacement_pending,
        )

    if start + length <= offset:
        return _skip(page, state, "page is entirely older than the cursor")
    return _skip(page, state, f"page starts at {start}, leaving a gap after {offset}")
