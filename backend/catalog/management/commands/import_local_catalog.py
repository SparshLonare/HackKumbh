import csv
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import (
    DiagnosticTest,
    Lab,
    LabTestPrice,
    Pharmacy,
)


DATA_DIR = settings.BASE_DIR / "data"


def read_rows(filename):
    path = DATA_DIR / filename
    if not path.is_file():
        raise CommandError(f"Required CSV file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def as_bool(value, field_name):
    normalized = str(value).strip().lower()
    if normalized not in {"true", "false"}:
        raise CommandError(f"Invalid boolean for {field_name}: {value!r}")
    return normalized == "true"


def as_decimal(value, field_name):
    try:
        return Decimal(str(value).strip())
    except Exception as exc:
        raise CommandError(f"Invalid decimal for {field_name}: {value!r}") from exc


def require_unique_names(rows, filename):
    names = [row.get("name", "").strip() for row in rows]
    if any(not name for name in names):
        raise CommandError(f"{filename} contains a blank name")
    if len(names) != len(set(names)):
        raise CommandError(f"{filename} contains duplicate names")


class Command(BaseCommand):
    help = "Idempotently import the supplied sample pharmacy, lab, test and lab-price CSVs."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Validate files without writing rows.")

    def handle(self, *args, **options):
        pharmacies = read_rows("pharmacies.csv")
        labs = read_rows("labs.csv")
        tests = read_rows("tests.csv")
        prices = read_rows("lab_test_prices.csv")
        require_unique_names(pharmacies, "pharmacies.csv")
        require_unique_names(labs, "labs.csv")
        require_unique_names(tests, "tests.csv")

        lab_names = {row["name"].strip() for row in labs}
        test_names = {row["name"].strip() for row in tests}
        pairs = set()
        for row in prices:
            pair = (row.get("lab_name", "").strip(), row.get("test_name", "").strip())
            if pair[0] not in lab_names or pair[1] not in test_names:
                raise CommandError(f"Lab price references an unknown lab or test: {pair!r}")
            if pair in pairs:
                raise CommandError(f"lab_test_prices.csv contains a duplicate pair: {pair!r}")
            pairs.add(pair)
            as_decimal(row.get("price"), "price")
            try:
                if int(row.get("report_time_hours", "")) < 0:
                    raise ValueError
            except ValueError as exc:
                raise CommandError(f"Invalid report_time_hours for {pair!r}") from exc

        if options["dry_run"]:
            self.stdout.write(
                f"Validated sample CSVs: {len(pharmacies)} pharmacies, {len(labs)} labs, "
                f"{len(tests)} tests and {len(prices)} lab-test prices. No rows written."
            )
            return

        counts = {"pharmacies_created": 0, "pharmacies_updated": 0,
                  "labs_created": 0, "labs_updated": 0,
                  "tests_created": 0, "tests_updated": 0,
                  "prices_created": 0, "prices_updated": 0}
        with transaction.atomic():
            for row in pharmacies:
                name = row["name"].strip()
                _, created = Pharmacy.objects.update_or_create(
                    name=name,
                    defaults={
                        "type": row["type"].strip(),
                        "area": row["area"].strip(),
                        "address": row["address"].strip(),
                        "lat": as_decimal(row["lat"], "lat"),
                        "lng": as_decimal(row["lng"], "lng"),
                        "phone": row["phone"].strip(),
                        "hours": row["hours"].strip(),
                    },
                )
                counts["pharmacies_created" if created else "pharmacies_updated"] += 1

            for row in labs:
                name = row["name"].strip()
                _, created = Lab.objects.update_or_create(
                    name=name,
                    defaults={
                        "address": row["address"].strip(),
                        "lat": as_decimal(row["lat"], "lat"),
                        "lng": as_decimal(row["lng"], "lng"),
                        "phone": row["phone"].strip(),
                        "hours": row["hours"].strip(),
                        "nabl_accredited": as_bool(row["nabl_accredited"], "nabl_accredited"),
                        "home_collection": as_bool(row["home_collection"], "home_collection"),
                        "collection_fee": as_decimal(row["collection_fee"], "collection_fee"),
                    },
                )
                counts["labs_created" if created else "labs_updated"] += 1

            for row in tests:
                name = row["name"].strip()
                _, created = DiagnosticTest.objects.update_or_create(
                    name=name,
                    defaults={
                        "category": row["category"].strip(),
                        "aliases": row["aliases"].strip(),
                        "fasting_required": as_bool(row["fasting_required"], "fasting_required"),
                    },
                )
                counts["tests_created" if created else "tests_updated"] += 1

            lab_by_name = {item.name: item for item in Lab.objects.filter(name__in=lab_names)}
            test_by_name = {item.name: item for item in DiagnosticTest.objects.filter(name__in=test_names)}
            for row in prices:
                lab = lab_by_name[row["lab_name"].strip()]
                test = test_by_name[row["test_name"].strip()]
                _, created = LabTestPrice.objects.update_or_create(
                    lab=lab,
                    test=test,
                    defaults={
                        "price": as_decimal(row["price"], "price"),
                        "report_time_hours": int(row["report_time_hours"]),
                    },
                )
                counts["prices_created" if created else "prices_updated"] += 1

        self.stdout.write(self.style.SUCCESS("Sample catalog imported idempotently."))
        for name, count in counts.items():
            self.stdout.write(f"{name}: {count:,}")
        self.stdout.write("No pharmacy price rows were imported; no pharmacy price CSV was provided.")
