"""Print read-only diagnostics for the cleaned medicine CSV."""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import pandas as pd


CSV_PATH = Path(__file__).resolve().parent / "data" / "clean" / "medicines_clean.csv"
GROUP_COLUMNS = ["salt_key", "form", "form_variant"]


def random_rows(data: pd.DataFrame, count: int, columns: list[str]) -> pd.DataFrame:
    """Return up to count random rows, handling empty and small subsets."""
    sample = data.sample(n=min(count, len(data))) if not data.empty else data
    return sample.loc[:, columns]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    data = pd.read_csv(CSV_PATH, encoding="utf-8")
    print(f"File: {CSV_PATH}")
    print(f"Rows: {len(data):,}")

    print("\nForm value counts:")
    print(data["form"].value_counts(dropna=False).to_string())
    print("\nForm variant value counts:")
    print(data["form_variant"].value_counts(dropna=False).to_string())

    for column in ("is_comparable", "composition_incomplete"):
        values = data[column].map(
            lambda value: value is True or str(value).strip().lower() == "true"
        )
        print(f"\n{column} counts:")
        print(f"True: {int(values.sum()):,}")
        print(f"False: {int((~values).sum()):,}")

    print("\n30 most common salt_key values:")
    print(data["salt_key"].value_counts(dropna=False).head(30).to_string())

    group_sizes = data.groupby(GROUP_COLUMNS, dropna=False).size()
    repeated_groups = group_sizes[group_sizes >= 2]
    print(f"\nDistinct salt_key + form + form_variant groups: {len(group_sizes):,}")
    print(f"Groups with 2 or more members: {len(repeated_groups):,}")
    print(f"Rows in groups with 2 or more members: {int(repeated_groups.sum()):,}")

    summary_columns = ["name", "price(₹)", "salt_key", "form", "is_comparable"]
    names = data["name"].astype("string")
    for term in ("atorva", "dolo", "crocin"):
        matching = data.loc[names.str.contains(re.escape(term), case=False, na=False)]
        print(f"\nRows with {term!r} in name ({len(matching):,}):")
        if matching.empty:
            print("<none>")
        else:
            print(matching[summary_columns].to_string(index=False))

    incomplete = data["composition_incomplete"].map(
        lambda value: value is True or str(value).strip().lower() == "true"
    )
    composition_columns = [
        "name",
        "short_composition1",
        "short_composition2",
        "salt_1",
        "salt_2",
    ]
    print("\n15 random composition_incomplete rows (name and composition):")
    print(random_rows(data.loc[incomplete], 15, composition_columns).to_string(index=False))

    other_form = data["form"].astype("string").str.casefold().eq("other")
    other_columns = ["name", "pack_size_label"]
    print(f"\n15 random rows with form='other' ({int(other_form.sum()):,} total):")
    if other_form.any():
        print(random_rows(data.loc[other_form], 15, other_columns).to_string(index=False))
    else:
        print("<none>")

    price_per_unit = pd.to_numeric(data["price_per_unit"], errors="coerce")
    valid_prices = data.loc[price_per_unit.notna() & price_per_unit.gt(0)].copy()
    valid_prices["price_per_unit"] = price_per_unit.loc[valid_prices.index]
    top_count = min(len(valid_prices), max(1, math.ceil(len(valid_prices) * 0.001)))
    top_subset = valid_prices.nlargest(top_count, "price_per_unit")
    price_columns = ["name", "price(₹)", "pack_size_label", "pack_units", "price_per_unit"]
    print(f"\n10 random rows in the top 0.1% of positive price_per_unit ({len(top_subset):,} rows):")
    if top_subset.empty:
        print("<none>")
    else:
        print(random_rows(top_subset, 10, price_columns).to_string(index=False))

    dolo_matches = data.loc[names.str.contains(r"\bdolo\s+650\b", case=False, na=False)]
    print("\nMembers of each group containing 'Dolo 650':")
    if dolo_matches.empty:
        print("<Dolo 650 not found>")
    else:
        group_keys = dolo_matches[GROUP_COLUMNS].drop_duplicates()
        for _, key in group_keys.iterrows():
            same_group = pd.Series(True, index=data.index)
            for column in GROUP_COLUMNS:
                value = key[column]
                same_group &= data[column].isna() if pd.isna(value) else data[column].eq(value)
            members = data.loc[same_group]
            print(
                f"\nGroup: salt_key={key['salt_key']!r}, form={key['form']!r}, "
                f"form_variant={key['form_variant']!r} ({len(members):,} members)"
            )
            print(
                members[["name", "manufacturer_name", "price(₹)", "price_per_unit"]]
                .to_string(index=False)
            )


if __name__ == "__main__":
    main()
