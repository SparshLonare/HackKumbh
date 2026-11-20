"""Print a read-only summary of the raw medicine CSV."""

import argparse
from pathlib import Path
import sys

import pandas as pd


DEFAULT_CSV = Path(__file__).resolve().parent / "data" / "raw" / "indian_medicine_data.csv"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=DEFAULT_CSV,
        help=f"CSV file to inspect (default: {DEFAULT_CSV})",
    )
    args = parser.parse_args()

    data = pd.read_csv(args.csv_path)

    print(f"File: {args.csv_path}")
    print("\nColumn names:")
    print(data.columns.tolist())
    print("\nDtypes:")
    print(data.dtypes.to_string())

    print(f"\nRow count: {len(data):,}")

    print("\nNull count per column:")
    print(data.isna().sum().to_string())

    print("\n20 random rows:")
    print(data.sample(n=min(20, len(data))).to_string(index=False))

    for column in ("pack_size_label", "type"):
        if column not in data.columns:
            raise KeyError(f"Required column {column!r} is missing from {args.csv_path}")
        print(f"\n40 most common values in {column}:")
        print(data[column].value_counts(dropna=False).head(40).to_string())


if __name__ == "__main__":
    main()
