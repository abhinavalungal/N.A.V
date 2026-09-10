"""Routing service.

Builds plausible sea routes over a small waypoint network, then derives the
route variants the optimizer scores: fastest, fuel efficient, weather
optimized and eco slow steam.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..config import ROUTE_VARIANTS
from . import weather as weather_service
from .geo import (
    Point,
    bearing_deg,
    densify,
    haversine_nm,
    offset_point,
    path_length_nm,
)
from .ports import LANES, PORT_ENTRIES, PORTS, WAYPOINTS

LATERAL_OFFSET_NM = 110.0


@dataclass
class RouteCandidate:
    code: str
    label: str
    waypoints: list[Point]
    distance_nm: float
    speed_kn: float
    via: list[str] = field(default_factory=list)

    @property
    def geometry(self) -> list[list[float]]:
        """GeoJSON-style [lon, lat] pairs for MapLibre."""
        return [[round(lon, 4), round(lat, 4)] for lat, lon in self.waypoints]


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


def _graph() -> tuple[dict[str, Point], dict[str, list[str]]]:
    coords: dict[str, Point] = {name: w["coord"] for name, w in WAYPOINTS.items()}
    adj: dict[str, list[str]] = {name: [] for name in coords}
    for a, b in LANES:
        adj[a].append(b)
        adj[b].append(a)
    for port, entries in PORT_ENTRIES.items():
        node = f"PORT:{port}"
        coords[node] = PORTS[port]["coord"]
        adj[node] = list(entries)
        for e in entries:
            adj[e].append(node)
    return coords, adj


COORDS, ADJ = _graph()


def _attach(coord: Point, label: str) -> tuple[str, dict[str, Point], dict[str, list[str]]]:
    """Attach an arbitrary position to the network via its nearest waypoints."""
    coords = dict(COORDS)
    adj = {k: list(v) for k, v in ADJ.items()}
    node = f"POS:{label}"
    coords[node] = coord
    nearest = sorted(WAYPOINTS, key=lambda n: haversine_nm(coord, WAYPOINTS[n]["coord"]))[:3]
    adj[node] = nearest
    for n in nearest:
        adj[n].append(node)
    return node, coords, adj


def _resolve(point_or_port: Point | str, label: str):
    if isinstance(point_or_port, str) and point_or_port in PORTS:
        return f"PORT:{point_or_port}", dict(COORDS), {k: list(v) for k, v in ADJ.items()}
    coord = point_or_port if isinstance(point_or_port, tuple) else PORTS[point_or_port]["coord"]
    return _attach(coord, label)


def _dijkstra(start: str, goal: str, coords: dict[str, Point], adj: dict[str, list[str]]):
    dist = {start: 0.0}
    prev: dict[str, str] = {}
    queue: list[tuple[float, str]] = [(0.0, start)]
    seen: set[str] = set()
    while queue:
        d, node = heapq.heappop(queue)
        if node in seen:
            continue
        seen.add(node)
        if node == goal:
            break
        for nxt in adj.get(node, []):
            step = haversine_nm(coords[node], coords[nxt])
            nd = d + step
            if nd < dist.get(nxt, float("inf")):
                dist[nxt] = nd
                prev[nxt] = node
                heapq.heappush(queue, (nd, nxt))
    if goal not in dist:
        return None, None
    path = [goal]
    while path[-1] != start:
        path.append(prev[path[-1]])
    path.reverse()
    return path, dist[goal]


def sea_route(
    origin: Point | str,
    destination: Point | str,
) -> tuple[list[Point], list[str], float]:
    """Return (waypoints, via names, distance in NM)."""
    start, coords_a, adj_a = _resolve(origin, "origin")
    goal, coords_b, adj_b = _resolve(destination, "destination")

    # Merge the two temporary attachments into one graph.
    coords = {**coords_a, **coords_b}
    adj: dict[str, list[str]] = {k: list(v) for k, v in adj_a.items()}
    for k, v in adj_b.items():
        adj.setdefault(k, [])
        for n in v:
            if n not in adj[k]:
                adj[k].append(n)

    path, distance = _dijkstra(start, goal, coords, adj)
    if not path:
        a = coords[start]
        b = coords[goal]
        return [a, b], [], haversine_nm(a, b)

    points = [coords[n] for n in path]
    via = [n for n in path[1:-1] if not n.startswith(("PORT:", "POS:"))]
    return points, via, distance


# ---------------------------------------------------------------------------
# Route variants
# ---------------------------------------------------------------------------


def _is_chokepoint(p: Point) -> bool:
    for w in WAYPOINTS.values():
        if w["chokepoint"] and haversine_nm(p, w["coord"]) < 120.0:
            return True
    return False


def _weather_optimized_path(
    base: list[Point],
    mid_time: datetime,
) -> list[Point]:
    """Shift open-ocean waypoints laterally toward calmer water.

    One batched weather lookup evaluates three candidate positions per
    shiftable waypoint (port side, on track, starboard side).
    """
    if len(base) < 3:
        return list(base)

    trial: list[Point] = []
    index: list[tuple[int, int]] = []  # (waypoint index, candidate index)
    for i in range(1, len(base) - 1):
        if _is_chokepoint(base[i]):
            continue
        course = bearing_deg(base[i - 1], base[i + 1])
        for c, brg in enumerate(((course - 90) % 360, None, (course + 90) % 360)):
            p = base[i] if brg is None else offset_point(base[i], brg, LATERAL_OFFSET_NM)
            index.append((i, c))
            trial.append(p)
    if not trial:
        return list(base)

    provider = weather_service.get_provider()
    samples = provider.get_many(trial, mid_time)
    scores: dict[int, list[tuple[float, Point]]] = {}
    for (i, _c), point, sample in zip(index, trial, samples):
        scores.setdefault(i, []).append((weather_service.risk_index_for(sample), point))

    out = list(base)
    for i, candidates in scores.items():
        best_risk, best_point = min(candidates, key=lambda x: x[0])
        on_track = candidates[1][0] if len(candidates) > 1 else best_risk
        # Only divert when it buys a meaningful reduction in risk.
        if best_risk < on_track - 0.03:
            out[i] = best_point
    return out


def generate_routes(
    origin: Point | str,
    destination: Point | str,
    design_speed_kn: float,
    departure_utc: datetime,
    max_speed_kn: float | None = None,
    min_speed_kn: float | None = None,
) -> list[RouteCandidate]:
    """Produce the candidate routes the optimizer will score."""
    base_points, via, base_distance = sea_route(origin, destination)
    base_dense = densify(base_points, step_nm=300.0)

    nominal_hours = base_distance / max(1.0, design_speed_kn)
    mid_time = (departure_utc + timedelta(hours=nominal_hours / 2)).replace(microsecond=0)
    weather_points = _weather_optimized_path(base_points, mid_time)
    weather_dense = densify(weather_points, step_nm=300.0)
    weather_distance = path_length_nm(weather_points)

    candidates: list[RouteCandidate] = []
    for code, spec in ROUTE_VARIANTS.items():
        speed = design_speed_kn * float(spec["speed_factor"])
        if max_speed_kn:
            speed = min(speed, max_speed_kn)
        if min_speed_kn:
            speed = max(speed, min_speed_kn)
        if code == "WEATHER_OPTIMIZED":
            points, distance = weather_dense, weather_distance
        else:
            points, distance = base_dense, base_distance
        candidates.append(
            RouteCandidate(
                code=code,
                label=str(spec["label"]),
                waypoints=points,
                distance_nm=round(distance, 1),
                speed_kn=round(speed, 2),
                via=via,
            )
        )
    return candidates


def route_summary(candidate: RouteCandidate) -> dict:
    return {
        "code": candidate.code,
        "label": candidate.label,
        "distance_nm": candidate.distance_nm,
        "speed_kn": candidate.speed_kn,
        "via": candidate.via,
        "waypoint_count": len(candidate.waypoints),
    }
