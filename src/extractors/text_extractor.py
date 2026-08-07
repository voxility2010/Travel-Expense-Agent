"""
Plain-text extractor -- for pasted/typed expense descriptions (e.g. a
Slack message like "Uber to airport, 640 rs, 12 Jan").

Uses a single lightweight Groq text-completion call per file/batch since
there's no structure to regex against reliably; falls back to regex-only
parsing if Groq is unavailable.
"""

from __future__ import annotations

import json

from src import config
from src.models.schema import ExpenseRecord, SourceType, ValidationFlag
from src.utils import make_record_id, parse_amount, parse_currency, parse_date_flexible

PROMPT_TEMPLATE = """Extract expense line items from the text below. Each line item may be
on its own line or mixed into a sentence. Return a strict JSON list, no markdown fences,
no commentary. Each item:

{{"vendor": "string or null", "date": "string as written or null", "amount": "string or null",
"currency": "3-letter code or null", "description": "string or null"}}

If nothing looks like an expense, return an empty list [].

TEXT:
{text}
"""


def _call_groq_text(text: str) -> list[dict]:
    if not config.GROQ_API_KEY:
        return []

    try:
        from groq import Groq
    except ImportError:
        return []

    try:
        client = Groq(api_key=config.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=config.GROQ_TEXT_MODEL,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(text=text)}],
            temperature=0,
            max_tokens=800,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception as e:  # noqa: BLE001
        print(f"[text_extractor] Groq text extraction failed ({e}); returning empty")
        return []


def extract_from_text(file_path: str) -> list[ExpenseRecord]:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    items = _call_groq_text(text)
    if not items:
        return [
            ExpenseRecord(
                record_id=make_record_id(file_path, None, None, None),
                source_file=file_path,
                source_type=SourceType.TEXT,
                extraction_method="failed",
                flags=[ValidationFlag.UNPARSEABLE],
                raw_text=text[:2000],
            )
        ]

    records = []
    for item in items:
        expense_date, ambiguous = parse_date_flexible(item.get("date") or "")
        amount = parse_amount(item.get("amount") or "")
        currency = item.get("currency") or parse_currency(item.get("amount") or "")

        record = ExpenseRecord(
            record_id=make_record_id(file_path, item.get("vendor"), expense_date, amount),
            source_file=file_path,
            source_type=SourceType.TEXT,
            vendor=item.get("vendor"),
            expense_date=expense_date,
            amount=amount,
            currency=currency,
            description=item.get("description"),
            extraction_method="groq_text",
            field_confidence={k: 0.7 for k in ("vendor", "date", "amount") if item.get(k)},
        )
        if ambiguous:
            record.flags.append(ValidationFlag.DATE_AMBIGUOUS)
        records.append(record)

    return records
