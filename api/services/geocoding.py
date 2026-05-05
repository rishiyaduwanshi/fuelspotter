from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from django.core.cache import cache

from .http import HttpError, get_json


@dataclass(frozen=True)
class GeocodeResult:
    lat: float
    lon: float
    display_name: str


class GeocodingError(RuntimeError):
    pass


def _cache_key_for_query(query: str) -> str:
    digest = hashlib.sha256(query.lower().encode('utf-8')).hexdigest()
    return f"geocode:nominatim:us:{digest}"


def geocode_us_place(query: str, *, timeout_s: float = 10.0) -> GeocodeResult:
    query = (query or '').strip()
    if not query:
        raise GeocodingError('Empty location string')

    cache_key = _cache_key_for_query(query)
    cached = cache.get(cache_key)
    if cached:
        return GeocodeResult(**cached)

    url = 'https://nominatim.openstreetmap.org/search'
    params: dict[str, Any] = {
        'q': query,
        'format': 'json',
        'limit': 1,
        'addressdetails': 0,
        'countrycodes': 'us',
    }

    try:
        res = get_json(
            url,
            params=params,
            headers={
                # Nominatim requires a valid User-Agent.
                'User-Agent': 'fuelspotter-assignment/1.0 (contact: local-dev)',
            },
            timeout_s=timeout_s,
        )
    except HttpError as exc:
        raise GeocodingError(str(exc)) from exc

    if not isinstance(res.json, list) or not res.json:
        raise GeocodingError('No geocoding results found')

    top = res.json[0]
    try:
        result = GeocodeResult(
            lat=float(top['lat']),
            lon=float(top['lon']),
            display_name=str(top.get('display_name') or query),
        )
    except Exception as exc:
        raise GeocodingError('Unexpected geocoding response') from exc

    cache.set(cache_key, result.__dict__, timeout=60 * 60 * 24)
    return result
