import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import TruckStop


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


class Command(BaseCommand):
    help = 'Import truckstop fuel prices from fuelPrices.csv into the local DB.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            default=str(Path(settings.BASE_DIR) / 'fuelPrices.csv'),
            help='Path to fuelPrices.csv (default: BASE_DIR/fuelPrices.csv)',
        )
        parser.add_argument(
            '--no-clear',
            action='store_true',
            help='Do not delete existing TruckStop rows before import.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Optional max rows to read from CSV (0 = no limit).',
        )

    def handle(self, *args, **options):
        csv_path = Path(options['path'])
        no_clear = bool(options['no_clear'])
        limit = int(options['limit'] or 0)

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV not found: {csv_path}")

        self.stdout.write(f"Reading: {csv_path}")

        best_by_key: dict[TruckStopKey, Decimal] = {}

        with csv_path.open('r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                if limit and idx > limit:
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
            if not no_clear:
                TruckStop.objects.all().delete()

            created = 0
            batch_size = 1000
            for start in range(0, len(rows), batch_size):
                batch = rows[start : start + batch_size]
                TruckStop.objects.bulk_create(batch, ignore_conflicts=True)
                created += len(batch)

        self.stdout.write(self.style.SUCCESS(f"Imported ~{created} rows (deduped)."))
