"""Device-agnostic decomposition of a B01 occupancy grid into map layers.

Both the Q10 (custom binary) and Q7 (SCMap protobuf) deliver their map as a
single-byte-per-cell occupancy grid where the cell *value* encodes a semantic
class (background / wall / per-room floor / ...). This module turns such a grid
into separable **layers** a frontend can stack, without knowing the device's
specific value encoding -- the caller supplies a ``classifier`` mapping a cell
value to a class name, plus the room metadata.

Coordinates here are **grid-pixel** space (origin top-left of the raw grid, before
any rendering flip/scale). Vector overlays in world/robot coordinates (path,
zones, ...) are placed into this same space by the device's calibration.
"""

import io
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from PIL import Image

# Canonical layer class names. Devices map their raw cell values onto these.
LAYER_BACKGROUND = "background"
LAYER_WALL = "wall"
LAYER_FLOOR = "floor"
LAYER_UNKNOWN = "unknown"

_PNG = "PNG"


@dataclass
class RoomLayer:
    """A single room (segment) and where its pixels sit in the grid."""

    id: int
    name: str
    pixel_value: int
    pixel_count: int
    bbox: tuple[int, int, int, int]
    """Inclusive ``(min_x, min_y, max_x, max_y)`` bounding box in grid pixels."""

    @property
    def center(self) -> tuple[float, float]:
        """Center of the bounding box in grid-pixel space (for label placement)."""
        min_x, min_y, max_x, max_y = self.bbox
        return ((min_x + max_x) / 2, (min_y + max_y) / 2)


@dataclass
class GridLayers:
    """Separable layers decomposed from a single occupancy grid.

    Holds a reference to the raw ``grid`` plus the classifier, and renders any
    layer to a transparent RGBA PNG on demand (so we don't eagerly build a mask
    per room). ``class_counts`` reports how many cells fall in each class.
    """

    width: int
    height: int
    grid: bytes
    rooms: list[RoomLayer]
    classifier: Callable[[int], str]
    class_counts: dict[str, int] = field(default_factory=dict)

    def cell_class(self, value: int) -> str:
        """Classify a single raw cell value into a canonical layer name."""
        return self.classifier(value)

    def render_mask(
        self,
        predicate: Callable[[int], bool],
        color: tuple[int, int, int, int],
        *,
        scale: int = 1,
        flip: bool = True,
    ) -> bytes:
        """Render cells matching ``predicate`` as ``color`` over transparency.

        ``flip`` applies the same top-to-bottom flip the composited map uses so
        layers line up pixel-for-pixel; ``scale`` nearest-neighbour upsamples.
        """
        transparent = (0, 0, 0, 0)
        px = bytearray()
        for value in self.grid:
            px.extend(color if predicate(value) else transparent)
        img = Image.frombytes("RGBA", (self.width, self.height), bytes(px))
        if flip:
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        if scale > 1:
            img = img.resize((self.width * scale, self.height * scale), Image.Resampling.NEAREST)
        buf = io.BytesIO()
        img.save(buf, format=_PNG)
        return buf.getvalue()

    def render_class(self, layer: str, color: tuple[int, int, int, int], *, scale: int = 1, flip: bool = True) -> bytes:
        """Render a whole class layer (e.g. ``"wall"``) to an RGBA PNG."""
        return self.render_mask(lambda v: self.classifier(v) == layer, color, scale=scale, flip=flip)

    def render_room(
        self, room_id: int, color: tuple[int, int, int, int], *, scale: int = 1, flip: bool = True
    ) -> bytes:
        """Render a single room's pixels to an RGBA PNG."""
        room = next((r for r in self.rooms if r.id == room_id), None)
        if room is None:
            raise KeyError(f"No room with id {room_id}")
        target = room.pixel_value
        return self.render_mask(lambda v: v == target, color, scale=scale, flip=flip)


def decompose_grid(
    width: int,
    height: int,
    grid: bytes,
    rooms: Iterable[tuple[int, str, int, int]],
    classifier: Callable[[int], str],
) -> GridLayers:
    """Build :class:`GridLayers` from a grid + room records + a classifier.

    ``rooms`` items are ``(id, name, pixel_value, pixel_count)`` tuples. Per-room
    bounding boxes are computed in one pass over the grid.
    """
    room_meta = list(rooms)
    bboxes: dict[int, list[int]] = {pv: [width, height, -1, -1] for (_, _, pv, _) in room_meta}
    counts: dict[str, int] = {}
    for index, value in enumerate(grid):
        cls = classifier(value)
        counts[cls] = counts.get(cls, 0) + 1
        box = bboxes.get(value)
        if box is not None:
            x = index % width
            y = index // width
            if x < box[0]:
                box[0] = x
            if y < box[1]:
                box[1] = y
            if x > box[2]:
                box[2] = x
            if y > box[3]:
                box[3] = y

    room_layers: list[RoomLayer] = []
    for room_id, name, pixel_value, pixel_count in room_meta:
        box = bboxes[pixel_value]
        bbox = (box[0], box[1], box[2], box[3]) if box[2] >= 0 else (0, 0, 0, 0)
        room_layers.append(
            RoomLayer(id=room_id, name=name, pixel_value=pixel_value, pixel_count=pixel_count, bbox=bbox)
        )

    return GridLayers(
        width=width,
        height=height,
        grid=grid,
        rooms=room_layers,
        classifier=classifier,
        class_counts=counts,
    )
