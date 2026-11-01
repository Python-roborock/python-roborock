"""Tests for the V1 dynamic map diff wire models."""

import base64
from copy import deepcopy
from typing import Any

import pytest

from roborock.data.v1 import (
    DynamicDataResponse,
    DynamicMapDiffEntry,
    DynamicMapDiffResponse,
    DynamicMapResult,
    DynamicMapSnapshot,
    dynamic_data_params,
    dynamic_map_diff_params,
)
from roborock.exceptions import RoborockException

# A robot-pose block with zero coordinates and angle.
BLOCKS = bytes.fromhex("080008000c000000000000000000000000000000")
BLOCKS_B64 = base64.b64encode(BLOCKS).decode()

# The spec's example diff result, with an inline path page added to element 3.
DIFF_RESULT: dict[str, Any] = {
    "result": 0,
    "nonce": 123456,
    "diff": {
        "2": {"count": 7, "obstacle": 3, "space": 4},
        "3": {"count": 0, "nonce": 9001, "max_len": 1040, "start": 1000, "len": 40, "data": BLOCKS_B64},
        "15": {"count": 0, "nonce": 9002, "max_len": 2},
    },
    "robot_data": BLOCKS_B64,
}

DATA_RESULT: dict[str, Any] = {
    "result": 0,
    "nonce": 9001,
    "data_id": 3,
    "start": 1000,
    "len": 40,
    "max_len": 1040,
    "data": BLOCKS_B64,
}


@pytest.mark.parametrize(
    ("code", "expected"),
    [(1, DynamicMapResult.nonce_mismatch), (99, DynamicMapResult.unknown)],
    ids=["known-code", "unknown-code-falls-back"],
)
def test_result_codes_fall_back_to_unknown(code: int, expected: DynamicMapResult) -> None:
    """An unexpected firmware code becomes ``unknown`` rather than an error."""
    assert DynamicMapDiffResponse.from_dict({"result": code}).result is expected


# --- Diff response -----------------------------------------------------------


def test_diff_response_from_dict() -> None:
    """Element keys become ints, entries become typed, result becomes an enum."""
    original = deepcopy(DIFF_RESULT)
    response = DynamicMapDiffResponse.from_dict(DIFF_RESULT)
    assert DIFF_RESULT == original
    assert response.result is DynamicMapResult.ok
    assert response.nonce == 123456
    assert response.diff is not None
    assert set(response.diff) == {2, 3, 15}
    assert response.decoded_robot_data == BLOCKS

    image = response.diff[2]
    assert (image.count, image.obstacle, image.space) == (7, 3, 4)
    assert image.nonce is None
    assert not image.has_inline_page

    path = response.diff[3]
    assert (path.nonce, path.max_len) == (9001, 1040)
    assert path.has_inline_page
    assert path.is_success
    assert path.decoded_data == BLOCKS

    obstacles = response.diff[15]
    assert obstacles.nonce == 9002
    assert not obstacles.has_inline_page
    assert obstacles.decoded_data is None


@pytest.mark.parametrize(
    ("payload", "map_nonce", "expected"),
    [
        ({"result": 0, "nonce": 1, "diff": {}}, 1, True),
        ({"result": 0, "nonce": 1, "diff": {}}, 2, False),
        ({"result": 1, "nonce": 1, "diff": {}}, 1, False),
        ({"result": 0, "nonce": 1}, 1, False),
        ({"nonce": 1, "diff": {}}, 1, False),
    ],
    ids=["ok-match", "ok-other-map", "not-ok", "no-diff", "missing-result"],
)
def test_diff_response_is_for_map(payload: dict[str, Any], map_nonce: int, expected: bool) -> None:
    """Only ``result == 0`` with the cached nonce and a present ``diff`` is applicable."""
    assert DynamicMapDiffResponse.from_dict(payload).is_for_map(map_nonce) is expected


def test_diff_response_rejects_bad_base64() -> None:
    """Corrupt base64 surfaces as a library exception, not a binascii error."""
    response = DynamicMapDiffResponse.from_dict({"result": 0, "nonce": 1, "robot_data": "!!not base64!!"})
    with pytest.raises(RoborockException, match="robot_data"):
        _ = response.decoded_robot_data


@pytest.mark.parametrize("model", [DynamicMapDiffEntry, DynamicDataResponse])
@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({}, False),
        ({"result": 0}, True),
        ({"count": 0}, True),
        ({"result": 1, "count": 0}, True),
        ({"result": 0, "count": 1}, True),
        ({"result": 1, "count": 1}, False),
        ({"result": 99}, False),
    ],
)
def test_page_success_matches_app_handler(
    model: type[DynamicMapDiffEntry] | type[DynamicDataResponse], payload: dict[str, int], expected: bool
) -> None:
    """The app shares an OR predicate between inline entries and fetched pages."""
    assert model.from_dict(payload).is_success is expected


@pytest.mark.parametrize("encoded", ["+/8=", "-_8="], ids=["standard", "url-safe"])
def test_base64_alphabets_accepted_by_app(encoded: str) -> None:
    assert DynamicDataResponse(data=encoded).decoded_data == b"\xfb\xff"


@pytest.mark.parametrize("encoded", ["!!not base64!!", "\u00e9", "AAA"])
def test_page_rejects_malformed_base64(encoded: str) -> None:
    with pytest.raises(RoborockException, match="data"):
        _ = DynamicDataResponse(data=encoded).decoded_data


