---
title: Travel Expense Extraction Agent
emoji: 🧾
colorFrom: yellow
colorTo: gray
sdk: streamlit
sdk_version: 1.37.0
app_file: app.py
pinned: false
---

# Travel Expense Extraction Agent

Turns a messy pile of travel expense evidence — photographed receipts, PDF
invoices, corporate card CSV/Excel exports, even pasted text — into one
clean, validated Excel report with a summary tab and a full line-item tab.

Built for Suproc. Follows the same design principles as the Supplier Data
Clean-Up Agent and the procurement-matching agent: LLM calls are used only
where judgment is genuinely required (reading a receipt image, categorizing
a line item), while all the money math — date sanity, duplicate detection,
amount checks — is deterministic and auditable.

## How it works

```
Input files (image/PDF/Excel/CSV/text)
        │
        ▼
  Router (src/router.py) — detects file type, dispatches to extractor
        │
        ├── Image  → Groq vision, falls back to Tesseract OCR on failure
        ├── PDF    → text-layer extraction first; rasterize + OCR only if
        │            the PDF has no usable text layer (i.e. scanned)
        ├── Excel/CSV → direct pandas parsing, fuzzy column-name matching
        └── Text   → single Groq call to pull structured items from prose
        │
        ▼
  Standardized ExpenseRecord (src/models/schema.py) — one schema, regardless
  of source
        │
        ▼
  Deterministic validation (src/validators/rules.py)
    - missing fields, date range sanity, amount sanity
    - currency code shape check
    - hash-based duplicate detection (vendor + date + amount)
        │
        ▼
  Categorization (src/categorizer.py) — one Groq call per batch of 20,
  not per record
        │
        ▼
  Excel report (src/report.py) — Summary tab + Line Items tab
```

## Why it's built this way

- **Extraction fallbacks are not optional.** Groq vision models get
  decommissioned without much warning — this bit the Supplier Data
  Clean-Up Agent in production. Every image-based extraction path here has
  a local Tesseract OCR fallback baked in from day one.
- **Validation never touches an LLM.** Date ambiguity, duplicate detection,
  and amount sanity checks are pure Python. Reproducible, testable, no
  hallucination risk on the numbers that actually matter.
- **Confidence, not pass/fail.** Every field carries a confidence score.
  Low-confidence OCR output gets flagged for human review rather than
  silently accepted.
- **LLM call budget is deliberate.** Categorization runs once per batch of
  20 records, not once per record — same discipline as the matching agent's
  2-calls-per-request budget.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # add your GROQ_API_KEY
```

For image/scanned-PDF extraction you'll also need Tesseract and poppler
installed at the OS level (for the OCR fallback and PDF rasterization):

```bash
# Debian/Ubuntu
sudo apt install tesseract-ocr poppler-utils
```

## Usage

### Web UI (recommended)

```bash
streamlit run app.py
```

Opens a browser UI where you drag-and-drop files, watch extraction/validation/
categorization progress live, review results in-browser, and download the
Excel report.

### CLI

```bash
# Process a folder of mixed files
python main.py --input data/receipts/ --output output/report.xlsx

# Process specific files
python main.py --input receipt1.jpg invoice.pdf statement.csv --output output/report.xlsx
```

## Live demo

Deployed on Hugging Face Spaces: **[add Space URL here after deploying]**

### Deploying your own copy to Hugging Face Spaces

1. Create a new Space at [huggingface.co/new-space](https://huggingface.co/new-space),
   SDK: **Streamlit**.
2. Push this repo's contents to the Space's git remote (same as pushing to GitHub —
   Spaces are git repos).
3. In the Space's **Settings → Repository secrets**, add `GROQ_API_KEY`.
4. The Space auto-builds from `requirements.txt` and `packages.txt` (the latter
   installs `tesseract-ocr` and `poppler-utils` for OCR/PDF fallback) and serves
   `app.py`.

The generated report has two tabs:
- **Summary** — total records, clean vs. flagged counts, duplicate count,
  totals by currency, totals by category
- **Line Items** — every extracted expense with vendor, date, amount,
  category, extraction method, and any validation flags

## Running tests

```bash
pytest tests/ -v
```

22 tests covering the amount/date/currency parsers, the deterministic
validation rules, and the Excel/CSV extractor's column-matching logic.

## Project structure

```
travel-expense-agent/
├── main.py                      # CLI entrypoint
├── src/
│   ├── config.py                # env-driven settings
│   ├── router.py                # file-type detection + dispatch
│   ├── categorizer.py           # batched LLM categorization
│   ├── report.py                # Excel report generation
│   ├── utils.py                 # amount/date/currency parsing helpers
│   ├── models/
│   │   └── schema.py            # ExpenseRecord, BatchSummary, enums
│   ├── extractors/
│   │   ├── image_extractor.py   # Groq vision + Tesseract fallback
│   │   ├── pdf_extractor.py     # text-layer extraction + OCR fallback
│   │   ├── excel_extractor.py   # pandas-based, fuzzy column matching
│   │   └── text_extractor.py    # Groq-based extraction from prose
│   └── validators/
│       └── rules.py             # deterministic validation + dedup
├── tests/
├── data/sample_receipts/        # sample CSV + text for smoke testing
└── output/                      # generated reports land here
```

## Known limitations / next steps

- Tesseract fallback is regex-based and cannot reliably infer `vendor` —
  it's left null and flagged for review rather than guessed.
- Multi-page PDFs currently only rasterize page 1 if there's no text layer;
  fine for single-page receipts, would need extending for multi-page
  scanned invoices.
- No currency conversion — amounts are reported in their original currency,
  grouped separately in the summary tab.
- No persistence layer yet (each run is stateless); duplicate detection
  only works within a single batch, not across historical runs. Worth
  adding a small SQLite store if this needs to catch dupes across separate
  submission batches.
