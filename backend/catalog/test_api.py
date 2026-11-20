from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from .models import (
    DiagnosticTest,
    Lab,
    LabTestPrice,
    Medicine,
    Pharmacy,
    PharmacyPrice,
)


class CatalogApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.pharmacy_one = Pharmacy.objects.create(
            name="Central Pharmacy",
            type=Pharmacy.PharmacyType.CHAIN,
            area="Central",
            address="1 Main Road",
            lat=Decimal("21.145000"),
            lng=Decimal("79.087000"),
            phone="0712-000-0001",
            hours="09:00-21:00",
        )
        self.pharmacy_two = Pharmacy.objects.create(
            name="North Pharmacy",
            type=Pharmacy.PharmacyType.LOCAL,
            area="North",
            address="2 North Road",
            lat=Decimal("21.155000"),
            lng=Decimal("79.097000"),
            phone="0712-000-0002",
            hours="09:00-21:00",
        )
        self.dolo = self.make_medicine(
            "Dolo 650 Tablet", "paracetamol (650mg)", Decimal("100.00"), Decimal("10.00")
        )
        self.generic = self.make_medicine(
            "Generic Paracetamol 650 Tablet",
            "paracetamol (650mg)",
            Decimal("70.00"),
            Decimal("7.00"),
        )
        self.cetirizine = self.make_medicine(
            "Cetirizine 10 Tablet", "cetirizine (10mg)", Decimal("100.00"), Decimal("10.00")
        )
        PharmacyPrice.objects.create(
            medicine=self.dolo, pharmacy=self.pharmacy_one, price=Decimal("90.00")
        )
        PharmacyPrice.objects.create(
            medicine=self.dolo, pharmacy=self.pharmacy_two, price=Decimal("85.00")
        )
        PharmacyPrice.objects.create(
            medicine=self.generic, pharmacy=self.pharmacy_one, price=Decimal("80.00")
        )
        PharmacyPrice.objects.create(
            medicine=self.generic, pharmacy=self.pharmacy_two, price=Decimal("70.00")
        )
        PharmacyPrice.objects.create(
            medicine=self.cetirizine, pharmacy=self.pharmacy_one, price=Decimal("30.00")
        )
        PharmacyPrice.objects.create(
            medicine=self.cetirizine, pharmacy=self.pharmacy_two, price=Decimal("50.00")
        )

        self.lab_one = self.make_lab("Central Diagnostics", Decimal("0.00"))
        self.lab_two = self.make_lab("North Diagnostics", Decimal("40.00"))
        self.cbc = DiagnosticTest.objects.create(
            name="Complete Blood Count",
            category="Hematology",
            aliases="CBC; hemogram",
            fasting_required=False,
        )
        self.lipid = DiagnosticTest.objects.create(
            name="Lipid Profile",
            category="Biochemistry",
            aliases="cholesterol panel",
            fasting_required=True,
        )
        LabTestPrice.objects.create(
            lab=self.lab_one, test=self.cbc, price=Decimal("250.00"), report_time_hours=6
        )
        LabTestPrice.objects.create(
            lab=self.lab_two, test=self.cbc, price=Decimal("280.00"), report_time_hours=8
        )
        LabTestPrice.objects.create(
            lab=self.lab_one, test=self.lipid, price=Decimal("500.00"), report_time_hours=8
        )
        LabTestPrice.objects.create(
            lab=self.lab_two, test=self.lipid, price=Decimal("480.00"), report_time_hours=10
        )

    @staticmethod
    def make_medicine(name, salt_key, mrp, price_per_unit):
        return Medicine.objects.create(
            name=name,
            manufacturer="Example Pharma",
            mrp=mrp,
            pack_size_label="strip of 10 tablets",
            pack_units=10,
            unit_type="tablet",
            form="tablet",
            form_variant="",
            salt_1=salt_key.split(" (")[0],
            salt_key=salt_key,
            price_per_unit=price_per_unit,
            composition_incomplete=False,
            is_comparable=True,
        )

    @staticmethod
    def make_lab(name, collection_fee):
        return Lab.objects.create(
            name=name,
            address="1 Diagnostic Road",
            lat=Decimal("21.145000"),
            lng=Decimal("79.087000"),
            phone="0712-000-1001",
            hours="07:00-19:00",
            nabl_accredited=True,
            home_collection=True,
            collection_fee=collection_fee,
        )

    def test_medicine_search_supports_name_and_ingredient(self):
        name_response = self.client.get("/api/medicines/search", {"q": "Doolo"})
        self.assertEqual(name_response.status_code, 200)
        self.assertEqual(name_response.data[0]["id"], self.dolo.id)

        ingredient_response = self.client.get(
            "/api/medicines/search", {"q": "paracetamol"}
        )
        self.assertEqual(ingredient_response.status_code, 200)
        self.assertIn(self.dolo.id, [item["id"] for item in ingredient_response.data])

    def test_medicine_detail_returns_alternatives_and_savings(self):
        response = self.client.get(f"/api/medicines/{self.dolo.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["medicine"]["id"], self.dolo.id)
        alternative = response.data["alternatives"][0]
        self.assertEqual(alternative["id"], self.generic.id)
        self.assertEqual(alternative["lowest_pharmacy_price"], "70.00")
        self.assertEqual(alternative["savings_vs_selected_mrp"]["amount"], "30.00")

    def test_alternative_savings_use_equivalent_pack_and_skip_unit_mismatch(self):
        self.generic.pack_units = 20
        self.generic.price_per_unit = Decimal("3.50")
        self.generic.save()
        response = self.client.get(f"/api/medicines/{self.dolo.id}/")
        alternative = response.data["alternatives"][0]
        self.assertEqual(alternative["lowest_pharmacy_price"], "70.00")
        self.assertEqual(alternative["equivalent_price_for_selected_pack"], "35.00")
        self.assertEqual(alternative["savings_vs_selected_mrp"]["amount"], "65.00")

        self.generic.unit_type = "capsule"
        self.generic.save()
        response = self.client.get(f"/api/medicines/{self.dolo.id}/")
        self.assertIsNone(response.data["alternatives"][0]["savings_vs_selected_mrp"])

    def test_medicine_prices_are_sorted_and_include_pharmacies(self):
        response = self.client.get(f"/api/medicines/{self.dolo.id}/prices")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["price"] for row in response.data], ["85.00", "90.00"])
        self.assertEqual(response.data[0]["pharmacy"]["name"], "North Pharmacy")

    def test_test_search_matches_aliases(self):
        response = self.client.get("/api/tests/search", {"q": "hemogram"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], self.cbc.id)

    def test_test_prices_include_lab_details_and_are_sorted(self):
        response = self.client.get(f"/api/tests/{self.cbc.id}/prices")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["price"] for row in response.data], ["250.00", "280.00"])
        self.assertTrue(response.data[0]["lab"]["nabl_accredited"])
        self.assertIn("home_collection", response.data[0]["lab"])

    def test_estimate_compares_pharmacy_and_lab_options(self):
        response = self.client.post(
            "/api/estimate",
            {
                "medicines": [
                    {"id": self.dolo.id, "qty": 2},
                    {"id": self.cetirizine.id, "qty": 1},
                ],
                "tests": [self.cbc.id, self.lipid.id],
                "use_cheapest_alternatives": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["medicines"]["at_mrp"], "300.00")
        self.assertEqual(
            response.data["medicines"]["cheapest_single_pharmacy"]["total"], "190.00"
        )
        self.assertEqual(
            response.data["medicines"]["split_across_pharmacies"]["total"], "170.00"
        )
        self.assertEqual(
            response.data["tests"]["best_single_lab"]["total"], "750.00"
        )
        self.assertEqual(
            response.data["combined_grand_total"]["split_medicines_plus_best_single_lab"],
            "920.00",
        )

    def test_estimate_rejects_unreasonably_large_quantity(self):
        response = self.client.post(
            "/api/estimate",
            {"medicines": [{"id": self.dolo.id, "qty": 1001}], "tests": []},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("qty cannot exceed 1000", response.data["detail"])
