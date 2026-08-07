#!/usr/bin/env python3
"""
Travel Expense Extraction Agent -- CLI entrypoint.

Usage:
    python main.py --input data/receipts/ --output output/report.xlsx
    python main.py --input receipt1.jpg receipt2.pdf statement.csv --output output/report.xlsx

Pipeline:
    1. Route each input file to the right extractor (image/PDF/Excel/CSV/text)
    2. Validate deterministically (dates, amounts, currency, duplicates)
    3. Categorize via a single batched Groq call
    4. Write a two-tab Excel report (Summary + Line Items)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.categorizer import categorize_batch
from src.report import generate_report
from src.router import route_batch
from src.validators.rules import validate_batch


def collect_files(inputs: list[str]) -> list[str]:
    """Expand directories into their contained files; pass through file paths as-is."""
    files = []
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            files.extend(str(f) for f in p.iterdir() if f.is_file())
        elif p.is_file():
            files.append(str(p))
        else:
            print(f"[main] WARNING: '{item}' does not exist, skipping")
    return files


def run(inputs: list[str], output_path: str) -> None:
    files = collect_files(inputs)
    if not files:
        print("[main] No valid input files found. Exiting.")
        sys.exit(1)

    print(f"[main] Extracting from {len(files)} file(s)...")
    records = route_batch(files)
    print(f"[main] Extracted {len(records)} record(s)")

    print("[main] Validating...")
    records = validate_batch(records)

    print("[main] Categorizing...")
    records = categorize_batch(records)

    print(f"[main] Writing report to {output_path}")
    generate_report(records, output_path)

    clean = sum(1 for r in records if r.is_clean())
    print(f"[main] Done. {clean}/{len(records)} records clean, "
          f"{len(records) - clean} flagged for review.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Travel Expense Extraction Agent")
    parser.add_argument("--input", nargs="+", required=True,
                         help="File(s) and/or directories to process")
    parser.add_argument("--output", default="output/expense_report.xlsx",
                         help="Path for the generated Excel report")
    args = parser.parse_args()

    run(args.input, args.output)


if __name__ == "__main__":
    main()
