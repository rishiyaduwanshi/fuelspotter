from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from django.core.cache import cache

from .http import HttpError, get_json
from .us_states import to_usps_state_code


@dataclass(frozen=True)
class GeocodeResult:
    lat: float
    lon: float
    display_name: str


@dataclass(frozen=True)
class ReverseGeocodeResult:
    city: str | None
    state: str | None


class GeocodingError(RuntimeError):
    pass


def _cache_key_for_query(query: str) -> str:
    digest = hashlib.sha256(query.lower().encode('utf-8')).hexdigest()
    return f"geocode:nominatim:us:{digest}"


def _cache_key_for_reverse(lat: float, lon: float) -> str:
    raw = f"{lat:.5f},{lon:.5f}"
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return f"revgeocode:nominatim:us:{digest}"


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


def reverse_geocode_us(lat: float, lon: float, *, timeout_s: float = 10.0) -> ReverseGeocodeResult:
    cache_key = _cache_key_for_reverse(lat, lon)
    cached = cache.get(cache_key)
    if cached:
        return ReverseGeocodeResult(**cached)

    url = 'https://nominatim.openstreetmap.org/reverse'
    params: dict[str, Any] = {
        'lat': lat,
        'lon': lon,
        'format': 'json',
        'zoom': 10,
        'addressdetails': 1,
        'countrycodes': 'us',
    }

    try:
        res = get_json(
            url,
            params=params,
            headers={
                'User-Agent': 'fuelspotter-assignment/1.0 (contact: local-dev)',
            },
            timeout_s=timeout_s,
        )
    except HttpError as exc:
        raise GeocodingError(str(exc)) from exc

    data = res.json
    address = data.get('address') if isinstance(data, dict) else None
    if not isinstance(address, dict):
        raise GeocodingError('Unexpected reverse geocoding response')

    # Prefer USPS 2-letter state code.
    state = address.get('state_code')
    if not state:
        # Some responses use ISO3166-2 keys like "US-TX".
        for iso_key in ('ISO3166-2-lvl4', 'ISO3166-2-lvl5', 'ISO3166-2-lvl6'):
            iso_val = address.get(iso_key)
            if isinstance(iso_val, str) and iso_val:
                state = iso_val
                break
    if not state:
        state = address.get('state')

    state_code = to_usps_state_code(state) if isinstance(state, str) else None

    city = address.get('city') or address.get('town') or address.get('village')

    result = ReverseGeocodeResult(
        city=str(city) if city else None,
        state=state_code,
    )
    cache.set(cache_key, result.__dict__, timeout=60 * 60 * 24)
    return result
