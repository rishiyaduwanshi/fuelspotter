from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Min

from api.models import TruckStop
from api.services.geo import LatLon, sample_linestring_every_miles
from api.services.geocoding import reverse_geocode_us
from api.services.optimizefuel import Station, optimize_fuel
from api.services.us_states import to_usps_state_code


MILES_PER_METER = 1.0 / 1609.344


@dataclass(frozen=True)
class CandidatePoint:
    distance_miles: float
    point: LatLon
    city: str | None
    state: str | None


class FuelPlanningError(RuntimeError):
    pass


def _state_code(state_value: str | None) -> str | None:
    return to_usps_state_code(state_value)


def build_state_profile_from_route(
    *,
    route_geometry: dict,
    sample_every_miles: float = 200.0,
) -> list[CandidatePoint]:
    coords = route_geometry.get('coordinates')
    if not isinstance(coords, list) or not coords:
        raise ValueError('Invalid route geometry')

    samples = sample_linestring_every_miles(coords, every_miles=sample_every_miles)

    points: list[CandidatePoint] = []
    for dist_miles, ll in samples:
        rev = reverse_geocode_us(ll.lat, ll.lon)
        points.append(
            CandidatePoint(
                distance_miles=float(dist_miles),
                point=ll,
                city=rev.city,
                state=_state_code(rev.state),
            )
        )

    # Keep order by distance and drop consecutive duplicates of state.
    points.sort(key=lambda p: p.distance_miles)
    compressed: list[CandidatePoint] = []
    last_state = None
    for p in points:
        if not compressed:
            compressed.append(p)
            last_state = p.state
            continue
        if p.state and p.state == last_state:
            continue
        compressed.append(p)
        last_state = p.state

    # Ensure we keep the final point.
    if points and compressed and compressed[-1].distance_miles != points[-1].distance_miles:
        compressed.append(points[-1])

    return compressed


def cheapest_station_per_state(states: list[str]) -> dict[str, TruckStop]:
    states = [s for s in states if s]
    if not states:
        return {}

    # Get min price per state.
    mins = (
        TruckStop.objects.filter(state__in=states)
        .values('state')
        .annotate(min_price=Min('retail_price'))
    )

    min_price_by_state: dict[str, Decimal] = {m['state']: m['min_price'] for m in mins}

    result: dict[str, TruckStop] = {}
    for state, min_price in min_price_by_state.items():
        st = (
            TruckStop.objects.filter(state=state, retail_price=min_price)
            .order_by('id')
            .first()
        )
        if st:
            result[state] = st

    return result


def plan_fuel_stops_for_route(
    *,
    route_distance_m: float,
    route_geometry: dict,
    tank_range_miles: float = 500.0,
    mpg: float = 10.0,
    start_fuel_miles: float = 0.0,
    sample_every_miles: float = 200.0,
) -> dict:
    total_distance_miles = float(route_distance_m) * MILES_PER_METER

    profile_points = build_state_profile_from_route(
        route_geometry=route_geometry,
        sample_every_miles=sample_every_miles,
    )

    states = [p.state for p in profile_points if p.state]
    station_by_state = cheapest_station_per_state(list(dict.fromkeys(states)))

    # Build stations list for optimization.
    stations: list[Station] = []
    for p in profile_points:
        if not p.state or p.state not in station_by_state:
            continue
        st = station_by_state[p.state]
        stations.append(Station(distance=p.distance_miles, price=float(st.retail_price)))

    # Ensure we have distance 0 station.
    if not stations or stations[0].distance > 0.0:
        if profile_points and profile_points[0].state and profile_points[0].state in station_by_state:
            st0 = station_by_state[profile_points[0].state]
            stations.insert(0, Station(distance=0.0, price=float(st0.retail_price)))
        else:
            raise FuelPlanningError('Could not determine starting fuel price')

    optimized = optimize_fuel(
        stations,
        total_distance_miles,
        tank_capacity_miles=tank_range_miles,
        mpg=mpg,
        start_fuel_miles=start_fuel_miles,
    )

    # Helper: find the latest profile point at/before a distance.
    def point_for_distance(d: float) -> CandidatePoint:
        last = profile_points[0]
        for p in profile_points:
            if p.distance_miles <= d + 1e-9:
                last = p
            else:
                break
        return last

    fuel_stops = []
    for idx, s in enumerate(optimized['stops'], start=1):
        d = float(s['at_distance_miles'])
        p = point_for_distance(d)
        state = p.state
        station = station_by_state.get(state) if state else None

        fuel_stops.append(
            {
                'stop_number': idx,
                'location': {
                    'city': p.city,
                    'state': state,
                    'lat': p.point.lat,
                    'lng': p.point.lon,
                },
                'station': {
                    'name': station.truckstop_name if station else None,
                    'address': station.address if station else None,
                    'price_per_gallon': float(station.retail_price) if station else None,
                },
                'fuel': {
                    'gallons_filled': float(s['gallons_filled']),
                    'cost': float(s['cost']),
                },
                'distance_from_start_miles': d,
            }
        )

    total_fuel_consumed_gallons = total_distance_miles / mpg

    return {
        'fuel_stops': fuel_stops,
        'summary': {
            'total_distance_miles': total_distance_miles,
            'total_fuel_consumed_gallons': total_fuel_consumed_gallons,
            'total_fuel_cost': float(optimized['total_cost']),
            'total_stops': len(fuel_stops),
            'vehicle': {
                'max_range_miles': tank_range_miles,
                'mileage_mpg': mpg,
            },
        },
    }
