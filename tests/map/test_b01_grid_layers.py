"""Tests for the device-agnostic grid->layers decomposition + Q10 classifier."""

import io
from pathlib import Path

import pytest
from PIL import Image

from roborock.map.b01_grid_layers import (
    LAYER_BACKGROUND,
    LAYER_FLOOR,
    LAYER_WALL,
    decompose_grid,
)
from roborock.map.b01_q10_map_parser import (
    classify_q10_cell,
    decompose_layers,
    parse_map_packet,
)

FIXTURE = Path(__file__).resolve().parent / "testdata" / "b01_q10_map.bin"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "unknown"),
        (8, LAYER_FLOOR),
        (12, LAYER_FLOOR),
        (240, LAYER_FLOOR),
        (243, LAYER_BACKGROUND),
        (249, LAYER_WALL),
    ],
)
def test_classify_q10_cell(value: int, expected: str) -> None:
    assert classify_q10_cell(value) == expected


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


def test_decompose_layers_on_q10_fixture() -> None:
    """The Q10 synthetic fixture splits into floor + per-room layers."""
    layers = decompose_layers(parse_map_packet(FIXTURE.read_bytes()))
    assert layers.class_counts.get(LAYER_FLOOR) == 26
    names = {room.id: room.name for room in layers.rooms}
    assert names == {2: "Living Room", 3: "Bedroom"}
    # Each room renders to a valid PNG and only its own pixels are opaque.
    living = layers.render_room(2, (255, 0, 0, 255))
    img = Image.open(io.BytesIO(living))
    opaque = sum(1 for *_rgb, a in img.getdata() if a > 0)
    assert opaque == next(r.pixel_count for r in layers.rooms if r.id == 2)


def test_render_room_unknown_id_raises() -> None:
    layers = decompose_layers(parse_map_packet(FIXTURE.read_bytes()))
    with pytest.raises(KeyError):
        layers.render_room(999, (0, 0, 0, 255))
