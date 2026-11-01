"""Tests for V1 element cursor transitions and page decisions using synthetic blocks."""

import base64
import struct

import pytest

from roborock.data.v1 import (
    DynamicDataResponse,
    DynamicMapDiffEntry,
)
from roborock.exceptions import RoborockException
from roborock.map.dynamic_blocks import MapBlock, encode_blocks, parse_dynamic_value
from roborock.map.dynamic_state import (
    PAGE_LIMITS,
    PATH_ELEMENT_ID,
    DynamicPage,
    ElementState,
    PageOutcome,
    count_path_points,
    element_record_count,
    page_limit,
    plan_page_merge,
    reconcile_announcement,
    validate_page_content,
)

PATH_LIMIT = PAGE_LIMITS[PATH_ELEMENT_ID]
OBSTACLE_ELEMENT_ID = 15


# --- Block builders ----------------------------------------------------------


def path_block(points: int, *, record_size: int = 4, num: int | None = None, angle: int = 0) -> MapBlock:
    """Block 3 holding ``points`` records of ``record_size`` bytes."""
    extra = struct.pack("<III", points if num is None else num, record_size, angle)
    return MapBlock(3, bytes(points * record_size), extra)


def mop_block(flags: int) -> MapBlock:
    """Block 18 holding one mop-state byte per path point."""
    return MapBlock(18, b"\x01" * flags)


def pose_block(x: int = 100, y: int = 200, angle: int = 90) -> MapBlock:
    """Block 8 holding a signed robot pose."""
    return MapBlock(8, struct.pack("<iii", x, y, angle))


def args_block(num: int) -> MapBlock:
    """Block 57 holding one optional argument word per path point."""
    return MapBlock(57, bytes(num * 4), struct.pack("<I", num))


def object_block(element_id: int, num: int, *, record_size: int = 8) -> MapBlock:
    """An object block with the standard ``num`` header."""
    return MapBlock(element_id, bytes(num * record_size), struct.pack("<I", num))


def path_page(points: int, *, pose: bool = False, args: bool = False) -> tuple[MapBlock, ...]:
    """A well-formed element 3 page of ``points`` points."""
    blocks = [path_block(points), mop_block(points)]
    if args:
        blocks.append(args_block(points))
    if pose:
        blocks.append(pose_block())
    return tuple(blocks)


def page(
    element_id: int = PATH_ELEMENT_ID,
    *,
    nonce: int | None = 9001,
    start: int | None = 0,
    length: int | None = 10,
    max_len: int | None = 10,
    blocks: tuple[MapBlock, ...] | None = None,
    success: bool = True,
    generation_reset: bool = False,
) -> DynamicPage:
    """A page with well-formed content unless the caller overrides it."""
    if blocks is None:
        blocks = path_page(length or 0) if element_id == PATH_ELEMENT_ID else (object_block(element_id, length or 0),)
    return DynamicPage(
        element_id=element_id,
        nonce=nonce,
        start=start,
        length=length,
        max_len=max_len,
        blocks=blocks,
        success=success and not generation_reset,
        generation_reset=generation_reset,
    )


def path_state(offset: int = 0, known_total: int = 0, *, replacement_pending: bool = False) -> ElementState:
    """An element 3 cursor carrying the real path page limit."""
    return ElementState(
        nonce=9001, offset=offset, known_total=known_total, limit=PATH_LIMIT, replacement_pending=replacement_pending
    )


# --- next_request_count ------------------------------------------------------


@pytest.mark.parametrize(
    ("offset", "known_total", "limit", "expected"),
    [(0, 1040, 500, 500), (50, 40, 500, 0), (0, 100, 0, 0)],
    ids=["capped-by-limit", "total-below-offset-is-zero", "no-limit-means-never-fetch"],
)
def test_next_request_count(offset: int, known_total: int, limit: int, expected: int) -> None:
    """The requested count is max(0, min(known_total - offset, limit))."""
    assert ElementState(offset=offset, known_total=known_total, limit=limit).next_request_count == expected


# --- Reconcile table ---------------------------------------------------------


