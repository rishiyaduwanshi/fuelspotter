from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class LatLon:
    lat: float
    lon: float


def haversine_m(a: LatLon, b: LatLon) -> float:
    r = 6371000.0
    lat1 = math.radians(a.lat)
    lat2 = math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)

    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(h)))


def sample_linestring_every_miles(
    coordinates_lonlat: list[list[float]],
    *,
    every_miles: float,
) -> list[tuple[float, LatLon]]:
    """Return samples (distance_from_start_miles, LatLon) along the LineString.

    Coordinates are expected to be [[lon, lat], ...] (GeoJSON).
    """

    if every_miles <= 0:
        raise ValueError('every_miles must be > 0')

    if len(coordinates_lonlat) < 2:
        return [(0.0, LatLon(lat=coordinates_lonlat[0][1], lon=coordinates_lonlat[0][0]))]

    # Precompute cumulative distances along polyline.
    points = [LatLon(lat=float(p[1]), lon=float(p[0])) for p in coordinates_lonlat]
    cum_m = [0.0]
    for i in range(1, len(points)):
        cum_m.append(cum_m[-1] + haversine_m(points[i - 1], points[i]))

    total_m = cum_m[-1]
    if total_m <= 0:
        return [(0.0, points[0])]

    step_m = every_miles * 1609.344
    targets = [0.0]
    d = step_m
    while d < total_m:
        targets.append(d)
        d += step_m
    targets.append(total_m)

    samples: list[tuple[float, LatLon]] = []
    seg = 1
    for t in targets:
        while seg < len(cum_m) and cum_m[seg] < t:
            seg += 1
        if seg >= len(cum_m):
            samples.append((total_m / 1609.344, points[-1]))
            continue

        prev_m = cum_m[seg - 1]
        next_m = cum_m[seg]
        if next_m <= prev_m:
            frac = 0.0
        else:
            frac = (t - prev_m) / (next_m - prev_m)

        a = points[seg - 1]
        b = points[seg]
        lat = a.lat + (b.lat - a.lat) * frac
        lon = a.lon + (b.lon - a.lon) * frac

        samples.append((t / 1609.344, LatLon(lat=lat, lon=lon)))

    return samples
