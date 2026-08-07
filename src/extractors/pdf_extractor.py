"""
PDF extractor.

Strategy: try native text-layer extraction first (fast, free, accurate for
digitally-generated invoices). Only if the PDF has no usable text layer
(i.e. it's a scanned image wrapped in a PDF) do we rasterize the first page
and route it through the image extractor's Groq vision / Tesseract path.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.models.schema import ExpenseRecord, SourceType, ValidationFlag
from src.utils import make_record_id, parse_amount, parse_currency, parse_date_flexible

MIN_CHARS_FOR_TEXT_LAYER = 30  # below this, treat as a scanned/image PDF


def _extract_text_layer(pdf_path: str) -> str:
    try:
        import pdfplumber
    except ImportError as e:
        raise RuntimeError("pdfplumber is required for PDF extraction") from e

    text_chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)
    return "\n".join(text_chunks).strip()


def _rasterize_and_ocr(pdf_path: str) -> list[ExpenseRecord]:
    """Scanned PDF with no text layer -- convert first page to image, reuse image extractor."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        print("[pdf_extractor] pdf2image not installed; cannot OCR scanned PDF")
        return [
            ExpenseRecord(
                record_id=make_record_id(pdf_path, None, None, None),
                source_file=pdf_path,
                source_type=SourceType.PDF,
                extraction_method="failed",
                flags=[ValidationFlag.UNPARSEABLE],
            )
        ]

    from src.extractors.image_extractor import extract_from_image

    images = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=1)
    tmp_path = str(Path(pdf_path).with_suffix(".page1.png"))
    images[0].save(tmp_path)

    records = extract_from_image(tmp_path)
    for r in records:
        r.source_file = pdf_path
        r.source_type = SourceType.PDF
        r.extraction_method = f"pdf_rasterized_{r.extraction_method}"

    Path(tmp_path).unlink(missing_ok=True)
    return records


def _parse_fields_from_text(text: str) -> dict:
    """Regex-based field extraction from a clean PDF text layer (e.g. flight/hotel invoices)."""
    vendor_match = re.search(r"(?:from|billed by|vendor|company)[:\s]+([A-Za-z0-9 &.,'\-]{3,60})", text, re.I)
    date_match = re.search(r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2})", text)
    amount_match = re.search(r"(?:total|grand total|amount due|amount)[:\s]*([₹$€£]?\s?[\d,]+\.?\d*)", text, re.I)

    return {
        "vendor": vendor_match.group(1).strip() if vendor_match else None,
        "date": date_match.group(1) if date_match else None,
        "amount": amount_match.group(1) if amount_match else None,
    }


def extract_from_pdf(pdf_path: str) -> list[ExpenseRecord]:
    text = _extract_text_layer(pdf_path)

    if len(text) < MIN_CHARS_FOR_TEXT_LAYER:
        # No usable text layer -- likely a scanned receipt saved as PDF.
        return _rasterize_and_ocr(pdf_path)

    fields = _parse_fields_from_text(text)
    expense_date, ambiguous = parse_date_flexible(fields.get("date") or "")
    amount = parse_amount(fields.get("amount") or "")
    currency = parse_currency(text)

    record = ExpenseRecord(
        record_id=make_record_id(pdf_path, fields.get("vendor"), expense_date, amount),
        source_file=pdf_path,
        source_type=SourceType.PDF,
        vendor=fields.get("vendor"),
        expense_date=expense_date,
        amount=amount,
        currency=currency,
        extraction_method="pdf_text_layer",
        field_confidence={k: 0.75 for k, v in fields.items() if v},
        raw_text=text[:2000],  # cap stored raw text
    )

    if ambiguous:
        record.flags.append(ValidationFlag.DATE_AMBIGUOUS)
    if not fields.get("amount") or not fields.get("date"):
        record.flags.append(ValidationFlag.MISSING_FIELD)

    return [record]
