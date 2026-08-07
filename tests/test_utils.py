from datetime import date
from decimal import Decimal

from src.utils import make_record_id, parse_amount, parse_currency, parse_date_flexible


def test_parse_amount_with_symbol_and_commas():
    assert parse_amount("Rs. 1,240.50") == Decimal("1240.50")


def test_parse_amount_plain():
    assert parse_amount("45.00") == Decimal("45.00")


def test_parse_amount_empty():
    assert parse_amount("") is None


def test_parse_currency_symbol():
    assert parse_currency("₹1,240") == "INR"


def test_parse_currency_code():
    assert parse_currency("USD 45.00") == "USD"


def test_parse_currency_none_found():
    assert parse_currency("1240") is None


def test_parse_date_iso():
    d, ambiguous = parse_date_flexible("2026-01-12")
    assert d == date(2026, 1, 12)


def test_parse_date_ambiguous_dd_mm():
    d, ambiguous = parse_date_flexible("05/03/2026")
    assert ambiguous is True


def test_parse_date_unambiguous_day_over_12():
    d, ambiguous = parse_date_flexible("25/03/2026")
    assert d == date(2026, 3, 25)
    assert ambiguous is False


def test_record_id_stable_across_filenames():
    id1 = make_record_id("receipt_a.jpg", "Uber", date(2026, 1, 12), Decimal("640"))
    id2 = make_record_id("receipt_b.jpg", "Uber", date(2026, 1, 12), Decimal("640"))
    assert id1 == id2


def test_record_id_differs_on_amount():
    id1 = make_record_id("r.jpg", "Uber", date(2026, 1, 12), Decimal("640"))
    id2 = make_record_id("r.jpg", "Uber", date(2026, 1, 12), Decimal("641"))
    assert id1 != id2
