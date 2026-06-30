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
from math import ceil

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
    flip: bool = True
    """Whether display rendering flips the grid top-to-bottom. Devices whose grid
    is stored bottom-up (V1/Q7 convention) flip; the Q10 grid is stored top-down,
    so it does not. Used as the default for the ``render_*`` methods so every
    layer matches the device's composited map orientation."""

    def cell_class(self, value: int) -> str:
        """Classify a single raw cell value into a canonical layer name."""
        return self.classifier(value)

    def render_mask(
        self,
        predicate: Callable[[int], bool],
        color: tuple[int, int, int, int],
        *,
        scale: int = 1,
        flip: bool | None = None,
    ) -> bytes:
        """Render cells matching ``predicate`` as ``color`` over transparency.

        ``flip`` applies the same top-to-bottom flip the composited map uses so
        layers line up pixel-for-pixel (defaults to the device's :attr:`flip`);
        ``scale`` nearest-neighbour upsamples.
        """
        if flip is None:
            flip = self.flip
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

    def render_class(
        self, layer: str, color: tuple[int, int, int, int], *, scale: int = 1, flip: bool | None = None
    ) -> bytes:
        """Render a whole class layer (e.g. ``"wall"``) to an RGBA PNG."""
        return self.render_mask(lambda v: self.classifier(v) == layer, color, scale=scale, flip=flip)

    def render_room(
        self, room_id: int, color: tuple[int, int, int, int], *, scale: int = 1, flip: bool | None = None
    ) -> bytes:
        """Render a single room's pixels to an RGBA PNG."""
        room = next((r for r in self.rooms if r.id == room_id), None)
        if room is None:
            raise KeyError(f"No room with id {room_id}")
        target = room.pixel_value
        return self.render_mask(lambda v: v == target, color, scale=scale, flip=flip)


@dataclass
class GridCalibration:
    """Affine transform between device world coordinates and grid pixels.

    ``resolution`` is world-units per pixel. The Y axis is flipped between world
    and grid space via ``y_sign`` (devices typically have world-Y increasing
    upward while the grid's Y increases downward).
    """

    resolution: float
    origin_x: float
    origin_y: float
    y_sign: int = 1

    def world_to_pixel(self, x: float, y: float) -> tuple[float, float]:
        """Map a world ``(x, y)`` to grid-pixel ``(px, py)``."""
        return (x / self.resolution + self.origin_x, self.origin_y - self.y_sign * y / self.resolution)

    def pixel_to_world(self, px: float, py: float) -> tuple[float, float]:
        """Map a grid-pixel ``(px, py)`` back to world ``(x, y)``."""
        return ((px - self.origin_x) * self.resolution, self.y_sign * (self.origin_y - py) * self.resolution)


