"""Tests for the geometry of the massifs."""

import pytest

from meteofrance_montagne import in_massif

# A holed polygon and an island
MULTIPOLYGON = {
    "type": "MultiPolygon",
    "coordinates": [
        [
            [[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]],
            [[1.25, 1.25], [1.75, 1.25], [1.75, 1.75], [1.25, 1.75], [1.25, 1.25]],
        ],
        [[[5, 5], [7, 5], [7, 7], [5, 7], [5, 5]]],
    ],
}


@pytest.mark.parametrize(
    ("longitude", "latitude", "expected"),
    [(1.0, 1.0, True), (2.5, 1.0, False), (1.5, 1.5, False), (6.0, 6.0, True)],
    ids=["inside", "outside", "hole", "second_polygon"],
)
def test_in_massif(longitude, latitude, expected):
    """Find a point in a massif made of a holed polygon and an island."""
    assert in_massif(longitude, latitude, MULTIPOLYGON) is expected


def test_in_polygon():
    """Find a point in a massif made of a single polygon."""
    polygon = {"type": "Polygon", "coordinates": MULTIPOLYGON["coordinates"][0]}
    assert in_massif(1.0, 1.0, polygon) is True
    assert in_massif(1.5, 1.5, polygon) is False


def test_in_massif_without_geometry():
    """Find no station in a massif without geometry."""
    assert in_massif(1.0, 1.0, None) is False


def test_in_massif_without_position():
    """Find no station without position."""
    assert in_massif(None, 1.0, MULTIPOLYGON) is False
