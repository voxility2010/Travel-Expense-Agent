from datetime import date
from decimal import Decimal

from src.models.schema import ExpenseRecord, SourceType, ValidationFlag
from src.validators.rules import flag_duplicates, validate_batch, validate_record


def make_record(**overrides) -> ExpenseRecord:
    defaults = dict(
        record_id="abc123",
        source_file="test.csv",
        source_type=SourceType.CSV,
        vendor="Uber",
        expense_date=date(2026, 1, 15),
        amount=Decimal("640"),
        currency="INR",
        extraction_method="csv_direct",
    )
    defaults.update(overrides)
    return ExpenseRecord(**defaults)


def test_clean_record_gets_ok_flag():
    r = validate_record(make_record(), today=date(2026, 1, 20))
    assert r.flags == [ValidationFlag.OK]


def test_missing_amount_flagged():
    r = validate_record(make_record(amount=None), today=date(2026, 1, 20))
    assert ValidationFlag.MISSING_FIELD in r.flags


def test_future_date_flagged():
    r = validate_record(make_record(expense_date=date(2026, 6, 1)), today=date(2026, 1, 20))
    assert ValidationFlag.DATE_OUT_OF_RANGE in r.flags


def test_old_date_flagged():
    r = validate_record(make_record(expense_date=date(2020, 1, 1)), today=date(2026, 1, 20))
    assert ValidationFlag.DATE_OUT_OF_RANGE in r.flags


def test_suspicious_amount_flagged():
    r = validate_record(make_record(amount=Decimal("500000")), today=date(2026, 1, 20))
    assert ValidationFlag.AMOUNT_SUSPICIOUS in r.flags


def test_bad_currency_code_flagged():
    r = validate_record(make_record(currency="XY1"), today=date(2026, 1, 20))
    assert ValidationFlag.CURRENCY_MISMATCH in r.flags


def test_duplicates_flagged_across_batch():
    r1 = make_record(record_id="dup1")
    r2 = make_record(record_id="dup1")
    r3 = make_record(record_id="unique1")
    result = flag_duplicates([r1, r2, r3])
    assert ValidationFlag.POSSIBLE_DUPLICATE in result[0].flags
    assert ValidationFlag.POSSIBLE_DUPLICATE in result[1].flags
    assert ValidationFlag.POSSIBLE_DUPLICATE not in result[2].flags


def test_validate_batch_end_to_end():
    records = [make_record(record_id="a"), make_record(record_id="a", amount=None)]
    result = validate_batch(records)
    assert len(result) == 2
    assert ValidationFlag.POSSIBLE_DUPLICATE in result[0].flags
