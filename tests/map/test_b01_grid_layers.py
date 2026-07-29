"""Tests for the device-agnostic grid-to-layers decomposition."""

import io

import pytest
from PIL import Image

from roborock.map.b01_grid_layers import (
    LAYER_BACKGROUND,
    LAYER_FLOOR,
    LAYER_WALL,
    GridCalibration,
    decompose_grid,
    solve_calibration,
    solve_calibration_with_origin,
)


def test_decompose_grid_generic_classifier_and_bbox() -> None:
    """A hand-built grid decomposes into the right classes with room bboxes."""
    # 4x3 grid: row0 walls(9), row1 = floor room 5 (value 20) at x1..2, row2 background(7)
    grid = bytes(
        [
            9,
            9,
            9,
            9,
            0,
            20,
            20,
            0,
            7,
            7,
            7,
            7,
        ]
    )

    def classify(v: int) -> str:
        if v == 9:
            return LAYER_WALL
        if v == 7:
            return LAYER_BACKGROUND
        if v == 0:
            return "unknown"
        return LAYER_FLOOR

    layers = decompose_grid(4, 3, grid, [(5, "Office", 20, 2)], classify)
    assert layers.class_counts == {LAYER_WALL: 4, "unknown": 2, LAYER_FLOOR: 2, LAYER_BACKGROUND: 4}
    assert len(layers.rooms) == 1
    room = layers.rooms[0]
    assert room.id == 5 and room.name == "Office" and room.pixel_value == 20
    assert room.bbox == (1, 1, 2, 1)  # the two floor cells, row 1, x in 1..2
    assert room.center == (1.5, 1.0)


def test_render_mask_produces_transparent_rgba() -> None:
    grid = bytes([0, 20, 20, 0])

    def classify(v: int) -> str:
        return LAYER_FLOOR if v == 20 else "unknown"

    layers = decompose_grid(4, 1, grid, [(5, "Office", 20, 2)], classify)
    png = layers.render_class(LAYER_FLOOR, (10, 20, 30, 255), flip=False)
    img = Image.open(io.BytesIO(png))
    assert img.mode == "RGBA" and img.size == (4, 1)
    pixels = list(img.getdata())
    assert pixels == [(0, 0, 0, 0), (10, 20, 30, 255), (10, 20, 30, 255), (0, 0, 0, 0)]


def test_render_scale_upsamples() -> None:
    layers = decompose_grid(2, 1, bytes([20, 20]), [(5, "R", 20, 2)], lambda v: LAYER_FLOOR)
    png = layers.render_class(LAYER_FLOOR, (1, 2, 3, 4), scale=3)
    assert Image.open(io.BytesIO(png)).size == (6, 3)


def test_render_room_unknown_id_raises() -> None:
    layers = decompose_grid(1, 1, b"\x01", [(1, "Room", 1, 1)], lambda _: LAYER_FLOOR)
    with pytest.raises(KeyError):
        layers.render_room(999, (0, 0, 0, 255))


def test_calibration_roundtrip() -> None:
    cal = GridCalibration(resolution=2.0, origin_x=3.0, origin_y=8.0, y_sign=1)
    assert cal.world_to_pixel(0, 0) == (3.0, 8.0)
    assert cal.world_to_pixel(10, 10) == (8.0, 3.0)  # +x right, +y up (flipped)
    back = cal.pixel_to_world(*cal.world_to_pixel(6, -4))
    assert back == (6, -4)


def _floor_block_layers():
    """12x12 grid with a 6x6 floor block at x[3..8], y[3..8]; rest background."""
    grid = bytearray([9] * 144)  # 9 = background
    for y in range(3, 9):
        for x in range(3, 9):
            grid[y * 12 + x] = 1  # 1 = floor
    classify = {1: LAYER_FLOOR, 9: LAYER_BACKGROUND}
    return decompose_grid(12, 12, bytes(grid), [], lambda v: classify.get(v, "other"))


def test_solve_calibration_recovers_known_transform() -> None:
    """A 2D-spread path over a floor block pins resolution + origin uniquely."""
    layers = _floor_block_layers()
    true = GridCalibration(2.0, 3.0, 8.0, 1)
    # World points chosen to land across the floor block (2D spread, not 1D).
    pixels = [(3, 8), (8, 8), (3, 3), (8, 3), (5, 5), (6, 6), (4, 7), (7, 4)]
    points = [true.pixel_to_world(px, py) for px, py in pixels]
    cal = solve_calibration(layers, points, resolutions=[1.0, 1.5, 2.0, 2.5, 3.0])
    assert cal is not None
    assert cal.resolution == 2.0
    assert (cal.origin_x, cal.origin_y, cal.y_sign) == (3.0, 8.0, 1)


def test_solve_calibration_considers_right_edge_fit() -> None:
    """A valid placement is not skipped when the path bbox reaches the map edge."""
    layers = decompose_grid(4, 2, bytes([1] * 8), [], lambda v: LAYER_FLOOR)
    points = [(0.0, 0.0), (3.2, 0.0), (6.4, 0.0)]
    cal = solve_calibration(layers, points, resolutions=[2.0], y_signs=[1])
    assert cal is not None
    assert (cal.origin_x, cal.origin_y, cal.y_sign) == (0.0, 0.0, 1)


def test_solve_calibration_returns_none_when_unfittable() -> None:
    layers = _floor_block_layers()
    # Points so far apart no resolution keeps them on the 6x6 floor block.
    points = [(0.0, 0.0), (1000.0, 0.0), (0.0, 1000.0)]
    assert solve_calibration(layers, points, resolutions=[2.0]) is None


def test_solve_calibration_with_origin_fits_resolution_from_short_path() -> None:
    """With a known origin only resolution is fit, so a tiny path suffices."""
    layers = _floor_block_layers()
    true = GridCalibration(2.0, 3.0, 8.0, 1)
    points = [true.pixel_to_world(px, py) for px, py in [(4, 7), (6, 5)]]  # two points
    cal = solve_calibration_with_origin(layers, points, (true.origin_x, true.origin_y), resolutions=[1.0, 2.0, 3.0])
    assert cal is not None
    assert (cal.resolution, cal.origin_x, cal.origin_y, cal.y_sign) == (2.0, 3.0, 8.0, 1)


def test_solve_calibration_with_origin_returns_none_off_floor() -> None:
    """A wrong origin that lands the path off floor is rejected, not forced."""
    layers = _floor_block_layers()
    true = GridCalibration(2.0, 3.0, 8.0, 1)
    points = [true.pixel_to_world(px, py) for px, py in [(4, 7), (6, 5)]]
    # Origin shoved into the background corner: every point lands off floor.
    assert solve_calibration_with_origin(layers, points, (0.0, 0.0), resolutions=[2.0]) is None


def test_solve_calibration_with_origin_returns_none_without_points() -> None:
    layers = _floor_block_layers()
    assert solve_calibration_with_origin(layers, [], (3.0, 8.0), resolutions=[2.0]) is None
