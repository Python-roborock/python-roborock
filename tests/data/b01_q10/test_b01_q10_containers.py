"""Tests for Q10 data containers."""

import pytest

from roborock.data.b01_q10.b01_q10_containers import Q10RoborockPoint


@pytest.mark.parametrize(
    ("vector", "expected"),
    [
        ((0, 0), Q10RoborockPoint(25500, 25500)),
        ((10, 20), Q10RoborockPoint(25550, 25600)),
        ((-10, -20), Q10RoborockPoint(25450, 25400)),
    ],
)
def test_q10_roborock_point_vector_conversion(vector: tuple[int, int], expected: Q10RoborockPoint) -> None:
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
def test_q10_roborock_point_trace_conversion(trace: tuple[int, int], expected: Q10RoborockPoint) -> None:
    """Q10 trace coordinates convert to common millimetre coordinates."""
    assert Q10RoborockPoint.from_trace(*trace) == expected


@pytest.mark.parametrize(
    "point",
    [
        Q10RoborockPoint(25501, 25500),
        Q10RoborockPoint(-138345, 25500),
    ],
)
def test_q10_roborock_point_rejects_invalid_vector_coordinates(
    point: Q10RoborockPoint,
) -> None:
    """Outbound vector coordinates must fit the signed wire grid exactly."""
    with pytest.raises(ValueError):
        point.to_vector()