@pytest.mark.parametrize(
    ("response_nonce", "map_nonce", "expected"),
    [
        (-1, 0xFFFFFFFF, True),
        (0xFFFFFFFF, -1, True),
        (-(1 << 31), 1 << 31, True),
        (-1, 0, False),
        (1 << 32, 0, False),
        (0, 1 << 32, False),
    ],
)
def test_map_nonce_compares_32_bit_identity(response_nonce: int, map_nonce: int, expected: bool) -> None:
    """Binary and JSON nonces can use different signs for the same 32 bits."""
    response = DynamicMapDiffResponse.from_dict({"result": 0, "nonce": response_nonce, "diff": {}})
    assert response.is_for_map(map_nonce) is expected
    assert response.nonce == response_nonce


def test_full_refresh_response_retains_unknown_element_ids() -> None:
    """Real captures include result 2 and IDs outside the initial element table."""
    response = DynamicMapDiffResponse.from_dict(
        {"result": 2, "nonce": 10, "diff": {"41": {"nonce": 11, "count": 0, "max_len": 0, "future": 42}}}
    )
    assert response.result is DynamicMapResult.full_map_required
    assert not response.is_for_map(10)
    assert response.diff == {41: DynamicMapDiffEntry(nonce=11, count=0, max_len=0)}


# --- Data response -----------------------------------------------------------


def test_data_response_from_dict() -> None:
    """A normal page decodes with its range, total, and blocks."""
    response = DynamicDataResponse.from_dict(DATA_RESULT)
    assert response.is_success
    assert (response.nonce, response.data_id) == (9001, 3)
    assert (response.start, response.len, response.max_len) == (1000, 40, 1040)
    assert response.decoded_data == BLOCKS


def test_data_response_generation_mismatch() -> None:
    """A result 1 page is not a success even though it reports current metadata."""
    response = DynamicDataResponse.from_dict(
        {"result": 1, "nonce": 9005, "data_id": 3, "start": 0, "len": 0, "max_len": 12}
    )
    assert not response.is_success
    assert response.result is DynamicMapResult.nonce_mismatch
    assert response.nonce == 9005
    assert response.decoded_data is None


def test_empty_element_page_is_successful() -> None:
    """Captured empty-element responses carry an empty string, not absent data."""
    response = DynamicDataResponse.from_dict(
        {"result": 0, "nonce": 10, "data_id": 36, "start": 0, "len": 0, "max_len": 0, "data": ""}
    )
    assert response.is_success
    assert response.len == response.max_len == 0
    assert response.decoded_data == b""


@pytest.mark.parametrize("result", [0, 1])
def test_zero_length_page_retains_pose_blocks(result: int) -> None:
    """Captured zero-length and nonce-mismatch pages can still carry robot data."""
    response = DynamicDataResponse.from_dict(
        {"result": result, "nonce": 10, "data_id": 3, "start": 0, "len": 0, "max_len": 78, "data": BLOCKS_B64}
    )
    assert response.len == 0
    assert response.decoded_data == BLOCKS
    assert response.is_success is (result == 0)


def test_snapshot_from_dict() -> None:
    """Snapshot entries are keyed by element id and may carry a page limit."""
    snapshot = DynamicMapSnapshot.from_dict(
        {
            "nonce": 123456,
            "snapshot": {
                "3": {"nonce": 9001, "limit_len": 500},
                "15": {"nonce": 9002},
                "41": {"nonce": 9003, "limit_len": 16},
            },
        }
    )
    assert snapshot.nonce == 123456
    assert snapshot.snapshot is not None
    assert (snapshot.snapshot[3].nonce, snapshot.snapshot[3].limit_len) == (9001, 500)
    assert snapshot.snapshot[15].limit_len is None
    assert (snapshot.snapshot[41].nonce, snapshot.snapshot[41].limit_len) == (9003, 16)


# --- Request params ----------------------------------------------------------


def test_request_params_keep_the_device_snake_case_keys() -> None:
    """Params are built by hand because ``as_dict`` would camelize ``data_id``."""
    assert dynamic_map_diff_params(123456, 1793376000000) == {"nonce": 123456, "round": 1793376000000}
    assert dynamic_data_params(9001, 3, 1000, 40) == {"nonce": 9001, "data_id": 3, "start": 1000, "len": 40}
    assert dynamic_data_params(9001, 3, 1000, 0)["len"] == 0, "len 0 requests the remainder"


def test_round_marker_is_optional() -> None:
    """Captured nonce-mismatch queries succeed with no round marker."""
    assert dynamic_map_diff_params(0) == {"nonce": 0}
    assert dynamic_map_diff_params(0, 0) == {"nonce": 0, "round": 0}


@pytest.mark.parametrize("nonce", [0, -1, -(1 << 31), 0xFFFFFFFF])
def test_request_nonce_representation_is_preserved(nonce: int) -> None:
    """Accept either 32-bit representation without guessing a wire conversion."""
    assert dynamic_map_diff_params(nonce) == {"nonce": nonce}
    assert dynamic_data_params(nonce, 3, 0, 0) == {"nonce": nonce, "data_id": 3, "start": 0, "len": 0}


@pytest.mark.parametrize("nonce", [-(1 << 31) - 1, 1 << 32])
def test_request_nonce_outside_32_bits_is_rejected(nonce: int) -> None:
    with pytest.raises(ValueError, match="32-bit"):
        dynamic_map_diff_params(nonce)
    with pytest.raises(ValueError, match="32-bit"):
        dynamic_data_params(nonce, 3, 0, 0)


@pytest.mark.parametrize(
    ("args", "message"),
    [((1, 3, -1, 0), "nonnegative"), ((1, 3, 0, -1), "nonnegative"), ((1, 0, 0, 0), "positive")],
    ids=["negative-start", "negative-length", "zero-data-id"],
)
def test_dynamic_data_params_validation(args: tuple[int, int, int, int], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        dynamic_data_params(*args)
