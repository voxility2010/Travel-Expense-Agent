"""
Streamlit UI for the Travel Expense Extraction Agent.

Designed to run both locally (`streamlit run app.py`) and on Hugging Face
Spaces (Streamlit SDK) with zero changes -- HF Spaces auto-detects app.py
at the repo root and runs it directly.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.categorizer import categorize_batch
from src.models.schema import ValidationFlag
from src.report import build_summary, generate_report
from src.router import route_batch
from src.validators.rules import validate_batch

st.set_page_config(
    page_title="Travel Expense Extraction Agent",
    page_icon="🧾",
    layout="wide",
)

# ---------- Style ----------
st.markdown(
    """
    <style>
    .stApp { max-width: 1100px; margin: 0 auto; }
    .flag-ok { color: #1a7f37; font-weight: 600; }
    .flag-bad { color: #b45309; font-weight: 600; }
    .metric-card {
        background: #f6f8fa; border-radius: 10px; padding: 1rem 1.25rem;
        border: 1px solid #e1e4e8;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🧾 Travel Expense Extraction Agent")
st.caption(
    "Upload receipts, invoices, or expense statements in any mix of formats "
    "— images, PDFs, Excel/CSV, or pasted text — and get back a validated, "
    "categorized expense report."
)

with st.expander("ℹ️ How this works", expanded=False):
    st.markdown(
        """
        1. **Extract** — each file is routed to the right extractor (Groq vision for
           photos, text-layer parsing for PDFs, direct parsing for Excel/CSV).
        2. **Validate** — deterministic checks catch missing fields, suspicious
           amounts, out-of-range dates, and duplicate submissions. No LLM
           involved in this step, so it's fully reproducible.
        3. **Categorize** — a single batched LLM call buckets each expense into
           a category (travel, lodging, food, etc).
        4. **Report** — download a two-tab Excel report: a summary and full
           line items.
        """
    )

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Settings")
    api_key_input = st.text_input(
        "Groq API key (optional)",
        type="password",
        help=(
            "Needed for image/scanned-receipt extraction and category "
            "classification. Without it, the agent still works for Excel/CSV "
            "input and falls back to local OCR for images, just without "
            "categorization."
        ),
    )
    if api_key_input:
        import os
        os.environ["GROQ_API_KEY"] = api_key_input

    st.divider()
    st.markdown(
        "**Supported formats**\n"
        "- 🖼️ Images (jpg, png, webp)\n"
        "- 📄 PDF (digital or scanned)\n"
        "- 📊 Excel / CSV\n"
        "- 📝 Plain text"
    )

# ---------- File upload ----------
uploaded_files = st.file_uploader(
    "Upload expense files",
    accept_multiple_files=True,
    type=["jpg", "jpeg", "png", "webp", "bmp", "pdf", "xlsx", "xls", "csv", "txt"],
)

run_button = st.button("Extract expenses", type="primary", disabled=not uploaded_files)

if run_button and uploaded_files:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_paths = []
        for uf in uploaded_files:
            path = Path(tmp_dir) / uf.name
            path.write_bytes(uf.getbuffer())
            tmp_paths.append(str(path))

        with st.status("Processing expenses...", expanded=True) as status:
            st.write(f"Extracting from {len(tmp_paths)} file(s)...")
            records = route_batch(tmp_paths)
            st.write(f"Extracted {len(records)} record(s).")

            st.write("Validating (dates, amounts, currency, duplicates)...")
            records = validate_batch(records)

            st.write("Categorizing...")
            records = categorize_batch(records)

            report_path = str(Path(tmp_dir) / "expense_report.xlsx")
            generate_report(records, report_path)
            report_bytes = Path(report_path).read_bytes()

            status.update(label="Done", state="complete")

        st.session_state["records"] = records
        st.session_state["report_bytes"] = report_bytes

# ---------- Results ----------
if "records" in st.session_state:
    records = st.session_state["records"]
    summary = build_summary(records)

    st.subheader("Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total records", summary.total_records)
    col2.metric("Clean", summary.clean_records)
    col3.metric("Flagged", summary.flagged_records)
    col4.metric("Duplicates", summary.duplicate_count)

    if summary.total_amount_by_currency:
        st.markdown("**Totals by currency**")
        totals_df = pd.DataFrame(
            [{"Currency": c, "Total": float(v)} for c, v in summary.total_amount_by_currency.items()]
        )
        st.dataframe(totals_df, hide_index=True, use_container_width=True)

    if summary.total_by_category:
        st.markdown("**Totals by category**")
        cat_df = pd.DataFrame(
            [{"Category": c, "Total": float(v)} for c, v in summary.total_by_category.items()]
        )
        st.bar_chart(cat_df.set_index("Category"))

    st.divider()
    st.subheader("Line items")

    rows = []
    for r in records:
        rows.append({
            "Vendor": r.vendor,
            "Date": r.expense_date,
            "Amount": float(r.amount) if r.amount is not None else None,
            "Currency": r.currency,
            "Category": r.category.value,
            "Method": r.extraction_method,
            "Status": "✅ Clean" if r.is_clean() else "⚠️ " + ", ".join(f.value for f in r.flags),
        })
    display_df = pd.DataFrame(rows)
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    st.divider()
    st.download_button(
        "📥 Download full Excel report",
        data=st.session_state["report_bytes"],
        file_name="expense_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

elif not uploaded_files:
    st.info("Upload one or more expense files above to get started.")
