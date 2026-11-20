from decimal import Decimal
import re

from django.db.models import F, Min, Q
from django.shortcuts import get_object_or_404
from rapidfuzz import fuzz, process
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from .models import (
    DiagnosticTest,
    LabTestPrice,
    Medicine,
    PharmacyPrice,
)


def money(value):
    return None if value is None else f"{value:.2f}"


def savings(baseline, cost):
    if cost is None:
        return {"amount": None, "percent": None}
    amount = baseline - cost
    percent = (amount / baseline * 100) if baseline else Decimal("0")
    return {"amount": money(amount), "percent": f"{percent:.2f}"}


def serialize_medicine(medicine):
    return {
        "id": medicine.id,
        "name": medicine.name,
        "manufacturer": medicine.manufacturer,
        "mrp": money(medicine.mrp),
        "pack_size_label": medicine.pack_size_label,
        "pack_units": medicine.pack_units,
        "unit_type": medicine.unit_type,
        "form": medicine.form,
        "form_variant": medicine.form_variant,
        "pack_volume": money(medicine.pack_volume),
        "salt_1": medicine.salt_1,
        "salt_2": medicine.salt_2,
        "salt_key": medicine.salt_key,
        "price_per_unit": money(medicine.price_per_unit),
        "composition_incomplete": medicine.composition_incomplete,
        "is_comparable": medicine.is_comparable,
    }


def serialize_pharmacy(pharmacy):
    return {
        "id": pharmacy.id,
        "name": pharmacy.name,
        "type": pharmacy.type,
        "area": pharmacy.area,
        "address": pharmacy.address,
        "lat": str(pharmacy.lat),
        "lng": str(pharmacy.lng),
        "phone": pharmacy.phone,
        "hours": pharmacy.hours,
    }


def serialize_lab(lab):
    return {
        "id": lab.id,
        "name": lab.name,
        "address": lab.address,
        "lat": str(lab.lat),
        "lng": str(lab.lng),
        "phone": lab.phone,
        "hours": lab.hours,
        "nabl_accredited": lab.nabl_accredited,
        "home_collection": lab.home_collection,
        "collection_fee": money(lab.collection_fee),
    }


def _medicine_search_result(medicine):
    return {
        "id": medicine.id,
        "name": medicine.name,
        "manufacturer": medicine.manufacturer,
        "mrp": money(medicine.mrp),
        "form": medicine.form,
        "salt_key": medicine.salt_key,
    }


@api_view(["GET"])
def medicine_search(request):
    query = request.query_params.get("q", "").strip()[:100]
    if not query:
        return Response([])

    found = []
    seen_ids = set()
    for queryset in (
        Medicine.objects.filter(name__istartswith=query),
        Medicine.objects.filter(name__icontains=query),
        Medicine.objects.filter(salt_key__icontains=query),
    ):
        for medicine in queryset.order_by("name", "id")[:20]:
            if medicine.id not in seen_ids:
                found.append(medicine)
                seen_ids.add(medicine.id)
                if len(found) == 20:
                    return Response([_medicine_search_result(item) for item in found])

    if len(found) < 20 and len(query) >= 3:
        choices = list(Medicine.objects.values_list("id", "name"))
        matches = process.extract(
            query,
            choices,
            scorer=fuzz.WRatio,
            processor=lambda choice: choice[1],
            limit=100,
            score_cutoff=60,
        )
        matching_ids = [choice[0] for choice, _, _ in matches if choice[0] not in seen_ids]
        fuzzy = Medicine.objects.filter(id__in=matching_ids)
        by_id = {item.id: item for item in fuzzy}
        found.extend(by_id[medicine_id] for medicine_id in matching_ids if medicine_id in by_id)

    return Response([_medicine_search_result(item) for item in found[:20]])