def test_reconcile_row1_missing_fields_makes_no_decision() -> None:
    """Row 1: an entry without nonce or max_len cannot move the cursor."""
    state = path_state(offset=10, known_total=10)
    assert reconcile_announcement(PATH_ELEMENT_ID, state, None, 40).state == state
    assert reconcile_announcement(PATH_ELEMENT_ID, state, 9001, None).state == state


def test_reconcile_row2_complete_element() -> None:
    """Row 2: same generation, same total, nothing beyond the cursor."""
    state = path_state(offset=40, known_total=40)
    outcome = reconcile_announcement(PATH_ELEMENT_ID, state, 9001, 40)
    assert outcome.state == state
    assert outcome.state.next_request_count == 0
    assert not outcome.clear_content and not outcome.full_map_required


@pytest.mark.parametrize(
    ("offset", "known_total", "announced", "expected_total", "expected_fetch"),
    [
        (40, 40, 100, 100, 60),
        (40, 100, 40, 100, 60),
        (10, 50, 50, 50, 40),
        (0, 0, 1040, 1040, PATH_LIMIT),
    ],
    ids=["total-grew", "total-shrank-no-rollback", "total-equal-but-unread", "capped-by-page-limit"],
)
def test_reconcile_row3_same_generation_keeps_offset(
    offset: int, known_total: int, announced: int, expected_total: int, expected_fetch: int
) -> None:
    """Row 3: the generation and offset survive; the known total never rolls back."""
    outcome = reconcile_announcement(PATH_ELEMENT_ID, path_state(offset, known_total), 9001, announced)
    assert outcome.state.nonce == 9001
    assert outcome.state.offset == offset
    assert outcome.state.known_total == expected_total
    assert outcome.state.next_request_count == expected_fetch
    assert not outcome.clear_content


def test_reconcile_row4_zero_total_clears_same_generation() -> None:
    """Row 4: an explicit zero total on the cached generation clears it."""
    outcome = reconcile_announcement(PATH_ELEMENT_ID, path_state(offset=40, known_total=100), 9001, 0)
    assert outcome.clear_content
    assert outcome.state.nonce == 9001
    assert (outcome.state.offset, outcome.state.known_total) == (0, 0)
    assert not outcome.state.replacement_pending


def test_reconcile_row5_new_generation_resets_cursor() -> None:
    """Row 5: a new nonce restarts at zero and marks the content for replacement."""
    outcome = reconcile_announcement(PATH_ELEMENT_ID, path_state(offset=40, known_total=40), 9002, 100)
    assert outcome.state.nonce == 9002
    assert (outcome.state.offset, outcome.state.known_total) == (0, 100)
    assert outcome.state.replacement_pending
    assert outcome.state.next_request_count == 100
    assert not outcome.clear_content, "content is replaced on first merge, not dropped now"


def test_reconcile_row6_new_empty_generation_clears_immediately() -> None:
    """Row 6: a new generation with no records clears the element at once."""
    outcome = reconcile_announcement(PATH_ELEMENT_ID, path_state(offset=40, known_total=40), 9002, 0)
    assert outcome.clear_content
    assert outcome.state.nonce == 9002
    assert (outcome.state.offset, outcome.state.known_total) == (0, 0)
    assert not outcome.state.replacement_pending


@pytest.mark.parametrize(
    ("announced", "expected_full_map"),
    [(PATH_LIMIT, False), (PATH_LIMIT + 1, True)],
    ids=["at-limit", "one-over-limit"],
)
def test_reconcile_row7_long_replacement_path_needs_full_map(announced: int, expected_full_map: bool) -> None:
    """Row 7: rebuilding a long replacement path by pages costs more than a full map."""
    outcome = reconcile_announcement(PATH_ELEMENT_ID, path_state(offset=40, known_total=40), 9002, announced)
    assert outcome.full_map_required is expected_full_map
    if expected_full_map:
        assert outcome.state == path_state(offset=40, known_total=40), "state is left for the full map to rebuild"


