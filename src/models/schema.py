"""
Standardized data models for the Travel Expense Extraction Agent.

Every extractor (image/OCR, PDF, Excel/CSV) must produce records that
conform to ExpenseRecord. This is the single contract the rest of the
pipeline (validation, categorization, reporting) relies on.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    IMAGE = "image"
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    TEXT = "text"


class ExpenseCategory(str, Enum):
    TRAVEL = "travel"
    LODGING = "lodging"
    FOOD = "food"
    TRANSPORT = "transport"
    COMMUNICATION = "communication"
    OFFICE_SUPPLIES = "office_supplies"
    CLIENT_ENTERTAINMENT = "client_entertainment"
    MISCELLANEOUS = "miscellaneous"
    UNCATEGORIZED = "uncategorized"


class ValidationFlag(str, Enum):
    OK = "ok"
    MISSING_FIELD = "missing_field"
    DATE_AMBIGUOUS = "date_ambiguous"
    DATE_OUT_OF_RANGE = "date_out_of_range"
    AMOUNT_SUSPICIOUS = "amount_suspicious"
    CURRENCY_MISMATCH = "currency_mismatch"
    POSSIBLE_DUPLICATE = "possible_duplicate"
    LOW_OCR_CONFIDENCE = "low_ocr_confidence"
    UNPARSEABLE = "unparseable"


class ExpenseRecord(BaseModel):
    """A single standardized expense line item."""

    record_id: str = Field(..., description="Stable hash-based ID for dedup")
    source_file: str
    source_type: SourceType

    vendor: Optional[str] = None
    expense_date: Optional[date] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = Field(default=None, description="ISO 4217, e.g. INR, USD")

    category: ExpenseCategory = ExpenseCategory.UNCATEGORIZED
    payment_mode: Optional[str] = None
    employee: Optional[str] = None
    description: Optional[str] = None

    # Confidence + trust surface (never let the LLM silently overwrite this)
    field_confidence: dict[str, float] = Field(default_factory=dict)
    extraction_method: str = Field(..., description="e.g. groq_vision, tesseract, pdf_text, excel_direct")

    flags: list[ValidationFlag] = Field(default_factory=list)
    raw_text: Optional[str] = Field(default=None, description="Original extracted text, for audit trail")

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.strip().upper()

    @field_validator("amount")
    @classmethod
    def amount_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("amount cannot be negative")
        return v

    def is_clean(self) -> bool:
        return not self.flags or self.flags == [ValidationFlag.OK]


class BatchSummary(BaseModel):
    """Aggregated summary for a full extraction run, feeds the report's summary tab."""

    total_records: int = 0
    clean_records: int = 0
    flagged_records: int = 0
    total_amount_by_currency: dict[str, Decimal] = Field(default_factory=dict)
    total_by_category: dict[str, Decimal] = Field(default_factory=dict)
    duplicate_count: int = 0