@api_view(["GET"])
def medicine_detail(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    alternatives = Medicine.objects.none()
    if medicine.salt_key and medicine.is_comparable and not medicine.composition_incomplete:
        alternatives = (
            Medicine.objects.filter(
                salt_key=medicine.salt_key,
                form=medicine.form,
                form_variant=medicine.form_variant,
                is_comparable=True,
                composition_incomplete=False,
            )
            .exclude(pk=medicine.pk)
            .annotate(
                lowest_pharmacy_price=Min(
                    "pharmacyprice__price",
                    filter=Q(pharmacyprice__in_stock=True),
                )
            )
            .order_by(F("price_per_unit").asc(nulls_last=True), "name", "id")
        )

    alternative_rows = []
    for alternative in alternatives:
        lowest_price = alternative.lowest_pharmacy_price
        can_compare_reference_pack = bool(
            medicine.pack_units
            and alternative.pack_units
            and medicine.unit_type == alternative.unit_type
        )
        reference_price = (
            alternative.mrp
            * Decimal(medicine.pack_units)
            / Decimal(alternative.pack_units)
            if can_compare_reference_pack
            else None
        )
        can_compare_pack = bool(
            lowest_price is not None
            and medicine.pack_units
            and alternative.pack_units
            and medicine.unit_type == alternative.unit_type
        )
        equivalent_price = (
            lowest_price
            * Decimal(medicine.pack_units)
            / Decimal(alternative.pack_units)
            if can_compare_pack
            else None
        )
        alternative_rows.append(
            {
                "id": alternative.id,
                "name": alternative.name,
                "manufacturer": alternative.manufacturer,
                "mrp": money(alternative.mrp),
                "price_per_unit": money(alternative.price_per_unit),
                "reference_price_for_selected_pack": money(reference_price),
                "reference_savings_vs_selected_mrp": (
                    savings(medicine.mrp, reference_price)
                    if can_compare_reference_pack
                    else None
                ),
                "lowest_pharmacy_price": money(lowest_price),
                "lowest_pharmacy_price_per_unit": (
                    money(lowest_price / Decimal(alternative.pack_units))
                    if lowest_price is not None and alternative.pack_units
                    else None
                ),
                "equivalent_price_for_selected_pack": money(equivalent_price),
                "savings_vs_selected_mrp": (
                    savings(medicine.mrp, equivalent_price) if can_compare_pack else None
                ),
            }
        )

    return Response({"medicine": serialize_medicine(medicine), "alternatives": alternative_rows})


@api_view(["GET"])
def medicine_prices(request, pk):
    get_object_or_404(Medicine, pk=pk)
    prices = PharmacyPrice.objects.filter(medicine_id=pk).select_related("pharmacy").order_by("price", "id")
    return Response(
        [
            {
                "price": money(item.price),
                "in_stock": item.in_stock,
                "last_updated": item.last_updated.isoformat(),
                "pharmacy": serialize_pharmacy(item.pharmacy),
            }
            for item in prices
        ]
    )


@api_view(["GET"])
def test_search(request):
    query = request.query_params.get("q", "").strip()[:100]
    if not query:
        return Response([])
    tests = DiagnosticTest.objects.filter(
        Q(name__icontains=query) | Q(aliases__icontains=query)
    ).order_by("name", "id")[:20]
    return Response(
        [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "aliases": item.aliases,
                "fasting_required": item.fasting_required,
            }
            for item in tests
        ]
    )


@api_view(["GET"])
def test_prices(request, pk):
    get_object_or_404(DiagnosticTest, pk=pk)
    prices = LabTestPrice.objects.filter(test_id=pk).select_related("lab").order_by("price", "id")
    return Response(
        [
            {
                "price": money(item.price),
                "report_time_hours": item.report_time_hours,
                "last_updated": item.last_updated.isoformat(),
                "lab": serialize_lab(item.lab),
            }
            for item in prices
        ]
    )


def _effective_offer_price(offer_price, requested_medicine, offered_medicine, quantity):
    cost = offer_price * quantity
    if (
        requested_medicine.pack_units
        and offered_medicine.pack_units
        and offered_medicine.pack_units > 0
    ):
        cost *= Decimal(requested_medicine.pack_units) / Decimal(offered_medicine.pack_units)
    return cost


def _parse_positive_integer(value, field_name):
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a positive integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a positive integer")
    if parsed <= 0 or str(parsed) != str(value).strip():
        raise ValueError(f"{field_name} must be a positive integer")
    if field_name == "qty" and parsed > 1000:
        raise ValueError("qty cannot exceed 1000")
    return parsed


