"""
Category classification.

One LLM call per batch (chunked by CATEGORIZATION_BATCH_SIZE), not per
record -- same call-budget discipline as the Suproc matching agent
(2 LLM calls per request, deterministic scoring for everything else).
Categorization is inherently fuzzy/judgment-based, which is exactly the
kind of task worth spending an LLM call on; extraction math is not.
"""

from __future__ import annotations

import json

from src import config
from src.models.schema import ExpenseCategory, ExpenseRecord

PROMPT_TEMPLATE = """Classify each of the following business expense items into exactly one
of these categories: travel, lodging, food, transport, communication, office_supplies,
client_entertainment, miscellaneous.

Return a strict JSON object mapping each item's index (as a string) to its category.
No markdown fences, no commentary.

ITEMS:
{items}
"""


def _format_items(records: list[ExpenseRecord]) -> str:
    lines = []
    for i, r in enumerate(records):
        desc = r.description or r.vendor or "unknown"
        lines.append(f"{i}: {desc}")
    return "\n".join(lines)


def _call_groq_categorize(records: list[ExpenseRecord]) -> dict[str, str]:
    if not config.GROQ_API_KEY or not records:
        return {}

    try:
        from groq import Groq
    except ImportError:
        return {}

    try:
        client = Groq(api_key=config.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=config.GROQ_TEXT_MODEL,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(items=_format_items(records))}],
            temperature=0,
            max_tokens=1000,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)
    except Exception as e:  # noqa: BLE001
        print(f"[categorizer] Groq categorization failed ({e}); leaving records uncategorized")
        return {}


def categorize_batch(records: list[ExpenseRecord]) -> list[ExpenseRecord]:
    chunk_size = config.CATEGORIZATION_BATCH_SIZE

    for start in range(0, len(records), chunk_size):
        chunk = records[start:start + chunk_size]
        result = _call_groq_categorize(chunk)

        for i, record in enumerate(chunk):
            category_str = result.get(str(i))
            if category_str:
                try:
                    record.category = ExpenseCategory(category_str.lower().strip())
                except ValueError:
                    record.category = ExpenseCategory.UNCATEGORIZED

    return records
