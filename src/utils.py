"""Shared utility helpers used across extractors."""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

# Common currency symbols/codes seen in receipts, mapped to ISO 4217.
CURRENCY_MAP = {
    "₹": "INR", "RS": "INR", "RS.": "INR", "INR": "INR",
    "$": "USD", "USD": "USD",
    "€": "EUR", "EUR": "EUR",
    "£": "GBP", "GBP": "GBP",
}

DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%m/%d/%Y", "%m-%d-%Y",
    "%Y-%m-%d", "%Y/%m/%d",
    "%d %b %Y", "%d %B %Y",
    "%b %d, %Y", "%B %d, %Y",
]


def make_record_id(source_file: str, vendor: Optional[str], expense_date: Optional[date],
                    amount: Optional[Decimal]) -> str:
    """
    Stable hash for duplicate detection. Deliberately excludes source_file
    from the hash content itself (only uses it as salt-free context) so the
    SAME receipt uploaded under two different filenames still collides.
    """
    key = f"{vendor or ''}|{expense_date or ''}|{amount or ''}".lower().strip()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def parse_amount(raw: str) -> Optional[Decimal]:
    """Extract a decimal amount from a noisy string like 'Rs. 1,240.50' or 'USD 45.00'."""
    if not raw:
        return None
    # Pull out the first proper number pattern (digits, optional thousands
    # commas, optional single decimal point) rather than stripping all
    # non-numeric chars, which breaks on things like "Rs." (the period
    # would otherwise get mistaken for a decimal separator).
    match = re.search(r"\d[\d,]*\.?\d*", raw)
    if not match:
        return None
    cleaned = match.group(0).replace(",", "")
    if not cleaned or cleaned == ".":
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_currency(raw: str) -> Optional[str]:
    """Detect currency code from symbols or text in a string."""
    if not raw:
        return None
    upper = raw.upper()
    for symbol, code in CURRENCY_MAP.items():
        if symbol in raw or symbol in upper:
            return code
    return None


def parse_date_flexible(raw: str) -> tuple[Optional[date], bool]:
    """
    Try known formats. Returns (parsed_date, is_ambiguous).
    is_ambiguous=True when a DD/MM vs MM/DD format could plausibly parse
    two different ways (day <= 12), so downstream validation can flag it.
    """
    if not raw:
        return None, False

    raw = raw.strip()
    ambiguous = False

    # Detect DD/MM vs MM/DD ambiguity before committing to a format
    slash_match = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$", raw)
    if slash_match:
        a, b, _ = slash_match.groups()
        if int(a) <= 12 and int(b) <= 12 and a != b:
            ambiguous = True

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date(), ambiguous
        except ValueError:
            continue

    return None, ambiguous
