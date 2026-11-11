"""Massifs of the avalanche bulletins."""

import logging
from typing import Any

from .models import Massif

_LOGGER = logging.getLogger(__name__)


def organize_by_department(json_data: dict[str, Any]) -> dict[str, list[Massif]]:
    """Organize the massifs of /liste-massifs by department."""
    department_map: dict[str, list[Massif]] = {}

    for feature in json_data["features"]:
        properties = feature["properties"]

        # Debug log if needed
        if not department_map:  # Log only for the first one
            _LOGGER.debug("Properties keys: %s", list(properties.keys()))

        if (code := properties.get("code")) is None:
            continue
        massif = Massif(
            code=int(code),
            nom=properties.get("title") or str(code),
            geometry=feature.get("geometry"),
        )

        # Try different key name variants, a massif may be on two departments
        for dep in (
            properties.get("Departemen")
            or properties.get("departement")
            or properties.get("Departement"),
            properties.get("Dep2")
            or properties.get("dep2")
            or properties.get("Departement2"),
        ):
            if dep:
                department_map.setdefault(dep, []).append(massif)

    return department_map


def _in_ring(longitude: float, latitude: float, ring: list[list[float]]) -> bool:
    """Return whether a point is inside a ring, by ray casting."""
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=True):
        if (y1 > latitude) != (y2 > latitude) and (
            longitude < (x2 - x1) * (latitude - y1) / (y2 - y1) + x1
        ):
            inside = not inside
    return inside


def in_massif(
    longitude: float | None, latitude: float | None, geometry: dict[str, Any] | None
) -> bool:
    """Return whether a point is inside the (Multi)Polygon of a massif."""
    if not geometry or longitude is None or latitude is None:
        return False
    polygons = geometry.get("coordinates") or []
    if geometry.get("type") == "Polygon":
        polygons = [polygons]
    return any(
        polygon
        and _in_ring(longitude, latitude, polygon[0])
        and not any(_in_ring(longitude, latitude, hole) for hole in polygon[1:])
        for polygon in polygons
    )
