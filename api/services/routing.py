from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from django.conf import settings
from django.core.cache import cache

from .http import HttpError, get_json


# distance_m = distance in meters 
# duration_s = duration in seconds 
# bbox = Bounding box ie. map area
@dataclass(frozen=True)
class RouteResult:
    distance_m: float
    duration_s: float
    geometry: dict[str, Any]
    bbox: list[float] | None


class RoutingError(RuntimeError):
    pass


def _route_cache_key(*, start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> str:
    raw = f"{start_lat:.6f},{start_lon:.6f}->{end_lat:.6f},{end_lon:.6f}"
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return f"route:osrm:driving:{digest}"

# lons = longitudes 
# lats = latutudes 
def _bbox_from_linestring(geometry: dict[str, Any]) -> list[float] | None:
    coords = geometry.get('coordinates')
    if not isinstance(coords, list) or not coords:
        return None
    try:
        lons = [float(p[0]) for p in coords]
        lats = [float(p[1]) for p in coords]
    except Exception:
        return None
    return [min(lons), min(lats), max(lons), max(lats)]


def osrm_route_driving(
    *,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    timeout_s: float = 15.0,
) -> RouteResult:
    base_url = getattr(settings, 'OSRM_BASE_URL', 'https://router.project-osrm.org')
    url = f"{base_url.rstrip('/')}/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"

    cache_key = _route_cache_key(
        start_lat=start_lat,
        start_lon=start_lon,
        end_lat=end_lat,
        end_lon=end_lon,
    )
    cached = cache.get(cache_key)
    if cached:
        return RouteResult(**cached)

    params = {
        'overview': 'full',
        'geometries': 'geojson',
        'steps': 'false',
        'annotations': 'false',
    }

    try:
        res = get_json(url, params=params, timeout_s=timeout_s)
    except HttpError as exc:
        raise RoutingError(str(exc)) from exc

    data = res.json
    if not isinstance(data, dict) or data.get('code') != 'Ok':
        raise RoutingError('OSRM routing failed')

    routes = data.get('routes') or []
    if not routes:
        raise RoutingError('No route found')

    route0 = routes[0]
    geometry = route0.get('geometry')
    if not isinstance(geometry, dict) or geometry.get('type') != 'LineString':
        raise RoutingError('Unexpected route geometry')

    result = RouteResult(
        distance_m=float(route0.get('distance') or 0.0),
        duration_s=float(route0.get('duration') or 0.0),
        geometry=geometry,
        bbox=_bbox_from_linestring(geometry),
    )

    cache.set(cache_key, result.__dict__, timeout=60 * 60 * 24)
    return result
