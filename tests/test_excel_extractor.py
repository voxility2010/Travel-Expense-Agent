import pandas as pd
import pytest

from src.extractors.excel_extractor import extract_from_excel
from src.models.schema import ValidationFlag


@pytest.fixture
def sample_csv(tmp_path):
    df = pd.DataFrame([
        {"Date": "12/01/2026", "Merchant": "Uber", "Amount": "640", "Currency": "INR", "Employee": "Vardha"},
        {"Date": "13/01/2026", "Merchant": "Indigo Airlines", "Amount": "5400", "Currency": "INR", "Employee": "Vardha"},
        {"Date": "", "Merchant": "", "Amount": "", "Currency": "", "Employee": ""},
    ])
    path = tmp_path / "statement.csv"
    df.to_csv(path, index=False)
    return str(path)


def test_extracts_all_rows(sample_csv):
    records = extract_from_excel(sample_csv)
    assert len(records) == 3


def test_maps_synonym_columns(sample_csv):
    records = extract_from_excel(sample_csv)
    assert records[0].vendor == "Uber"
    assert records[0].amount == 640
    assert records[0].currency == "INR"
    assert records[0].employee == "Vardha"


def test_empty_row_flagged_missing(sample_csv):
    records = extract_from_excel(sample_csv)
    assert ValidationFlag.MISSING_FIELD in records[2].flags
