"""Spherical geometry helpers. All distances in nautical miles."""

from __future__ import annotations

import math

EARTH_RADIUS_NM = 3440.065

Point = tuple[float, float]  # (lat, lon)


def haversine_nm(a: Point, b: Point) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_NM * math.asin(min(1.0, math.sqrt(h)))


def path_length_nm(points: list[Point]) -> float:
    return sum(haversine_nm(points[i], points[i + 1]) for i in range(len(points) - 1))


def bearing_deg(a: Point, b: Point) -> float:
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlon = math.radians(b[1] - a[1])
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def interpolate(a: Point, b: Point, fraction: float) -> Point:
    """Point along the great circle between a and b."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    d = haversine_nm(a, b) / EARTH_RADIUS_NM
    if d == 0:
        return a
    sd = math.sin(d)
    p = math.sin((1 - fraction) * d) / sd
    q = math.sin(fraction * d) / sd
    x = p * math.cos(lat1) * math.cos(lon1) + q * math.cos(lat2) * math.cos(lon2)
    y = p * math.cos(lat1) * math.sin(lon1) + q * math.cos(lat2) * math.sin(lon2)
    z = p * math.sin(lat1) + q * math.sin(lat2)
    return (
        math.degrees(math.atan2(z, math.sqrt(x * x + y * y))),
        math.degrees(math.atan2(y, x)),
    )


def densify(points: list[Point], step_nm: float = 250.0) -> list[Point]:
    """Insert intermediate points so a leg renders as a curve, not a straight line."""
    if len(points) < 2:
        return list(points)
    out: list[Point] = [points[0]]
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        legs = max(1, int(haversine_nm(a, b) // step_nm))
        for j in range(1, legs):
            out.append(interpolate(a, b, j / legs))
        out.append(b)
    return out


def offset_point(p: Point, bearing: float, distance_nm: float) -> Point:
    lat1, lon1 = math.radians(p[0]), math.radians(p[1])
    brg = math.radians(bearing)
    d = distance_nm / EARTH_RADIUS_NM
    lat2 = math.asin(math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(brg))
    lon2 = lon1 + math.atan2(
        math.sin(brg) * math.sin(d) * math.cos(lat1),
        math.cos(d) - math.sin(lat1) * math.sin(lat2),
    )
    lon2 = (lon2 + 3 * math.pi) % (2 * math.pi) - math.pi
    return (math.degrees(lat2), math.degrees(lon2))


def relative_angle(heading_deg: float, direction_deg: float) -> float:
    """Smallest angle (0-180) between a ship heading and a weather direction."""
    diff = abs((direction_deg - heading_deg + 180.0) % 360.0 - 180.0)
    return diff


def position_along_path(points: list[Point], travelled_nm: float) -> Point:
    """Where a vessel sits after travelling `travelled_nm` along a path."""
    if travelled_nm <= 0:
        return points[0]
    remaining = travelled_nm
    for i in range(len(points) - 1):
        leg = haversine_nm(points[i], points[i + 1])
        if remaining <= leg:
            return interpolate(points[i], points[i + 1], remaining / leg if leg else 0)
        remaining -= leg
    return points[-1]
