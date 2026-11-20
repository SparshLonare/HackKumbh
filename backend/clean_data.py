"""Clean the raw medicine CSV and report parsing/comparison diagnostics."""

from __future__ import annotations

import re
from pathlib import Path
import sys

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "data" / "raw" / "indian_medicine_data.csv"
OUTPUT_CSV = BASE_DIR / "data" / "clean" / "medicines_clean.csv"

PACK_PATTERN = re.compile(
    r"^(?P<package>[a-z][a-z -]*?)\s+of\s+"
    r"(?P<quantity>\d+(?:\.\d+)?)\s*(?P<measure>ml|gm)?\s*(?P<descriptor>.*)$",
    re.IGNORECASE,
)
COMPOSITION_PATTERN = re.compile(r"^\s*(.*?)\s*\(([^()]*)\)\s*$")
STRENGTH_PATTERN = re.compile(
    r"(?<!\w)\d+(?:\.\d+)?\s*(?:mg|mcg|µg|g|gm|ml|iu|%)?"
    r"(?:\s*/\s*\d+(?:\.\d+)?\s*(?:mg|mcg|µg|g|gm|ml|iu|%)?)+",
    re.IGNORECASE,
)
FORM_VARIANT_PATTERN = re.compile(r"\b(sr|er|dt|md|pr)\b", re.IGNORECASE)
ALIASES = {"amoxycillin": "amoxicillin"}


def _present(value: object) -> bool:
    return pd.notna(value) and bool(str(value).strip())


def parse_pack(value: object) -> dict[str, object]:
    """Parse the container, size and dosage form from a pack label."""
    result: dict[str, object] = {
        "pack_parsed": False,
        "form": "other",
        "form_variant": "",
        "pack_units": pd.NA,
        "unit_type": pd.NA,
        "pack_volume": pd.NA,
    }
    if not _present(value):
        return result

    match = PACK_PATTERN.fullmatch(str(value).strip())
    if not match:
        return result

    result["pack_parsed"] = True
    package = match.group("package").strip().lower()
    quantity = float(match.group("quantity"))
    measure = (match.group("measure") or "").lower()
    descriptor = match.group("descriptor").strip().lower()

    variant_match = FORM_VARIANT_PATTERN.search(descriptor)
    if variant_match:
        result["form_variant"] = variant_match.group(1).lower()

    if re.search(r"\bsoft\s+gelatin\s+capsules?\b", descriptor):
        result["form"] = "softgel capsule"
    elif re.search(r"\bpowder\s+for\s+injection\b", descriptor):
        result["form"] = "powder for injection"
    elif re.search(r"\bdry\s+syrup\b", descriptor):
        result["form"] = "dry syrup"
    elif re.search(r"\boral\s+suspension\b", descriptor):
        result["form"] = "oral suspension"
    elif re.search(r"\bsuspension\b", descriptor):
        result["form"] = "suspension"
    elif re.search(r"\beye\s+drops?\b", descriptor):
        result["form"] = "eye drop"
    elif re.search(r"\bcapsules?\b", descriptor):
        result["form"] = "capsule"
    elif re.search(r"\btablets?\b", descriptor):
        result["form"] = "tablet"
    elif re.search(r"\bsyrup\b", descriptor):
        result["form"] = "syrup"
    elif re.search(r"\binjection\b", descriptor):
        result["form"] = "injection"
    elif re.search(r"\bcream\b", descriptor):
        result["form"] = "cream"

    if package == "strip" and re.search(
        r"\btablets?\b|\bcapsules?\b|\bsoft\s+gelatin\s+capsules?\b",
        descriptor,
    ):
        result["pack_units"] = quantity
        result["unit_type"] = "capsule" if re.search(r"\bcapsules?\b", descriptor) else "tablet"
    elif package in {"bottle", "packet"} and measure == "ml":
        result["pack_units"] = quantity
        result["unit_type"] = "ml"
    elif package == "tube" and measure == "gm":
        result["pack_units"] = quantity
        result["unit_type"] = "gm"
    elif package in {"vial", "ampoule"}:
        result["pack_units"] = 1
        result["unit_type"] = "vial"
        if measure == "ml":
            result["pack_volume"] = quantity

    return result


def parse_composition(value: object) -> tuple[str | None, str | None, str | None]:
    """Return normalized ingredient name, strength and combined part."""
    if not _present(value):
        return None, None, None

    match = COMPOSITION_PATTERN.fullmatch(str(value))
    if not match:
        return None, None, None

    name = " ".join(match.group(1).lower().split())
    name = ALIASES.get(name, name)
    strength = re.sub(r"\s+", "", match.group(2).lower())
    if not name or not strength:
        return None, None, None
    return name, strength, f"{name} ({strength})"


