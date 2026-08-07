"""
Image/scanned-receipt extractor.

Primary path: Groq vision model reads the receipt and returns structured JSON.
Fallback path: Tesseract OCR (local, no API) + regex parsing, used when Groq
vision fails or is unavailable -- this fallback exists specifically because
the Suproc catalog agent broke in production when a Groq vision model was
decommissioned without warning. Never assume the primary path is available.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Optional

from src import config
from src.models.schema import ExpenseRecord, SourceType
from src.utils import make_record_id, parse_amount, parse_currency, parse_date_flexible

EXTRACTION_PROMPT = """You are looking at a photo of a travel/business expense receipt.
Extract the following fields as strict JSON, with no markdown fences and no commentary:

{
  "vendor": "string or null",
  "date": "string as printed on receipt, or null",
  "amount": "string as printed (numbers only ok), or null",
  "currency": "3-letter code if identifiable, or null",
  "payment_mode": "string (cash/card/upi/etc) or null",
  "description": "short string describing what was purchased, or null"
}

If a field is not visible or not present, use null. Do not guess or invent values."""


def _encode_image(path: str) -> tuple[str, str]:
    ext = Path(path).suffix.lower().lstrip(".")
    media_type = "jpeg" if ext == "jpg" else ext
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, f"image/{media_type}"


def _call_groq_vision(image_path: str) -> Optional[dict]:
    """Returns parsed field dict from Groq vision, or None if it fails for any reason."""
    if not config.GROQ_API_KEY:
        return None

    try:
        from groq import Groq
    except ImportError:
        return None

    try:
        b64_data, media_type = _encode_image(image_path)
        client = Groq(api_key=config.GROQ_API_KEY)

        response = client.chat.completions.create(
            model=config.GROQ_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{media_type};base64,{b64_data}"},
                        },
                    ],
                }
            ],
            temperature=0,
            max_tokens=500,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)
    except Exception as e:  # noqa: BLE001 - any failure here should trigger fallback, not crash
        print(f"[image_extractor] Groq vision failed ({e}); falling back to Tesseract OCR")
        return None


def _call_tesseract_fallback(image_path: str) -> Optional[dict]:
    """Local OCR fallback. Lower accuracy, no field structure -- we regex the raw text."""
    if not config.ENABLE_TESSERACT_FALLBACK:
        return None

    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        print("[image_extractor] pytesseract/Pillow not installed; cannot fall back")
        return None

    try:
        text = pytesseract.image_to_string(Image.open(image_path))
    except Exception as e:  # noqa: BLE001
        print(f"[image_extractor] Tesseract OCR failed: {e}")
        return None

    # Very light heuristic parsing from raw OCR text -- this is intentionally
    # conservative. We'd rather leave a field null (and flagged downstream)
    # than fabricate a confident-looking wrong value.
    import re

    amount_match = re.search(r"(?:total|amount|rs\.?|inr|\$)\s*[:\-]?\s*([\d,]+\.?\d*)", text, re.I)
    date_match = re.search(r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})", text)

    return {
        "vendor": None,  # too unreliable to guess from raw OCR without an LLM pass
        "date": date_match.group(1) if date_match else None,
        "amount": amount_match.group(1) if amount_match else None,
        "currency": parse_currency(text),
        "payment_mode": None,
        "description": None,
        "_raw_ocr_text": text.strip(),
    }


def extract_from_image(image_path: str) -> list[ExpenseRecord]:
    fields = _call_groq_vision(image_path)
    method = "groq_vision"

    if fields is None:
        fields = _call_tesseract_fallback(image_path)
        method = "tesseract_fallback"

    if fields is None:
        # Both paths failed. Return a stub record flagged for manual review
        # rather than silently dropping the receipt.
        from src.models.schema import ValidationFlag

        return [
            ExpenseRecord(
                record_id=make_record_id(image_path, None, None, None),
                source_file=image_path,
                source_type=SourceType.IMAGE,
                extraction_method="failed",
                flags=[ValidationFlag.UNPARSEABLE],
            )
        ]

    expense_date, ambiguous = parse_date_flexible(fields.get("date") or "")
    amount = parse_amount(fields.get("amount") or "")
    currency = fields.get("currency") or parse_currency(fields.get("amount") or "")

    confidence = {}
    if method == "tesseract_fallback":
        # Fallback OCR gets flat lower confidence across the board since it's
        # regex-based, not model-verified.
        confidence = {"vendor": 0.0, "date": 0.5, "amount": 0.5, "currency": 0.4}
    else:
        confidence = {k: 0.85 for k in ("vendor", "date", "amount", "currency") if fields.get(k)}

    record = ExpenseRecord(
        record_id=make_record_id(image_path, fields.get("vendor"), expense_date, amount),
        source_file=image_path,
        source_type=SourceType.IMAGE,
        vendor=fields.get("vendor"),
        expense_date=expense_date,
        amount=amount,
        currency=currency,
        payment_mode=fields.get("payment_mode"),
        description=fields.get("description"),
        extraction_method=method,
        field_confidence=confidence,
        raw_text=fields.get("_raw_ocr_text"),
    )

    if ambiguous:
        from src.models.schema import ValidationFlag
        record.flags.append(ValidationFlag.DATE_AMBIGUOUS)

    return [record]
