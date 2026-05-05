from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Station:
    distance: float  # miles from start
    price: float  # price per gallon


@dataclass(frozen=True)
class Stop:
    at_distance: float  # miles from start
    fuel_added_miles: float  # how many miles worth of fuel added
    cost: float


# Core Algorithm
def optimize_fuel(
    stations: list[Station],
    total_distance_miles: float,
    *,
    tank_capacity_miles: float = 500.0,
    mpg: float = 10.0,
    start_fuel_miles: float = 0.0,
) -> dict[str, Any]:
    """
    ASSUMPTIONS:

     Stations are already mapped to the route (no geospatial filtering here) - can be extended later.
     Vehicle starts at distance = 0 with 'start_fuel' miles of fuel.
     Starting fuel price is approximated using the first station's price.
     Fuel is always available at every station (no outages).
     Tank capacity is fixed (default = 500 miles range) - given in assignment.
     Mileage is constant (default = 10 mpg) - given in assignment.
     Destination is treated as a virtual station to simplify logic
     
    """


    if total_distance_miles <= 0:
        return {"total_cost": 0.0, "stops": []}

    if tank_capacity_miles <= 0 or mpg <= 0:
        raise ValueError('Invalid tank capacity or mpg')
      
    stations_sorted = sorted(stations, key=lambda s: s.distance)

    # Ensure a start station exists at distance 0.
    if not stations_sorted or stations_sorted[0].distance > 0:
        raise ValueError('First station must be at distance 0')

    # Add destination as a virtual station (price irrelevant).
    stations_sorted = stations_sorted + [Station(distance=total_distance_miles, price=0.0)]

    current_index = 0
    current_pos = 0.0
    fuel_left = float(start_fuel_miles)
    total_cost = 0.0
    stops: list[Stop] = []

    while current_pos < total_distance_miles:
        current_price = stations_sorted[current_index].price

        # Find the farthest reachable station.
        farthest_index = current_index
        for j in range(current_index + 1, len(stations_sorted)):
            if stations_sorted[j].distance - current_pos <= tank_capacity_miles + 1e-9:
                farthest_index = j
            else:
                break

        if farthest_index == current_index:
            raise RuntimeError('Trip impossible: no reachable station within tank range')

        # Find next cheaper station within reach.
        next_cheaper_index: int | None = None
        for j in range(current_index + 1, farthest_index + 1):
            if stations_sorted[j].price < current_price:
                next_cheaper_index = j
                break

        if next_cheaper_index is not None:
            target_index = next_cheaper_index
            dist_to_target = stations_sorted[target_index].distance - current_pos
            desired_fuel = dist_to_target
        else:
            # No cheaper station ahead in range: fill up and go as far as possible.
            target_index = farthest_index
            desired_fuel = tank_capacity_miles

        if fuel_left < desired_fuel - 1e-9:
            fuel_to_buy = desired_fuel - fuel_left
            gallons = fuel_to_buy / mpg
            cost = gallons * current_price
            total_cost += cost
            fuel_left += fuel_to_buy

            stops.append(
                Stop(
                    at_distance=current_pos,
                    fuel_added_miles=fuel_to_buy,
                    cost=cost,
                )
            )

        # Travel to target.
        travel = stations_sorted[target_index].distance - current_pos
        fuel_left -= travel
        current_pos = stations_sorted[target_index].distance
        current_index = target_index

    return {
        'total_cost': float(total_cost),
        'stops': [
            {
                'at_distance_miles': float(s.at_distance),
                'fuel_added_miles': float(s.fuel_added_miles),
                'gallons_filled': float(s.fuel_added_miles / mpg),
                'cost': float(s.cost),
            }
            for s in stops
            if s.at_distance < total_distance_miles
        ],
    }