def test_reconcile_row7_applies_only_to_the_path() -> None:
    """Row 7 is specific to element 3; other elements page through a long replacement."""
    state = ElementState(nonce=9001, offset=10, known_total=10, limit=PAGE_LIMITS[OBSTACLE_ELEMENT_ID])
    outcome = reconcile_announcement(OBSTACLE_ELEMENT_ID, state, 9002, 500)
    assert not outcome.full_map_required
    assert outcome.state.nonce == 9002
    assert outcome.state.next_request_count == PAGE_LIMITS[OBSTACLE_ELEMENT_ID]


# --- Accept table ------------------------------------------------------------


def test_accept_row1_append_at_cursor() -> None:
    """Row 1: a page starting at the cursor appends its records."""
    plan = plan_page_merge(path_state(offset=1000, known_total=1040), page(start=1000, length=40, max_len=1040))
    assert plan.outcome is PageOutcome.APPEND
    assert (plan.discard_leading, plan.append_count) == (0, 40)
    assert plan.state.offset == 1040
    assert plan.state.known_total == 1040
    assert plan.state.next_request_count == 0


def test_accept_row1_replacement_clears_before_first_merge() -> None:
    """Row 1: a pending replacement drops the old generation before appending."""
    state = path_state(offset=0, known_total=100, replacement_pending=True)
    plan = plan_page_merge(state, page(start=0, length=100, max_len=100))
    assert plan.outcome is PageOutcome.APPEND
    assert plan.replace_content
    assert not plan.state.replacement_pending, "replacement is consumed by the first accepted page"


def test_accept_row1_second_page_does_not_replace_again() -> None:
    """Row 1: only the first page of a replacement generation clears content."""
    first = plan_page_merge(
        path_state(offset=0, known_total=80, replacement_pending=True), page(start=0, length=50, max_len=80)
    )
    second = plan_page_merge(first.state, page(start=50, length=30, max_len=80))
    assert second.outcome is PageOutcome.APPEND
    assert not second.replace_content
    assert second.state.offset == 80


def test_accept_row2_empty_path_page_updates_total_only() -> None:
    """Row 2: an empty path page keeps the arrays and refreshes the total."""
    plan = plan_page_merge(
        path_state(offset=40, known_total=40), page(start=40, length=0, max_len=120, blocks=(pose_block(),))
    )
    assert plan.outcome is PageOutcome.NO_RECORDS
    assert plan.append_count == 0
    assert plan.state.offset == 40
    assert plan.state.known_total == 120
    assert plan.state.next_request_count == 80


def test_accept_row3_empty_page_for_another_element() -> None:
    """Row 3: an empty page for another element appends nothing."""
    state = ElementState(nonce=9002, offset=2, known_total=2, limit=80)
    plan = plan_page_merge(state, page(OBSTACLE_ELEMENT_ID, nonce=9002, start=2, length=0, max_len=2, blocks=()))
    assert plan.outcome is PageOutcome.NO_RECORDS
    assert plan.state.offset == 2


def test_accept_row4_path_overlap_keeps_only_the_suffix() -> None:
    """Row 4: an overlapping path page contributes only its unseen tail."""
    plan = plan_page_merge(path_state(offset=30, known_total=100), page(start=20, length=40, max_len=100))
    assert plan.outcome is PageOutcome.APPEND
    assert plan.discard_leading == 10, "records 20..29 are already cached"
    assert plan.append_count == 30, "records 30..59 are new"
    assert plan.state.offset == 60


def test_accept_row4_overlap_of_a_single_unseen_record() -> None:
    """Row 4: an overlap leaving one unseen record still advances by one."""
    plan = plan_page_merge(path_state(offset=39, known_total=100), page(start=0, length=40, max_len=100))
    assert (plan.discard_leading, plan.append_count) == (39, 1)
    assert plan.state.offset == 40


@pytest.mark.parametrize(
    ("offset", "start", "length"),
    [(40, 0, 40), (40, 10, 20)],
    ids=["exactly-consumed", "fully-inside"],
)
def test_accept_row5_entirely_old_pages_are_dropped(offset: int, start: int, length: int) -> None:
    """Row 5: a page ending at or before the cursor contributes nothing."""
    state = path_state(offset=offset, known_total=100)
    plan = plan_page_merge(state, page(start=start, length=length, max_len=100))
    assert plan.outcome is PageOutcome.SKIP
    assert plan.state.offset == offset


