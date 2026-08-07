"""
Streamlit UI for the Travel Expense Extraction Agent.

Designed to run both locally (`streamlit run app.py`) and on any Docker-based
host (Render, etc) with zero changes.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.categorizer import categorize_batch
from src.report import build_summary, generate_report
from src.router import route_batch
from src.validators.rules import validate_batch

st.set_page_config(
    page_title="Travel Expense Extraction Agent",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Design tokens
#   Background:  #F5F7FB (soft blue-white)
#   Surface:     #FFFFFF
#   Border:      #E3E8F1
#   Accent:      #2F5CFF
#   Accent dark: #1E3FCC
#   Text:        #101828 (primary) / #667085 (secondary)
#   Success:     #17803D / bg #ECFDF3
#   Warning:     #B54708 / bg #FFFAEB
#   Type:        Inter (UI), IBM Plex Mono (data / labels)
# ============================================================

st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background: #F5F7FB; }
    .block-container { max-width: 1080px; padding-top: 2rem; }

    code, .mono { font-family: 'IBM Plex Mono', monospace; }

    /* ---- Header ---- */
    .app-header {
        display: flex; align-items: center; gap: 14px;
        margin-bottom: 4px;
    }
    .app-header .badge {
        width: 44px; height: 44px; border-radius: 12px;
        background: linear-gradient(135deg, #2F5CFF, #1E3FCC);
        display: flex; align-items: center; justify-content: center;
        font-size: 22px; flex-shrink: 0;
        box-shadow: 0 4px 12px rgba(47,92,255,0.25);
    }
    .app-header h1 {
        font-size: 1.5rem; font-weight: 700; color: #101828;
        margin: 0; line-height: 1.2;
    }
    .app-header .eyebrow {
        font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem;
        font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
        color: #2F5CFF; margin: 0 0 2px 0;
    }
    .app-subtitle {
        color: #667085; font-size: 0.95rem; margin: 6px 0 28px 0;
        max-width: 640px; line-height: 1.5;
    }

    /* ---- Cards ---- */
    .card {
        background: #FFFFFF; border: 1px solid #E3E8F1; border-radius: 14px;
        padding: 20px 22px; margin-bottom: 18px;
    }
    .card-title {
        font-weight: 600; font-size: 0.95rem; color: #101828;
        margin-bottom: 14px; display: flex; align-items: center; gap: 8px;
    }

    /* ---- KPI tiles ---- */
    .kpi-row { display: flex; gap: 14px; margin-bottom: 18px; flex-wrap: wrap; }
    .kpi {
        flex: 1; min-width: 140px;
        background: #FFFFFF; border: 1px solid #E3E8F1; border-radius: 14px;
        padding: 16px 18px;
    }
    .kpi-label {
        font-size: 0.72rem; font-weight: 600; letter-spacing: 0.06em;
        text-transform: uppercase; color: #667085; margin-bottom: 6px;
    }
    .kpi-value {
        font-family: 'IBM Plex Mono', monospace; font-size: 1.6rem;
        font-weight: 600; color: #101828;
    }
    .kpi-value.accent { color: #2F5CFF; }
    .kpi-value.good { color: #17803D; }
    .kpi-value.warn { color: #B54708; }

    /* ---- Status chips ---- */
    .chip {
        display: inline-block; padding: 3px 10px; border-radius: 999px;
        font-size: 0.78rem; font-weight: 600;
    }
    .chip-ok { background: #ECFDF3; color: #17803D; }
    .chip-warn { background: #FFFAEB; color: #B54708; }

    /* ---- Upload zone ---- */
    section[data-testid="stFileUploaderDropzone"] {
        background: #FFFFFF; border: 1.5px dashed #C7D2E8; border-radius: 14px;
    }

    /* ---- Buttons ---- */
    .stButton > button, .stDownloadButton > button {
        border-radius: 10px; font-weight: 600; border: none;
    }
    .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
        background: #2F5CFF;
    }
    .stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {
        background: #1E3FCC;
    }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: #FFFFFF; border-right: 1px solid #E3E8F1;
    }
    section[data-testid="stSidebar"] h2 {
        font-size: 0.95rem; font-weight: 700; color: #101828;
    }

    /* ---- Dataframe ---- */
    [data-testid="stDataFrame"] { border: 1px solid #E3E8F1; border-radius: 12px; }

    hr { border-color: #E3E8F1; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Header ----------
st.markdown(
    """
    <div class="app-header">
        <div class="badge">🧾</div>
        <div>
            <p class="eyebrow">Suproc Agent Marketplace</p>
            <h1>Travel Expense Extraction Agent</h1>
        </div>
    </div>
    <p class="app-subtitle">
        Upload receipts, invoices, or expense statements in any mix of formats —
        images, PDFs, Excel/CSV, or pasted text — and get back a validated,
        categorized expense report in seconds.
    </p>
    """,
    unsafe_allow_html=True,
)

with st.expander("How this agent works", expanded=False):
    st.markdown(
        """
        **1. Extract** — each file is routed to the right extractor (Groq vision for
        photos, text-layer parsing for PDFs, direct parsing for Excel/CSV).

        **2. Validate** — deterministic checks catch missing fields, suspicious
        amounts, out-of-range dates, and duplicate submissions. No LLM involved
        in this step, so it's fully reproducible and auditable.

        **3. Categorize** — a single batched LLM call buckets each expense into
        a category (travel, lodging, food, etc).

        **4. Report** — download a two-tab Excel report: a summary and full
        line items.
        """
    )

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## Settings")
    api_key_input = st.text_input(
        "Groq API key",
        type="password",
        placeholder="gsk_...",
        help=(
            "Needed for image/scanned-receipt extraction and category "
            "classification. Without it, the agent still works for Excel/CSV "
            "input and falls back to local OCR for images, just without "
            "categorization."
        ),
    )
    if api_key_input:
        os.environ["GROQ_API_KEY"] = api_key_input

    st.divider()
    st.markdown("**Supported formats**")
    st.markdown(
        """
        - 🖼️ Images (jpg, png, webp)
        - 📄 PDF (digital or scanned)
        - 📊 Excel / CSV
        - 📝 Plain text
        """
    )
    st.divider()
    st.caption("Built for the Suproc Agent Marketplace.")

# ---------- File upload ----------
st.markdown('<div class="card-title">Upload expense files</div>', unsafe_allow_html=True)
uploaded_files = st.file_uploader(
    "Upload expense files",
    accept_multiple_files=True,
    type=["jpg", "jpeg", "png", "webp", "bmp", "pdf", "xlsx", "xls", "csv", "txt"],
    label_visibility="collapsed",
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

    st.markdown("### Summary")
    st.markdown(
        f"""
        <div class="kpi-row">
            <div class="kpi">
                <div class="kpi-label">Total records</div>
                <div class="kpi-value">{summary.total_records}</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Clean</div>
                <div class="kpi-value good">{summary.clean_records}</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Flagged</div>
                <div class="kpi-value warn">{summary.flagged_records}</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Duplicates</div>
                <div class="kpi-value accent">{summary.duplicate_count}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Totals by currency</div>', unsafe_allow_html=True)
        if summary.total_amount_by_currency:
            totals_df = pd.DataFrame(
                [{"Currency": c, "Total": float(v)} for c, v in summary.total_amount_by_currency.items()]
            )
            st.dataframe(totals_df, hide_index=True, use_container_width=True)
        else:
            st.caption("No amounts extracted yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">Totals by category</div>', unsafe_allow_html=True)
        if summary.total_by_category:
            cat_df = pd.DataFrame(
                [{"Category": c, "Total": float(v)} for c, v in summary.total_by_category.items()]
            )
            st.bar_chart(cat_df.set_index("Category"), color="#2F5CFF")
        else:
            st.caption("No categories assigned yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Line items")

    rows = []
    for r in records:
        rows.append({
            "Vendor": r.vendor,
            "Date": r.expense_date,
            "Amount": float(r.amount) if r.amount is not None else None,
            "Currency": r.currency,
            "Category": r.category.value,
            "Method": r.extraction_method,
            "Status": "Clean" if r.is_clean() else "Flagged: " + ", ".join(f.value for f in r.flags),
        })
    display_df = pd.DataFrame(rows)
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        "Download full Excel report",
        data=st.session_state["report_bytes"],
        file_name="expense_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

elif not uploaded_files:
    st.markdown(
        """
        <div class="card" style="text-align:center; padding: 40px 20px; color:#667085;">
            Upload one or more expense files above to get started.
        </div>
        """,
        unsafe_allow_html=True,
    )
