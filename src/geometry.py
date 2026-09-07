"""
src/geometry.py
---------------
Geospatial helpers for hospital directory distance calculations.

Used by api/main.py to compute great-circle distances between the
requesting user's current location and hospital facilities.
"""

from __future__ import annotations

import math
from typing import Optional


# ---------------------------------------------------------------------------
# Great-circle distance helpers
# ---------------------------------------------------------------------------

EARTH_RADIUS_KM = 6371.0


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Return the great-circle distance in kilometres between two coordinates.

    Uses the haversine formula which assumes a spherical Earth.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def distance_km_between(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> Optional[float]:
    """Return rounded distance in km, or None when any coordinate is missing."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    return round(haversine_distance(lat1, lon1, lat2, lon2), 2)