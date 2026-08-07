"""Central config. Reads from environment variables (.env supported via python-dotenv)."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# NOTE: Groq deprecates vision models periodically (we hit this once already
# with the Suproc catalog agent). Keep this as a config value, not a hardcoded
# literal in extractor code, so a decommission is a one-line fix.
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-90b-vision-preview")
GROQ_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.3-70b-versatile")

# If Groq vision fails (rate limit, decommission, network), fall back to local OCR.
ENABLE_TESSERACT_FALLBACK = os.getenv("ENABLE_TESSERACT_FALLBACK", "true").lower() == "true"

# Categorization is done once per BATCH, not per record, to control LLM call volume.
CATEGORIZATION_BATCH_SIZE = int(os.getenv("CATEGORIZATION_BATCH_SIZE", "20"))

# Date sanity bounds for validation (flag anything outside this window).
EXPENSE_DATE_MIN_YEARS_BACK = int(os.getenv("EXPENSE_DATE_MIN_YEARS_BACK", "2"))
EXPENSE_DATE_MAX_DAYS_FUTURE = int(os.getenv("EXPENSE_DATE_MAX_DAYS_FUTURE", "1"))

# Amount sanity bound (flag anything above this as "suspicious", not reject).
AMOUNT_SUSPICIOUS_THRESHOLD = float(os.getenv("AMOUNT_SUSPICIOUS_THRESHOLD", "100000"))

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
