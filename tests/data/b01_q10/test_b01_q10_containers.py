"""Tests for B01 Q10 data containers."""

from typing import Any

import pytest

from roborock.data.b01_q10.b01_q10_containers import Q10RoborockPoint


@pytest.mark.parametrize(
    ("vector", "roborock"),
    [
        ((0, 0), (25_500, 25_500)),
        ((-1682, -1595), (17_090, 17_525)),
        ((932, -925), (30_160, 20_875)),
        ((-32_768, 32_767), (-138_340, 189_335)),
        ((32_767, -32_768), (189_335, -138_340)),
    ],
)
def test_q10_roborock_point_conversion_round_trip(vector: tuple[int, int], roborock: tuple[int, int]) -> None:
    """Vector coordinates round-trip at the full signed-int16 boundaries."""
    point = Q10RoborockPoint.from_vector(*vector)

    assert (point.x, point.y) == roborock
    assert point.to_vector() == vector


@pytest.mark.parametrize(
    ("x", "y"),
    [
        (True, 0),
        (0, False),
        (1.0, 0),
        (0, 1.0),
        ("1", 0),
        (0, "1"),
        (-32_769, 0),
        (0, 32_768),
    ],
)
def test_q10_roborock_point_from_vector_rejects_invalid_coordinates(x: Any, y: Any) -> None:
    """Wire vectors must be real integers inside the signed-int16 range."""
    with pytest.raises(ValueError, match="coordinates"):
        Q10RoborockPoint.from_vector(x, y)


@pytest.mark.parametrize(
    ("x", "y", "message"),
    [
        (True, 25_500, "integers"),
        (25_500, False, "integers"),
        (25_500.0, 25_500, "integers"),
        (25_500, "25500", "integers"),
        (25_501, 25_500, "5 mm grid"),
        (25_500, 25_499, "5 mm grid"),
        (-138_345, 25_500, "outside"),
        (25_500, 189_340, "outside"),
    ],
)
def test_q10_roborock_point_to_vector_rejects_invalid_coordinates(x: Any, y: Any, message: str) -> None:
    """Common coordinates must be aligned and encodable without wrapping."""
    with pytest.raises(ValueError, match=message):
        Q10RoborockPoint(x, y).to_vector()


@pytest.mark.parametrize(
    ("vector", "expected"),
    [
        ((0, 0), Q10RoborockPoint(25500, 25500)),
        ((10, 20), Q10RoborockPoint(25550, 25600)),
        ((-10, -20), Q10RoborockPoint(25450, 25400)),
    ],
)
def test_upstream_q10_roborock_point_vector_conversion(vector: tuple[int, int], expected: Q10RoborockPoint) -> None:
    """Q10 vector conversion is reversible on the device's 5 mm grid."""
    point = Q10RoborockPoint.from_vector(*vector)

    assert point == expected
    assert point.to_vector() == vector


@pytest.mark.parametrize(
    ("trace", "expected"),
    [
        ((0, 0), Q10RoborockPoint(25500, 25500)),
        ((276, -1), Q10RoborockPoint(26190, 25498)),
        ((-1700, -800), Q10RoborockPoint(21250, 23500)),
    ],
)
def test_upstream_q10_roborock_point_trace_conversion(trace: tuple[int, int], expected: Q10RoborockPoint) -> None:
    """Q10 trace coordinates convert to common millimetre coordinates."""
    assert Q10RoborockPoint.from_trace(*trace) == expected


@pytest.mark.parametrize(
    "point",
    [
        Q10RoborockPoint(25501, 25500),
        Q10RoborockPoint(-138345, 25500),
    ],
)
def test_upstream_q10_roborock_point_rejects_invalid_vector_coordinates(
    point: Q10RoborockPoint,
) -> None:
    """Outbound vector coordinates must fit the signed wire grid exactly."""
    with pytest.raises(ValueError):
        point.to_vector()
