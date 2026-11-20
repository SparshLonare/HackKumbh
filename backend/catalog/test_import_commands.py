import csv
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import TestCase

from catalog.management.commands import import_local_catalog, import_medicines
from catalog.models import DiagnosticTest, Lab, LabTestPrice, Medicine, Pharmacy, PharmacyPrice


class ImportMedicinesCommandTests(TestCase):
    headers = [
        "id", "name", "price(₹)", "manufacturer_name", "pack_size_label",
        "pack_units", "unit_type", "form", "form_variant", "pack_volume",
        "salt_1", "salt_2", "salt_key", "price_per_unit",
        "composition_incomplete", "is_comparable",
    ]

    def make_csv(self, folder):
        path = Path(folder) / "medicines_clean.csv"
        rows = []
        for row_id, name, price in ((1, "Example Brand", "100.00"), (2, "Example Generic", "80.00")):
            rows.append({
                "id": row_id,
                "name": name,
                "price(₹)": price,
                "manufacturer_name": "Example Pharma",
                "pack_size_label": "strip of 10 tablets",
                "pack_units": 10,
                "unit_type": "tablet",
                "form": "tablet",
                "form_variant": "",
                "pack_volume": "",
                "salt_1": "example ingredient",
                "salt_2": "",
                "salt_key": "example ingredient (10mg)",
                "price_per_unit": str(float(price) / 10),
                "composition_incomplete": "False",
                "is_comparable": "True",
            })
        with path.open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=self.headers)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_repeat_import_is_a_no_op_and_mismatched_catalog_requires_replace(self):
        with TemporaryDirectory() as folder:
            path = self.make_csv(folder)
            with patch.object(import_medicines, "CSV_PATH", path):
                call_command("import_medicines", verbosity=0)
                self.assertEqual(Medicine.objects.count(), 2)

                call_command("import_medicines", verbosity=0)
                self.assertEqual(Medicine.objects.count(), 2)

                Medicine.objects.create(
                    name="Manually added record",
                    manufacturer="Example",
                    mrp=100,
                    pack_size_label="box",
                    pack_units=1,
                    unit_type="tablet",
                    form="tablet",
                    salt_1="example",
                    salt_key="example (1mg)",
                    price_per_unit=100,
                )
                with self.assertRaises(CommandError):
                    call_command("import_medicines", verbosity=0)
                self.assertEqual(Medicine.objects.count(), 3)

                call_command("import_medicines", "--replace", verbosity=0)
                self.assertEqual(Medicine.objects.count(), 2)

    def test_dry_run_does_not_write(self):
        with TemporaryDirectory() as folder:
            path = self.make_csv(folder)
            with patch.object(import_medicines, "CSV_PATH", path):
                call_command("import_medicines", "--dry-run", verbosity=0)
                self.assertEqual(Medicine.objects.count(), 0)

    def test_replace_refuses_to_cascade_existing_pharmacy_prices(self):
        with TemporaryDirectory() as folder:
            path = self.make_csv(folder)
            with patch.object(import_medicines, "CSV_PATH", path):
                call_command("import_medicines", verbosity=0)
                medicine = Medicine.objects.first()
                pharmacy = Pharmacy.objects.create(
                    name="Linked Pharmacy",
                    type=Pharmacy.PharmacyType.LOCAL,
                    area="Central",
                    address="1 Main Road",
                    lat=21,
                    lng=79,
                    phone="0712-000-0000",
                    hours="09:00-18:00",
                )
                PharmacyPrice.objects.create(medicine=medicine, pharmacy=pharmacy, price=80)
                Medicine.objects.create(
                    name="Extra record",
                    manufacturer="Example",
                    mrp=100,
                    pack_size_label="box",
                    pack_units=1,
                    unit_type="tablet",
                    form="tablet",
                    salt_1="extra",
                    salt_key="extra (1mg)",
                    price_per_unit=100,
                )
                with self.assertRaises(CommandError):
                    call_command("import_medicines", "--replace", verbosity=0)
                self.assertEqual(Medicine.objects.count(), 3)
                self.assertEqual(PharmacyPrice.objects.count(), 1)


class ImportLocalCatalogCommandTests(TestCase):
    def test_reimport_updates_rows_instead_of_duplicating(self):
        with patch.object(import_local_catalog, "DATA_DIR", Path(__file__).resolve().parents[1] / "data"):
            call_command("import_local_catalog", verbosity=0)
            counts = (
                Pharmacy.objects.count(),
                Lab.objects.count(),
                DiagnosticTest.objects.count(),
                LabTestPrice.objects.count(),
            )
            call_command("import_local_catalog", verbosity=0)
            self.assertEqual(
                counts,
                (
                    Pharmacy.objects.count(),
                    Lab.objects.count(),
                    DiagnosticTest.objects.count(),
                    LabTestPrice.objects.count(),
                ),
            )
