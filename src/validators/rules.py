"""
Deterministic validation layer. No LLM involved here on purpose --
the money math and duplicate/date/amount sanity checks must be
reproducible and auditable, same principle as the 5-component scorer
in the Suproc procurement-matching agent.
"""

from __future__ import annotations

from datetime import date, timedelta

from src import config
from src.models.schema import ExpenseRecord, ValidationFlag


def validate_record(record: ExpenseRecord, today: date | None = None) -> ExpenseRecord:
    today = today or date.today()

    # Missing critical fields
    if record.amount is None or record.expense_date is None or not record.vendor:
        if ValidationFlag.MISSING_FIELD not in record.flags:
            record.flags.append(ValidationFlag.MISSING_FIELD)

    # Date sanity window
    if record.expense_date is not None:
        earliest = date(today.year - config.EXPENSE_DATE_MIN_YEARS_BACK, today.month, today.day)
        latest = today + timedelta(days=config.EXPENSE_DATE_MAX_DAYS_FUTURE)
        if record.expense_date < earliest or record.expense_date > latest:
            record.flags.append(ValidationFlag.DATE_OUT_OF_RANGE)

    # Amount sanity
    if record.amount is not None and float(record.amount) > config.AMOUNT_SUSPICIOUS_THRESHOLD:
        record.flags.append(ValidationFlag.AMOUNT_SUSPICIOUS)

    # Currency present but unrecognized shape (not 3-letter code)
    if record.currency and (len(record.currency) != 3 or not record.currency.isalpha()):
        record.flags.append(ValidationFlag.CURRENCY_MISMATCH)

    # Low confidence fields (from OCR fallback etc.)
    low_conf_fields = [f for f, c in record.field_confidence.items() if c < 0.5]
    if low_conf_fields:
        record.flags.append(ValidationFlag.LOW_OCR_CONFIDENCE)

    if not record.flags:
        record.flags.append(ValidationFlag.OK)

    return record


def flag_duplicates(records: list[ExpenseRecord]) -> list[ExpenseRecord]:
    """Hash-based dedup using record_id (built from vendor+date+amount)."""
    seen: dict[str, int] = {}
    for r in records:
        seen[r.record_id] = seen.get(r.record_id, 0) + 1

    for r in records:
        if seen[r.record_id] > 1:
            if ValidationFlag.OK in r.flags:
                r.flags.remove(ValidationFlag.OK)
            r.flags.append(ValidationFlag.POSSIBLE_DUPLICATE)

    return records


def validate_batch(records: list[ExpenseRecord]) -> list[ExpenseRecord]:
    validated = [validate_record(r) for r in records]
    return flag_duplicates(validated)
