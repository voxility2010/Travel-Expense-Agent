"""
Input router: detects file type by extension/content and dispatches to
the correct extractor. This mirrors the pattern used in the Suproc
Supplier Data Clean-Up Agent's ingestion layer.
"""

from __future__ import annotations

from pathlib import Path

from src.models.schema import ExpenseRecord, SourceType
from src.extractors.image_extractor import extract_from_image
from src.extractors.pdf_extractor import extract_from_pdf
from src.extractors.excel_extractor import extract_from_excel
from src.extractors.text_extractor import extract_from_text

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
PDF_EXTS = {".pdf"}
EXCEL_EXTS = {".xlsx", ".xls", ".csv"}
TEXT_EXTS = {".txt"}


class UnsupportedFileType(Exception):
    pass


def route_file(file_path: str) -> list[ExpenseRecord]:
    """Detect the file type and return standardized ExpenseRecord(s)."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext in IMAGE_EXTS:
        return extract_from_image(str(path))
    if ext in PDF_EXTS:
        return extract_from_pdf(str(path))
    if ext in EXCEL_EXTS:
        return extract_from_excel(str(path))
    if ext in TEXT_EXTS:
        return extract_from_text(str(path))

    raise UnsupportedFileType(
        f"'{ext}' is not supported. Supported: images, PDF, Excel/CSV, text."
    )


def route_batch(file_paths: list[str]) -> list[ExpenseRecord]:
    """Run route_file across a batch, collecting failures rather than crashing the run."""
    all_records: list[ExpenseRecord] = []
    errors: list[tuple[str, str]] = []

    for fp in file_paths:
        try:
            all_records.extend(route_file(fp))
        except Exception as e:  # noqa: BLE001 - we want to keep going on batch runs
            errors.append((fp, str(e)))

    if errors:
        print(f"[router] {len(errors)} file(s) failed extraction:")
        for fp, err in errors:
            print(f"  - {fp}: {err}")

    return all_records