def test_accept_row6_gap_does_not_advance() -> None:
    """Row 6: a page starting past the cursor leaves a hole and is refused."""
    plan = plan_page_merge(path_state(offset=40, known_total=200), page(start=60, length=40, max_len=200))
    assert plan.outcome is PageOutcome.SKIP
    assert "gap" in plan.reason
    assert plan.state.offset == 40, "the cursor must not jump to the page end"


def test_accept_row7_overlap_refused_for_other_elements() -> None:
    """Row 7: the overlap exception belongs to the path alone."""
    state = ElementState(nonce=9002, offset=30, known_total=100, limit=80)
    plan = plan_page_merge(state, page(OBSTACLE_ELEMENT_ID, nonce=9002, start=20, length=40, max_len=100))
    assert plan.outcome is PageOutcome.SKIP
    assert "overlapping" in plan.reason
    assert plan.state.offset == 30


def test_accept_row8_page_from_another_generation() -> None:
    """Row 8: a successful page for a different nonce is not merged."""
    plan = plan_page_merge(path_state(offset=10, known_total=100), page(nonce=9999, start=10, length=10, max_len=100))
    assert plan.outcome is PageOutcome.SKIP
    assert plan.state == path_state(offset=10, known_total=100)


def test_accept_row9_generation_reset_restarts_the_element() -> None:
    """Row 9: result 1 clears the element and adopts the device's generation."""
    plan = plan_page_merge(
        path_state(offset=40, known_total=40), page(nonce=9005, start=0, length=0, max_len=12, generation_reset=True)
    )
    assert plan.outcome is PageOutcome.RESET
    assert plan.replace_content
    assert plan.retry_now
    assert plan.state.nonce == 9005
    assert (plan.state.offset, plan.state.known_total) == (0, 12)
    assert plan.state.next_request_count == 12


def test_accept_row9_consecutive_resets_stop_retrying() -> None:
    """Row 9: one immediate retry is allowed, not an unbounded loop."""
    first = plan_page_merge(
        path_state(offset=40, known_total=40), page(nonce=9005, length=0, max_len=12, generation_reset=True)
    )
    assert first.retry_now
    second = plan_page_merge(first.state, page(nonce=9006, length=0, max_len=12, generation_reset=True))
    assert second.outcome is PageOutcome.RESET
    assert not second.retry_now, "a second consecutive reset must not retry again"


def test_accept_successful_page_clears_the_reset_streak() -> None:
    """A page that merges resets the retry budget for future generations."""
    reset = plan_page_merge(
        path_state(offset=40, known_total=40), page(nonce=9005, length=0, max_len=40, generation_reset=True)
    )
    accepted = plan_page_merge(reset.state, page(nonce=9005, start=0, length=40, max_len=40))
    assert accepted.state.reset_streak == 0


def test_accept_unsuccessful_page_is_skipped() -> None:
    """A page reporting neither success nor a reset is ignored."""
    plan = plan_page_merge(path_state(offset=0, known_total=40), page(length=40, success=False))
    assert plan.outcome is PageOutcome.SKIP
    assert plan.state.offset == 0


def test_accept_page_without_a_range_is_skipped() -> None:
    """A page missing start or len carries no usable range."""
    assert plan_page_merge(path_state(), page(start=None)).outcome is PageOutcome.SKIP
    assert plan_page_merge(path_state(), page(length=None)).outcome is PageOutcome.SKIP


# --- Content validation ------------------------------------------------------


@pytest.mark.parametrize(
    ("blocks", "expected"),
    [
        (path_page(10), None),
        (path_page(10, pose=True, args=True), None),
        ((mop_block(10),), "missing its path point block"),
        ((path_block(10),), "missing its mop flag block"),
        ((path_block(10), mop_block(9)), "10 path points but 9 mop flags"),
        ((path_block(10), mop_block(0)), "empty path point or mop flag array"),
        ((path_block(4, record_size=0), mop_block(4)), "zero record size"),
        ((MapBlock(3, bytes(10)), mop_block(10)), "shorter than 20 bytes"),
    ],
    ids=[
        "valid",
        "valid-with-pose-and-args",
        "no-path-block",
        "no-mop-block",
        "length-mismatch",
        "empty-mop",
        "zero-record-size",
        "short-path-header",
    ],
)
def test_validate_path_page_content(blocks: tuple[MapBlock, ...], expected: str | None) -> None:
    """A path page needs matching, non-empty point and mop arrays."""
    problem = validate_page_content(PATH_ELEMENT_ID, blocks)
    if expected is None:
        assert problem is None
    else:
        assert problem is not None and expected in problem