def solve_calibration(
    layers: GridLayers,
    points: list[tuple[float, float]],
    *,
    resolutions: Iterable[float],
    y_signs: Iterable[int] = (1, -1),
) -> GridCalibration | None:
    """Fit a :class:`GridCalibration` by overlaying ``points`` onto the floor.

    A cleaning path must lie on floor (not walls/background). For each candidate
    resolution and Y orientation we slide the path's pixel bounding box across
    the map and keep the placement that maximises on-floor points while
    penalising points landing on walls/background. Returns ``None`` if no
    placement lands a clear majority of points on floor.

    The search is bounded: the path bbox size fixes how far it can slide, so the
    offset range is small. Needs a reasonably dense, shape-rich path (a long
    clean) to be well-constrained.
    """
    if not points:
        return None
    w, h = layers.width, layers.height
    classify = layers.classifier
    # 1 = floor, 2 = wall/background (blocked), 0 = other. Index by cell.
    klass = bytes(
        1 if (c := classify(v)) == LAYER_FLOOR else 2 if c in (LAYER_WALL, LAYER_BACKGROUND) else 0 for v in layers.grid
    )

    best: tuple[float, GridCalibration] | None = None
    for resolution in resolutions:
        if resolution <= 0:
            continue
        for y_sign in y_signs:
            sx = [x / resolution for x, _ in points]
            sy = [y_sign * y / resolution for _, y in points]
            min_sx, max_sx, min_sy, max_sy = min(sx), max(sx), min(sy), max(sy)
            if (max_sx - min_sx) >= w or (max_sy - min_sy) >= h:
                continue  # path wider/taller than the map at this resolution
            pts = list(zip(sx, sy))
            # Slide so every point stays in-bounds: px = px_f + ox in [0, w), py = oy - py_f in [0, h).
            for ox in range(ceil(-min_sx), ceil(w - max_sx)):
                for oy in range(ceil(max_sy), ceil(h + min_sy)):
                    on_floor = 0
                    blocked = 0
                    for px_f, py_f in pts:
                        cell = int(oy - py_f) * w + int(px_f + ox)
                        k = klass[cell]
                        if k == 1:
                            on_floor += 1
                        elif k == 2:
                            blocked += 1
                    score = on_floor - 1.5 * blocked
                    if best is None or score > best[0]:
                        best = (score, GridCalibration(float(resolution), float(ox), float(oy), y_sign))

    if best is None or best[0] < len(points) * 0.5:
        return None
    return best[1]


def solve_calibration_with_origin(
    layers: GridLayers,
    points: list[tuple[float, float]],
    origin: tuple[float, float],
    *,
    resolutions: Iterable[float],
    y_signs: Iterable[int] = (1, -1),
    min_on_floor: float = 0.5,
) -> GridCalibration | None:
    """Fit resolution + Y orientation around a *known* grid-pixel origin.

    Unlike :func:`solve_calibration`, the pixel origin ``(ox, oy)`` is fixed --
    e.g. read straight from the Q10 grid-frame header -- so this only sweeps the
    candidate ``resolutions`` and ``y_signs`` and keeps the placement landing the
    most ``points`` on floor. With the expensive 2-D offset slide gone, far fewer
    points are needed to confirm the fit, so it works from a short path rather
    than a dense clean. Returns ``None`` if no candidate lands a ``min_on_floor``
    fraction of points on floor (e.g. the origin or points are bogus).
    """
    if not points:
        return None
    w, h = layers.width, layers.height
    ox, oy = origin
    classify = layers.classifier
    # 1 = floor, 2 = wall/background (blocked), 0 = other. Index by cell.
    klass = bytes(
        1 if (c := classify(v)) == LAYER_FLOOR else 2 if c in (LAYER_WALL, LAYER_BACKGROUND) else 0 for v in layers.grid
    )

    best: tuple[float, GridCalibration] | None = None
    for resolution in resolutions:
        if resolution <= 0:
            continue
        for y_sign in y_signs:
            on_floor = 0
            blocked = 0
            for x, y in points:
                px = int(x / resolution + ox)
                py = int(oy - y_sign * y / resolution)
                if not (0 <= px < w and 0 <= py < h):
                    blocked += 1
                    continue
                k = klass[py * w + px]
                if k == 1:
                    on_floor += 1
                elif k == 2:
                    blocked += 1
            score = on_floor - 1.5 * blocked
            if best is None or score > best[0]:
                best = (score, GridCalibration(float(resolution), float(ox), float(oy), y_sign))

    if best is None or best[0] < len(points) * min_on_floor:
        return None
    return best[1]


def decompose_grid(
    width: int,
    height: int,
    grid: bytes,
    rooms: Iterable[tuple[int, str, int, int]],
    classifier: Callable[[int], str],
    *,
    flip: bool = True,
) -> GridLayers:
    """Build :class:`GridLayers` from a grid + room records + a classifier.

    ``rooms`` items are ``(id, name, pixel_value, pixel_count)`` tuples. Per-room
    bounding boxes are computed in one pass over the grid. ``flip`` records the
    device's display orientation (see :attr:`GridLayers.flip`).
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
        flip=flip,
    )
