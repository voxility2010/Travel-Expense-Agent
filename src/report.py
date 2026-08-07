"""
Report generator. Produces a two-tab Excel workbook:
  - "Summary": totals by category, totals by currency, flag counts
  - "Line Items": every extracted record, one row per expense
"""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import pandas as pd

from src.models.schema import BatchSummary, ExpenseRecord, ValidationFlag


def build_summary(records: list[ExpenseRecord]) -> BatchSummary:
    summary = BatchSummary(total_records=len(records))

    by_currency: dict[str, Decimal] = defaultdict(Decimal)
    by_category: dict[str, Decimal] = defaultdict(Decimal)

    for r in records:
        is_clean = r.is_clean()
        summary.clean_records += int(is_clean)
        summary.flagged_records += int(not is_clean)

        if ValidationFlag.POSSIBLE_DUPLICATE in r.flags:
            summary.duplicate_count += 1

        if r.amount is not None:
            currency = r.currency or "UNKNOWN"
            by_currency[currency] += r.amount
            by_category[r.category.value] += r.amount

    summary.total_amount_by_currency = dict(by_currency)
    summary.total_by_category = dict(by_category)
    return summary


def _line_items_df(records: list[ExpenseRecord]) -> pd.DataFrame:
    rows = []
    for r in records:
        rows.append({
            "Record ID": r.record_id,
            "Source File": r.source_file,
            "Source Type": r.source_type.value,
            "Vendor": r.vendor,
            "Date": r.expense_date,
            "Amount": float(r.amount) if r.amount is not None else None,
            "Currency": r.currency,
            "Category": r.category.value,
            "Payment Mode": r.payment_mode,
            "Employee": r.employee,
            "Description": r.description,
            "Extraction Method": r.extraction_method,
            "Flags": ", ".join(f.value for f in r.flags),
            "Clean": r.is_clean(),
        })
    return pd.DataFrame(rows)


def _summary_df(summary: BatchSummary) -> pd.DataFrame:
    rows = [
        {"Metric": "Total Records", "Value": summary.total_records},
        {"Metric": "Clean Records", "Value": summary.clean_records},
        {"Metric": "Flagged Records", "Value": summary.flagged_records},
        {"Metric": "Possible Duplicates", "Value": summary.duplicate_count},
        {"Metric": "", "Value": ""},
        {"Metric": "-- Total by Currency --", "Value": ""},
    ]
    for currency, total in summary.total_amount_by_currency.items():
        rows.append({"Metric": currency, "Value": float(total)})

    rows.append({"Metric": "", "Value": ""})
    rows.append({"Metric": "-- Total by Category --", "Value": ""})
    for category, total in summary.total_by_category.items():
        rows.append({"Metric": category, "Value": float(total)})

    return pd.DataFrame(rows)


def generate_report(records: list[ExpenseRecord], output_path: str) -> str:
    summary = build_summary(records)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        _summary_df(summary).to_excel(writer, sheet_name="Summary", index=False)
        _line_items_df(records).to_excel(writer, sheet_name="Line Items", index=False)

        # Auto-width columns for readability
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for column_cells in ws.columns:
                length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
                ws.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 40)

    return output_path