def test_validate_other_element_requires_its_own_block() -> None:
    """Another element's page must contain the block for that element."""
    assert validate_page_content(OBSTACLE_ELEMENT_ID, (object_block(15, 3),)) is None
    assert validate_page_content(OBSTACLE_ELEMENT_ID, (object_block(16, 3),)) is not None
    assert validate_page_content(OBSTACLE_ELEMENT_ID, ()) is not None


def test_invalid_content_does_not_advance_the_cursor() -> None:
    """A structurally broken page is refused rather than partially merged."""
    plan = plan_page_merge(path_state(offset=10, known_total=100), page(start=10, length=40, blocks=(path_block(40),)))
    assert plan.outcome is PageOutcome.SKIP
    assert plan.state.offset == 10


def test_count_path_points_ignores_the_header_num() -> None:
    """The record array, not the header's num, determines the point count."""
    assert count_path_points(path_block(12, num=999)) == 12
    assert count_path_points(path_block(12, record_size=8)) == 12


# --- Record counting ---------------------------------------------------------


@pytest.mark.parametrize(
    ("element_id", "blocks", "expected"),
    [
        (PATH_ELEMENT_ID, (path_block(37), mop_block(37)), 37),
        (PATH_ELEMENT_ID, (mop_block(37),), None),
        (OBSTACLE_ELEMENT_ID, (object_block(15, 6),), 6),
        (24, (MapBlock(24, bytes(100)),), None),
        (37, (object_block(37, 2),), None),
    ],
    ids=["path", "path-absent", "standard-num", "floor-map-unmeasurable", "non-standard-header"],
)
def test_element_record_count(element_id: int, blocks: tuple[MapBlock, ...], expected: int | None) -> None:
    """Only elements with a trustworthy record count get a starting cursor."""
    assert element_record_count(element_id, blocks) == expected


@pytest.mark.parametrize("cached,incoming", [(-1, 0xFFFFFFFF), (0xFFFFFFFF, -1), (-0x80000000, 0x80000000)])
def test_nonce_bit_patterns_preserve_the_generation(cached: int, incoming: int) -> None:
    state = ElementState(nonce=cached, offset=5, known_total=10, limit=PATH_LIMIT)

    announced = reconcile_announcement(PATH_ELEMENT_ID, state, incoming, 12)
    accepted = plan_page_merge(state, page(nonce=incoming, start=5, length=5, max_len=12))

    assert announced.state.nonce == cached
    assert announced.state.offset == 5
    assert not announced.state.replacement_pending
    assert accepted.outcome is PageOutcome.APPEND
    assert accepted.state.nonce == cached
    assert accepted.state.offset == 10
    assert state == ElementState(nonce=cached, offset=5, known_total=10, limit=PATH_LIMIT)


def test_different_high_bit_nonce_starts_a_new_generation() -> None:
    state = ElementState(nonce=-1, offset=5, known_total=10, limit=PATH_LIMIT)
    announced = reconcile_announcement(PATH_ELEMENT_ID, state, 0xFFFFFFFE, 12)
    assert announced.state.offset == 0
    assert announced.state.replacement_pending
    assert plan_page_merge(state, page(nonce=0xFFFFFFFE, start=5)).outcome is PageOutcome.SKIP


def test_unknown_generation_is_distinct_from_zero() -> None:
    state = ElementState(limit=PATH_LIMIT)
    assert plan_page_merge(state, page(nonce=0)).outcome is PageOutcome.SKIP
    announced = reconcile_announcement(PATH_ELEMENT_ID, state, 0, 10)
    assert announced.state.nonce == 0
    assert announced.state.replacement_pending
    assert plan_page_merge(announced.state, page(nonce=0)).outcome is PageOutcome.APPEND


