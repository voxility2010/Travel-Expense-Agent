"""
Excel/CSV extractor.

No LLM involved -- these are already structured. We just need to map
whatever column names the source file uses onto our standard schema.
Column name matching is fuzzy (case-insensitive, common synonyms) since
different corporate card exports / bank statements name things differently.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.models.schema import ExpenseRecord, SourceType, ValidationFlag
from src.utils import make_record_id, parse_amount, parse_currency, parse_date_flexible

COLUMN_SYNONYMS = {
    "vendor": {"vendor", "merchant", "payee", "description", "narration", "supplier"},
    "date": {"date", "transaction date", "txn date", "expense date", "posted date"},
    "amount": {"amount", "amt", "debit", "value", "total"},
    "currency": {"currency", "ccy"},
    "payment_mode": {"payment mode", "mode", "card type", "method"},
    "employee": {"employee", "employee name", "cardholder", "name"},
}


def _match_columns(columns: list[str]) -> dict[str, str]:
    """Map our standard field names to whatever the actual column headers are."""
    lower_cols = {c.lower().strip(): c for c in columns}
    mapping = {}
    for field, synonyms in COLUMN_SYNONYMS.items():
        for syn in synonyms:
            if syn in lower_cols:
                mapping[field] = lower_cols[syn]
                break
    return mapping


def extract_from_excel(file_path: str) -> list[ExpenseRecord]:
    ext = Path(file_path).suffix.lower()

    if ext == ".csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    col_map = _match_columns(list(df.columns))
    source_type = SourceType.CSV if ext == ".csv" else SourceType.EXCEL

    records: list[ExpenseRecord] = []

    for _, row in df.iterrows():
        vendor = str(row[col_map["vendor"]]).strip() if "vendor" in col_map and pd.notna(row.get(col_map["vendor"])) else None
        raw_date = str(row[col_map["date"]]) if "date" in col_map and pd.notna(row.get(col_map["date"])) else ""
        raw_amount = str(row[col_map["amount"]]) if "amount" in col_map and pd.notna(row.get(col_map["amount"])) else ""
        currency = str(row[col_map["currency"]]).strip().upper() if "currency" in col_map and pd.notna(row.get(col_map["currency"])) else None
        payment_mode = str(row[col_map["payment_mode"]]).strip() if "payment_mode" in col_map and pd.notna(row.get(col_map["payment_mode"])) else None
        employee = str(row[col_map["employee"]]).strip() if "employee" in col_map and pd.notna(row.get(col_map["employee"])) else None

        expense_date, ambiguous = parse_date_flexible(raw_date)
        amount = parse_amount(raw_amount)
        if currency is None:
            currency = parse_currency(raw_amount)

        record = ExpenseRecord(
            record_id=make_record_id(file_path, vendor, expense_date, amount),
            source_file=file_path,
            source_type=source_type,
            vendor=vendor,
            expense_date=expense_date,
            amount=amount,
            currency=currency,
            payment_mode=payment_mode,
            employee=employee,
            extraction_method="excel_direct" if source_type == SourceType.EXCEL else "csv_direct",
            field_confidence={"vendor": 1.0, "date": 1.0, "amount": 1.0} if vendor else {},
        )

        if ambiguous:
            record.flags.append(ValidationFlag.DATE_AMBIGUOUS)
        if not vendor or expense_date is None or amount is None:
            record.flags.append(ValidationFlag.MISSING_FIELD)

        records.append(record)

    if not col_map.get("amount"):
        print(f"[excel_extractor] WARNING: no 'amount' column matched in {file_path}. "
              f"Columns found: {list(df.columns)}")

    return records
