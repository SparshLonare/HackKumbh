from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
import re

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Medicine, PharmacyPrice


CSV_PATH = settings.BASE_DIR / "data" / "clean" / "medicines_clean.csv"
GROUP_COLUMNS = ["salt_key", "form", "form_variant"]
MAX_ROWS = 20_000
BATCH_SIZE = 2_000
MODEL_FIELDS = (
    "name",
    "manufacturer",
    "mrp",
    "pack_size_label",
    "pack_units",
    "unit_type",
    "form",
    "form_variant",
    "pack_volume",
    "salt_1",
    "salt_2",
    "salt_key",
    "price_per_unit",
    "composition_incomplete",
    "is_comparable",
)
BRANDS = (
    "Dolo 650",
    "Crocin",
    "Augmentin 625",
    "Pan 40",
    "Glycomet",
    "Telma 40",
    "Azithral 500",
    "Cetzine",
)


def as_bool(value):
    return value is True or str(value).strip().lower() == "true"


def as_string(value, default=""):
    return default if pd.isna(value) else str(value).strip()


def as_decimal(value):
    if pd.isna(value) or str(value).strip() == "":
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def as_integer(value):
    if pd.isna(value) or str(value).strip() == "":
        return None
    number = Decimal(str(value))
    if number != number.to_integral_value():
        raise ValueError(f"Expected an integer pack_units value, received {value!r}")
    return int(number)


class Command(BaseCommand):
    help = "Import comparable medicines from the cleaned CSV without duplicating existing rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the import action without changing the database.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Replace the medicine catalog if it differs from this CSV.",
        )

    def handle(self, *args, **options):
        if not CSV_PATH.is_file():
            raise CommandError(f"Cleaned medicines CSV not found: {CSV_PATH}")

        data = pd.read_csv(CSV_PATH, encoding="utf-8")
        self.stdout.write(f"CSV rows: {len(data):,}")

        comparable = data.loc[data["is_comparable"].map(as_bool)].copy()
        self.stdout.write(f"is_comparable=True rows: {len(comparable):,}")

        for column in GROUP_COLUMNS:
            comparable[column] = comparable[column].fillna("").astype(str)

        group_sizes = comparable.groupby(GROUP_COLUMNS, sort=False, dropna=False).size()
        repeated_sizes = group_sizes[group_sizes >= 2]
        size_by_key = {tuple(key): int(size) for key, size in repeated_sizes.items()}
        comparable["_group_key"] = list(
            zip(*(comparable[column] for column in GROUP_COLUMNS))
        )
        comparable["_group_size"] = comparable["_group_key"].map(size_by_key)
        eligible = comparable.loc[comparable["_group_size"].notna()].copy()
        self.stdout.write(
            f"Rows in groups with 2+ comparable members: {len(eligible):,} "
            f"across {len(repeated_sizes):,} groups"
        )

        brand_mask = pd.Series(False, index=eligible.index)
        names = eligible["name"].astype("string")
        for brand in BRANDS:
            pattern = rf"^\s*{re.escape(brand)}(?:mg)?\b"
            brand_mask |= names.str.contains(pattern, case=False, na=False, regex=True)
        brand_group_keys = set(eligible.loc[brand_mask, "_group_key"])
        brand_group_rows = int(eligible["_group_key"].isin(brand_group_keys).sum())
        self.stdout.write(
            f"Priority brand groups: {len(brand_group_keys):,}; "
            f"rows in those groups: {brand_group_rows:,}"
        )

        if len(eligible) <= MAX_ROWS:
            selected_group_keys = set(eligible["_group_key"])
        else:
            selected_group_keys = set(brand_group_keys)
            selected_rows = brand_group_rows
            remaining_capacity = max(0, MAX_ROWS - selected_rows)

            largest_groups = repeated_sizes.sort_values(ascending=False, kind="stable")
            for raw_key, size in largest_groups.items():
                key = tuple(raw_key)
                if key in selected_group_keys:
                    continue
                group_size = int(size)
                if group_size <= remaining_capacity:
                    selected_group_keys.add(key)
                    selected_rows += group_size
                    remaining_capacity -= group_size

        selected = eligible.loc[
            eligible["_group_key"].isin(selected_group_keys)
        ].copy()
        self.stdout.write(f"Rows selected for import: {len(selected):,}")

        objects = []
        for values in selected.to_dict(orient="records"):
            objects.append(
                Medicine(
                    name=as_string(values["name"]),
                    manufacturer=as_string(values["manufacturer_name"]),
                    mrp=as_decimal(values["price(₹)"]),
                    pack_size_label=as_string(values["pack_size_label"]),
                    pack_units=as_integer(values["pack_units"]),
                    unit_type=as_string(values["unit_type"]),
                    form=as_string(values["form"]),
                    form_variant=as_string(values["form_variant"]),
                    pack_volume=as_decimal(values["pack_volume"]),
                    salt_1=as_string(values["salt_1"]),
                    salt_2=as_string(values["salt_2"]) or None,
                    salt_key=as_string(values["salt_key"]),
                    price_per_unit=as_decimal(values["price_per_unit"]),
                    composition_incomplete=as_bool(values["composition_incomplete"]),
                    is_comparable=as_bool(values["is_comparable"]),
                )
            )

        incoming_signatures = Counter(
            tuple(getattr(item, field) for field in MODEL_FIELDS) for item in objects
        )
        existing_count = Medicine.objects.count()
        existing_signatures = Counter(
            Medicine.objects.values_list(*MODEL_FIELDS).iterator(chunk_size=BATCH_SIZE)
        )
        catalog_matches_csv = existing_signatures == incoming_signatures

        if options["dry_run"]:
            if catalog_matches_csv:
                self.stdout.write("Dry run: the database already matches this CSV; no change needed.")
            elif existing_count and not options["replace"]:
                self.stdout.write(
                    f"Dry run: would refuse to add {len(objects):,} rows because "
                    f"{existing_count:,} medicine rows already exist. Use --replace after reviewing the database."
                )
            else:
                self.stdout.write(f"Dry run: would import {len(objects):,} medicine rows.")
            return

        if catalog_matches_csv:
            self.stdout.write(self.style.SUCCESS("Medicine catalog already matches the CSV; no rows changed."))
            return

        if existing_count and not options["replace"]:
            raise CommandError(
                f"The database contains {existing_count:,} medicine rows that do not match this CSV. "
                "No data was changed. Review the database, back it up, then rerun with --replace to rebuild it."
            )

        if existing_count and PharmacyPrice.objects.exists():
            raise CommandError(
                "Medicine replacement was stopped because pharmacy prices reference existing medicines. "
                "No data was changed; reconcile those prices before replacing the catalog."
            )

        created = 0
        with transaction.atomic():
            if existing_count:
                Medicine.objects.all().delete()
            for offset in range(0, len(objects), BATCH_SIZE):
                batch = objects[offset : offset + BATCH_SIZE]
                Medicine.objects.bulk_create(batch, batch_size=BATCH_SIZE)
                created += len(batch)

        self.stdout.write(self.style.SUCCESS(f"Medicines imported: {created:,}; previous rows replaced: {existing_count:,}"))