@pytest.mark.parametrize("nonce", [None, -(1 << 31) - 1, 1 << 32])
def test_invalid_or_missing_generation_is_ignored(nonce: int | None) -> None:
    state = path_state(5, 10)
    assert reconcile_announcement(PATH_ELEMENT_ID, state, nonce, 10).state == state
    assert plan_page_merge(state, page(nonce=nonce, start=5)).state == state
    assert plan_page_merge(state, page(nonce=nonce, generation_reset=True)).state == state


@pytest.mark.parametrize("start,length,total", [(-1, 10, 10), (0, -1, 10), (0, 10, -1)])
def test_negative_range_metadata_does_not_advance(start: int, length: int, total: int) -> None:
    state = path_state(0, 10)
    incoming = page(start=start, length=length, max_len=total, blocks=path_page(10))
    assert plan_page_merge(state, incoming).state == state
    assert reconcile_announcement(PATH_ELEMENT_ID, state, 9001, -1).state == state


def test_reset_requires_a_reported_total() -> None:
    state = path_state(5, 10)
    assert plan_page_merge(state, page(generation_reset=True, max_len=None)).outcome is PageOutcome.SKIP


@pytest.mark.parametrize("element_id", [99, 32, 37, 38, 58])
def test_unsupported_elements_are_not_fetched_or_merged(element_id: int) -> None:
    assert page_limit(element_id) == 0
    state = ElementState(nonce=9001, limit=page_limit(element_id))
    announced = reconcile_announcement(element_id, state, 9001, 100)
    assert announced.state.next_request_count == 0
    assert plan_page_merge(state, page(element_id)).outcome is PageOutcome.SKIP


def test_path_length_must_match_the_decoded_records() -> None:
    state = path_state(0, 10)
    plan = plan_page_merge(state, page(length=10, blocks=path_page(5)))
    assert plan.outcome is PageOutcome.SKIP
    assert plan.state == state


def test_malformed_record_headers_are_rejected() -> None:
    block = MapBlock(15, b"records")
    assert validate_page_content(15, (block,)) is not None
    with pytest.raises(RoborockException, match="shorter than 12"):
        element_record_count(15, (block,))
    partial_path = MapBlock(3, bytes(5), struct.pack("<III", 1, 4, 0))
    with pytest.raises(RoborockException, match="whole number"):
        count_path_points(partial_path)


@pytest.mark.parametrize(
    "result,count,outcome",
    [
        (0, None, PageOutcome.NO_RECORDS),
        (None, 0, PageOutcome.NO_RECORDS),
        (1, 0, PageOutcome.NO_RECORDS),
        (1, None, PageOutcome.RESET),
        (2, None, PageOutcome.SKIP),
    ],
)
def test_response_adapter_uses_the_shared_success_predicate(
    result: int | None, count: int | None, outcome: PageOutcome
) -> None:
    response = DynamicDataResponse.from_dict(
        {"result": result, "count": count, "data_id": 3, "nonce": 9001, "start": 0, "len": 0, "max_len": 10}
    )
    incoming = DynamicPage.from_data_response(response, (pose_block(),))
    assert plan_page_merge(path_state(0, 10), incoming).outcome is outcome


def test_inline_page_adapter_preserves_the_input_blocks() -> None:
    blocks = list(path_page(10, pose=True))
    encoded = encode_blocks(blocks)
    entry = DynamicMapDiffEntry.from_dict(
        {"count": 0, "nonce": 9001, "start": 0, "len": 10, "max_len": 10, "data": base64.b64encode(encoded).decode()}
    )
    decoded = parse_dynamic_value(entry.decoded_data or b"")
    incoming = DynamicPage.from_diff_entry(PATH_ELEMENT_ID, entry, decoded)
    plan = plan_page_merge(path_state(), incoming)

    assert plan.outcome is PageOutcome.APPEND
    assert plan.state.offset == 10
    assert encode_blocks(decoded) == encoded
    decoded.clear()
    assert incoming.blocks == tuple(blocks)