@api_view(["POST"])
def estimate(request):
    body = request.data
    medicine_input = body.get("medicines", [])
    test_input = body.get("tests", [])
    use_alternatives = body.get("use_cheapest_alternatives", False)
    if not isinstance(medicine_input, list) or not isinstance(test_input, list):
        return Response({"detail": "medicines and tests must be lists"}, status=status.HTTP_400_BAD_REQUEST)
    if len(medicine_input) > 100 or len(test_input) > 100:
        return Response({"detail": "An estimate can include at most 100 medicine and 100 test entries"}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(use_alternatives, bool):
        return Response({"detail": "use_cheapest_alternatives must be a boolean"}, status=status.HTTP_400_BAD_REQUEST)

    medicine_lines = []
    try:
        for entry in medicine_input:
            if not isinstance(entry, dict) or "id" not in entry or "qty" not in entry:
                raise ValueError("Each medicine must include id and qty")
            medicine_id = _parse_positive_integer(entry["id"], "medicine id")
            quantity = _parse_positive_integer(entry["qty"], "qty")
            medicine = get_object_or_404(Medicine, pk=medicine_id)
            existing_line = next(
                (line for line in medicine_lines if line["medicine"].id == medicine.id),
                None,
            )
            if existing_line is not None:
                existing_line["quantity"] += quantity
                continue
            options = [medicine]
            if use_alternatives and medicine.pack_units and medicine.unit_type:
                alternatives = list(
                    Medicine.objects.filter(
                        salt_key=medicine.salt_key,
                        form=medicine.form,
                        form_variant=medicine.form_variant,
                        is_comparable=True,
                        composition_incomplete=False,
                        pack_units__isnull=False,
                        unit_type=medicine.unit_type,
                    ).order_by("id")
                )
                options.extend(item for item in alternatives if item.id != medicine.id)
            medicine_lines.append({"medicine": medicine, "quantity": quantity, "options": options})
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    try:
        test_ids = list(dict.fromkeys(_parse_positive_integer(item, "test id") for item in test_input))
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    tests_by_id = DiagnosticTest.objects.in_bulk(test_ids)
    missing_test_ids = sorted(set(test_ids) - set(tests_by_id))
    if missing_test_ids:
        raise NotFound({"tests": f"Unknown test ids: {missing_test_ids}"})
    test_objects = [tests_by_id[test_id] for test_id in test_ids]

    mrp_total = sum(
        (line["medicine"].mrp * line["quantity"] for line in medicine_lines),
        Decimal("0"),
    )

    reference_items = []
    reference_total = Decimal("0")
    for line in medicine_lines:
        requested = line["medicine"]
        quantity = Decimal(line["quantity"])
        reference_options = []
        for option in line["options"]:
            if (
                requested.pack_units
                and option.pack_units
                and option.pack_units > 0
                and requested.unit_type == option.unit_type
            ):
                cost = (
                    option.mrp
                    * Decimal(requested.pack_units)
                    / Decimal(option.pack_units)
                    * quantity
                )
            else:
                cost = option.mrp * quantity
            reference_options.append((cost, option))
        cost, selected_option = min(reference_options, key=lambda item: (item[0], item[1].id))
        reference_total += cost
        reference_items.append(
            {
                "medicine_id": requested.id,
                "name": requested.name,
                "selected_product": {
                    "id": selected_option.id,
                    "name": selected_option.name,
                },
                "total": money(cost),
            }
        )

    candidate_ids = {option.id for line in medicine_lines for option in line["options"]}
    offers = list(
        PharmacyPrice.objects.filter(medicine_id__in=candidate_ids, in_stock=True)
        .select_related("pharmacy", "medicine")
        .order_by("price", "id")
    ) if candidate_ids else []
    offers_by_medicine = {}
    for offer in offers:
        offers_by_medicine.setdefault(offer.medicine_id, []).append(offer)

    pharmacy_line_costs = {}
    split_items = []
    split_total = Decimal("0")
    split_complete = True
    for line in medicine_lines:
        requested = line["medicine"]
        quantity = Decimal(line["quantity"])
        cheapest = None
        costs_by_pharmacy = {}
        for option in line["options"]:
            for offer in offers_by_medicine.get(option.id, []):
                cost = _effective_offer_price(offer.price, requested, option, quantity)
                current = costs_by_pharmacy.get(offer.pharmacy_id)
                if current is None or cost < current["cost"]:
                    costs_by_pharmacy[offer.pharmacy_id] = {
                        "cost": cost,
                        "offer": offer,
                        "option": option,
                    }
                if cheapest is None or cost < cheapest["cost"]:
                    cheapest = {"cost": cost, "offer": offer, "option": option}

        for pharmacy_id, choice in costs_by_pharmacy.items():
            pharmacy_line_costs.setdefault(pharmacy_id, {})[requested.id] = choice

        if cheapest is None:
            split_complete = False
            split_items.append(
                {"medicine_id": requested.id, "name": requested.name, "total": None, "pharmacy": None}
            )
        else:
            split_total += cheapest["cost"]
            split_items.append(
                {
                    "medicine_id": requested.id,
                    "name": requested.name,
                    "selected_product": {
                        "id": cheapest["option"].id,
                        "name": cheapest["option"].name,
                    },
                    "total": money(cheapest["cost"]),
                    "pharmacy": serialize_pharmacy(cheapest["offer"].pharmacy),
                }
            )

    single_pharmacy_totals = []
    if medicine_lines:
        for pharmacy_id, line_choices in pharmacy_line_costs.items():
            if len(line_choices) == len(medicine_lines):
                total = sum((choice["cost"] for choice in line_choices.values()), Decimal("0"))
                pharmacy = next(
                    choice["offer"].pharmacy for choice in line_choices.values()
                )
                single_pharmacy_totals.append((total, pharmacy_id, pharmacy))
    else:
        single_pharmacy_totals.append((Decimal("0"), None, None))
    single_pharmacy_totals.sort(key=lambda row: (row[0], row[1] or 0))
    best_single = single_pharmacy_totals[0] if single_pharmacy_totals else None

    if best_single:
        single_pharmacy_result = {
            "pharmacy": serialize_pharmacy(best_single[2]) if best_single[2] else None,
            "total": money(best_single[0]),
        }
        single_pharmacy_cost = best_single[0]
    else:
        single_pharmacy_result = {"pharmacy": None, "total": None}
        single_pharmacy_cost = None

    split_cost = split_total if split_complete else None
    medicine_result = {
        "at_mrp": money(mrp_total),
        "reference_estimate": {
            "total": money(reference_total),
            "items": reference_items,
            "savings_vs_mrp": savings(mrp_total, reference_total),
            "basis": "catalog_mrp",
        },
        "cheapest_single_pharmacy": single_pharmacy_result,
        "split_across_pharmacies": {
            "total": money(split_cost),
            "items": split_items,
        },
        "savings_vs_mrp": {
            "single_pharmacy": savings(mrp_total, single_pharmacy_cost),
            "split_across_pharmacies": savings(mrp_total, split_cost),
        },
    }

    test_prices = list(
        LabTestPrice.objects.filter(test_id__in=test_ids)
        .select_related("lab", "test")
        .order_by("price", "id")
    ) if test_ids else []
    prices_by_test = {}
    prices_by_lab = {}
    for test_price in test_prices:
        prices_by_test.setdefault(test_price.test_id, []).append(test_price)
        prices_by_lab.setdefault(test_price.lab_id, {})[test_price.test_id] = test_price

    cheapest_lab_per_test = []
    cheapest_test_total = Decimal("0")
    all_tests_priced = True
    for test in test_objects:
        choices = prices_by_test.get(test.id, [])
        if not choices:
            all_tests_priced = False
            cheapest_lab_per_test.append({"test_id": test.id, "test_name": test.name, "price": None, "lab": None})
            continue
        choice = choices[0]
        cheapest_test_total += choice.price
        cheapest_lab_per_test.append(
            {
                "test_id": test.id,
                "test_name": test.name,
                "price": money(choice.price),
                "lab": serialize_lab(choice.lab),
            }
        )

    if not test_objects:
        best_lab_result = None
        best_lab_total = Decimal("0")
    else:
        lab_totals = []
        for lab_id, lab_prices in prices_by_lab.items():
            if len(lab_prices) == len(test_objects):
                lab = next(price.lab for price in lab_prices.values())
                subtotal = sum((lab_prices[test.id].price for test in test_objects), Decimal("0"))
                total = subtotal + lab.collection_fee
                lab_totals.append((total, lab_id, lab, subtotal))
        lab_totals.sort(key=lambda row: (row[0], row[1]))
        if lab_totals:
            total, _, lab, subtotal = lab_totals[0]
            best_lab_total = total
            best_lab_result = {
                "lab": serialize_lab(lab),
                "test_subtotal": money(subtotal),
                "collection_fee": money(lab.collection_fee),
                "total": money(total),
            }
        else:
            best_lab_total = None
            best_lab_result = None

    if not test_objects:
        cheapest_test_result = money(Decimal("0"))
    else:
        cheapest_test_result = money(cheapest_test_total) if all_tests_priced else None

    def combined_total(medicine_cost, lab_cost):
        if medicine_cost is None or lab_cost is None:
            return None
        return money(medicine_cost + lab_cost)

    return Response(
        {
            "medicines": medicine_result,
            "tests": {
                "cheapest_lab_per_test": cheapest_lab_per_test,
                "cheapest_per_test_total": cheapest_test_result,
                "best_single_lab": best_lab_result,
            },
            "combined_grand_total": {
                "reference_medicines_plus_cheapest_test_labs": combined_total(
                    reference_total,
                    Decimal(cheapest_test_result) if cheapest_test_result is not None else None,
                ),
                "at_mrp_plus_cheapest_test_labs": combined_total(
                    mrp_total,
                    Decimal(cheapest_test_result) if cheapest_test_result is not None else None,
                ),
                "single_pharmacy_medicines_plus_best_single_lab": combined_total(
                    single_pharmacy_cost, best_lab_total
                ),
                "split_medicines_plus_best_single_lab": combined_total(
                    split_cost, best_lab_total
                ),
            },
        }
    )