def slash_strength_count(product_name: object) -> int:
    if not _present(product_name):
        return 0
    return max(
        (len(re.findall(r"\d+(?:\.\d+)?", part)) for part in STRENGTH_PATTERN.findall(str(product_name))),
        default=0,
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    data = pd.read_csv(INPUT_CSV, encoding="utf-8")
    print(f"Initial rows: {len(data):,}")

    discontinued = data["Is_discontinued"].map(
        lambda value: value is True or str(value).strip().lower() == "true"
    )
    removed = int(discontinued.sum())
    data = data.loc[~discontinued].copy()
    print(f"Removed discontinued rows: {removed:,}; rows after step: {len(data):,}")

    prices = pd.to_numeric(data["price(₹)"], errors="coerce")
    nonpositive_price = prices.le(0).fillna(False)
    removed = int(nonpositive_price.sum())
    data = data.loc[~nonpositive_price].copy()
    print(f"Removed rows with price <= 0: {removed:,}; rows after step: {len(data):,}")

    empty_composition = ~data["short_composition1"].map(_present)
    removed = int(empty_composition.sum())
    data = data.loc[~empty_composition].copy()
    print(f"Removed rows with empty short_composition1: {removed:,}; rows after step: {len(data):,}")

    parsed_packs = [parse_pack(value) for value in data["pack_size_label"]]
    pack_data = pd.DataFrame(parsed_packs, index=data.index)
    data = data.join(pack_data)
    failed_pack = ~data["pack_parsed"]
    failed_labels = data.loc[failed_pack, "pack_size_label"].value_counts(dropna=False)
    print(f"Rows after pack parsing: {len(data):,}")
    print(f"Pack labels that failed to parse: {int(failed_pack.sum()):,}")
    print("30 most common unparsed pack labels:")
    print(failed_labels.head(30).to_string())

    composition_1 = [parse_composition(value) for value in data["short_composition1"]]
    composition_2 = [parse_composition(value) for value in data["short_composition2"]]
    data["salt_1"] = [part[0] for part in composition_1]
    data["salt_2"] = [part[0] for part in composition_2]
    composition_counts = data["short_composition1"].map(_present).astype(int)
    composition_counts += data["short_composition2"].map(_present).astype(int)
    data["composition_incomplete"] = [
        slash_strength_count(name) > count
        for name, count in zip(data["name"], composition_counts)
    ]
    salt_keys = []
    salt_names = []
    for first, second in zip(composition_1, composition_2):
        parts = sorted(part[2] for part in (first, second) if part[2] is not None)
        salt_keys.append(" + ".join(parts))
        salt_names.extend(part[0] for part in (first, second) if part[0] is not None)
    data["salt_key"] = salt_keys
    print(f"Rows after composition parsing: {len(data):,}")
    print(f"Rows with composition_incomplete=True: {int(data['composition_incomplete'].sum()):,}")
    print("30 most common salt names:")
    print(pd.Series(salt_names, dtype="string").value_counts().head(30).to_string())

    data["price(₹)"] = pd.to_numeric(data["price(₹)"], errors="coerce")
    numeric_units = pd.to_numeric(data["pack_units"], errors="coerce")
    if numeric_units.dropna().mod(1).eq(0).all():
        data["pack_units"] = numeric_units.astype("Int64")
        numeric_units = data["pack_units"].astype("Float64")
    data["price_per_unit"] = data["price(₹)"].div(numeric_units).where(numeric_units.gt(0))
    data["is_comparable"] = (
        data["pack_parsed"]
        & ~data["composition_incomplete"]
        & data["price(₹)"].gt(0)
    )
    comparable_groups = (
        data.groupby(["salt_key", "form", "form_variant"], dropna=False)
        .size()
        .ge(2)
        .sum()
    )
    print(f"Rows after price-per-unit and comparability calculation: {len(data):,}")
    print(f"Groups with 2 or more salt_key + form + form_variant members: {int(comparable_groups):,}")

    print("Brand checks:")
    for brand in (
        "Dolo 650",
        "Crocin",
        "Augmentin 625",
        "Pan 40",
        "Glycomet",
        "Telma 40",
        "Atorva 10",
        "Azithral 500",
        "Cetzine",
    ):
        brand_pattern = rf"^\s*{re.escape(brand)}(?:mg)?\b"
        matches = data["name"].astype("string").str.contains(
            brand_pattern, case=False, na=False, regex=True
        )
        salt_keys_for_brand = sorted(data.loc[matches, "salt_key"].dropna().unique())
        exists = bool(matches.any())
        keys = ", ".join(salt_keys_for_brand) if salt_keys_for_brand else "<none>"
        print(f"{brand}: exists={exists}; salt_key={keys}")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"\nWrote {len(data):,} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
