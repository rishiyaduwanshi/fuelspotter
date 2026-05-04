import argparse
import csv
import os
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import django


@dataclass(frozen=True)
class TruckStopKey:
    opis_truckstop_id: int
    truckstop_name: str
    address: str
    city: str
    state: str
    rack_id: int | None


def _clean_str(value: str) -> str:
    return (value or '').strip()


def _parse_int(value: str) -> int | None:
    value = _clean_str(value)
    if not value:
        return None
    return int(value)


def _parse_price(value: str) -> Decimal:
    value = _clean_str(value)
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid price: {value!r}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description='Seed TruckStop prices from fuelPrices.csv')
    parser.add_argument(
        '--path',
        default=str(Path(__file__).resolve().parent.parent / 'fuelPrices.csv'),
        help='Path to fuelPrices.csv (default: project root/fuelPrices.csv)',
    )
    parser.add_argument(
        '--settings',
        default='fuelspotter.settings',
        help='Django settings module (default: fuelspotter.settings)',
    )
    parser.add_argument(
        '--no-clear',
        action='store_true',
        help='Do not delete existing rows before import.',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Optional max rows to read from CSV (0 = no limit).',
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', args.settings)
    django.setup()

    from django.db import transaction

    from api.models import TruckStop

    csv_path = Path(args.path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    best_by_key: dict[TruckStopKey, Decimal] = {}

    with csv_path.open('r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            if args.limit and idx > args.limit:
                break

            opis_id = _parse_int(row.get('OPIS Truckstop ID', ''))
            if opis_id is None:
                continue

            name = _clean_str(row.get('Truckstop Name', ''))
            address = _clean_str(row.get('Address', ''))
            city = _clean_str(row.get('City', ''))
            state = _clean_str(row.get('State', '')).upper()
            rack_id = _parse_int(row.get('Rack ID', ''))
            price = _parse_price(row.get('Retail Price', ''))

            if not (name and address and city and state):
                continue

            key = TruckStopKey(
                opis_truckstop_id=opis_id,
                truckstop_name=name,
                address=address,
                city=city,
                state=state,
                rack_id=rack_id,
            )

            existing = best_by_key.get(key)
            if existing is None or price < existing:
                best_by_key[key] = price

    rows = [
        TruckStop(
            opis_truckstop_id=key.opis_truckstop_id,
            truckstop_name=key.truckstop_name,
            address=key.address,
            city=key.city,
            state=key.state,
            rack_id=key.rack_id,
            retail_price=price,
        )
        for key, price in best_by_key.items()
    ]

    with transaction.atomic():
        if not args.no_clear:
            TruckStop.objects.all().delete()

        created = 0
        batch_size = 1000
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            TruckStop.objects.bulk_create(batch, ignore_conflicts=True)
            created += len(batch)

    print(f"Imported ~{created} rows (deduped).")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
