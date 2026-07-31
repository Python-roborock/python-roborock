"""Coordinate conversion helpers for Q10 B01 devices."""

# Q10 trace coordinates are relative to the dock and use 2.5 mm units. The
# public Roborock actions use millimetres with the dock at (25500, 25500).
ROBOROCK_COORDINATE_OFFSET = 25500
Q10_TRACE_UNIT_MM = 2.5
# Zone and restriction vectors use 5 mm units in the same dock-relative frame.
Q10_VECTOR_UNIT_MM = 5


def trace_to_roborock_coordinate(value: int) -> int:
    """Convert a Q10 trace value to the common Roborock coordinate space."""
    return round(ROBOROCK_COORDINATE_OFFSET + value * Q10_TRACE_UNIT_MM)


def roborock_to_vector_coordinate(value: int) -> int:
    """Convert a common Roborock coordinate to the Q10 vector format."""
    return round((value - ROBOROCK_COORDINATE_OFFSET) / Q10_VECTOR_UNIT_MM)
