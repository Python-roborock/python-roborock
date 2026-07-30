"""Deterministic room colors that keep adjacent segments distinguishable."""

from collections.abc import Callable, Sequence

from vacuum_map_parser_base.config.color import Color, ColorsPalette

RoomIdFromCell = Callable[[int], int | None]


def adjacency_aware_room_colors(
    grid: Sequence[int],
    width: int,
    palette: ColorsPalette,
    room_id_from_cell: RoomIdFromCell,
) -> dict[int, Color]:
    """Return room colors, changing only adjacent same-color conflicts.

    Room IDs remain the stable preference, matching the existing V1 palette.
    When two rooms sharing an edge resolve to the same RGB value, the
    higher-numbered room receives the first palette color not already used by
    one of its colored neighbors.
    """
    if width <= 0:
        return {}

    room_ids: set[int] = set()
    neighbors: dict[int, set[int]] = {}
    for index, value in enumerate(grid):
        room_id = room_id_from_cell(value)
        if room_id is None:
            continue
        room_ids.add(room_id)
        neighbors.setdefault(room_id, set())

        for neighbor_index in (index - 1 if index % width else -1, index - width):
            if neighbor_index < 0:
                continue
            neighbor_id = room_id_from_cell(grid[neighbor_index])
            if neighbor_id is None or neighbor_id == room_id:
                continue
            neighbors[room_id].add(neighbor_id)
            neighbors.setdefault(neighbor_id, set()).add(room_id)

    candidates: list[Color] = []
    for palette_id in map(int, ColorsPalette.ROOM_COLORS):
        color = palette.get_room_color(palette_id)
        if color not in candidates:
            candidates.append(color)

    assigned: dict[int, Color] = {}
    for room_id in sorted(room_ids):
        preferred = palette.get_room_color(room_id)
        neighbor_colors = {assigned[neighbor] for neighbor in neighbors[room_id] if neighbor in assigned}
        assigned[room_id] = (
            preferred
            if preferred not in neighbor_colors
            else next((color for color in candidates if color not in neighbor_colors), preferred)
        )
    return assigned
