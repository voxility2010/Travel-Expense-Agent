"""
Streamlit UI for the Travel Expense Extraction Agent.

Designed to run both locally (`streamlit run app.py`) and on any Docker-based
host (Render, etc) with zero changes.
"""

from __future__ import annotations

import os
import tempfile
import textwrap
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
# Design tokens — Suproc Marketplace Theme
#   Background:  #E8EDF5 (soft blue-gray)
#   Surface:     #FFFFFF
#   Border:      #D6DDE9
#   Accent:      #2563EB (vibrant blue)
#   Accent dark: #1D4ED8
#   Text:        #1E293B (primary) / #64748B (secondary)
#   Success:     #059669 / bg #ECFDF5
#   Warning:     #D97706 / bg #FFFBEB
#   Type:        Inter (UI), IBM Plex Mono (data / labels)
# ============================================================

st.markdown(
    textwrap.dedent(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background: #E8EDF5; }
    .block-container { max-width: 1200px; padding-top: 1.5rem; padding-bottom: 3rem; }

    code, .mono { font-family: 'IBM Plex Mono', monospace; }

    /* ---- Top Navigation Bar ---- */
    .top-nav {
        display: flex; align-items: center; justify-content: space-between;
        padding: 12px 24px; background: #FFFFFF;
        border-bottom: 1px solid #D6DDE9; margin: -4rem -4rem 2rem -4rem;
        position: sticky; top: 0; z-index: 100;
    }
    .nav-left { display: flex; align-items: center; gap: 20px; }
    .nav-brand {
        display: flex; align-items: center; gap: 10px;
        font-weight: 700; font-size: 1.1rem; color: #1E293B;
    }
    .nav-brand .logo {
        width: 32px; height: 32px; border-radius: 8px;
        background: linear-gradient(135deg, #2563EB, #1D4ED8);
        display: flex; align-items: center; justify-content: center;
        color: white; font-size: 16px;
    }
    .nav-tabs {
        display: flex; gap: 4px; background: #F1F5F9;
        padding: 4px; border-radius: 10px;
    }
    .nav-tab {
        padding: 6px 16px; border-radius: 8px; font-size: 0.85rem;
        font-weight: 500; color: #64748B; cursor: pointer;
    }
    .nav-tab.active {
        background: #FFFFFF; color: #1E293B;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .nav-right {
        display: flex; align-items: center; gap: 12px;
    }
    .nav-avatar {
        width: 36px; height: 36px; border-radius: 50%;
        background: linear-gradient(135deg, #F472B6, #DB2777);
        display: flex; align-items: center; justify-content: center;
        color: white; font-weight: 600; font-size: 0.9rem;
    }

    /* ---- Header ---- */
    .app-header {
        text-align: center; margin-bottom: 32px; padding-top: 16px;
    }
    .app-header .eyebrow {
        font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem;
        font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase;
        color: #2563EB; margin: 0 0 10px 0;
    }
    .app-header h1 {
        font-size: 2.2rem; font-weight: 700; color: #1E293B;
        margin: 0 0 12px 0; line-height: 1.15; letter-spacing: -0.02em;
    }
    .app-header h1 span { color: #2563EB; }
    .app-subtitle {
        color: #64748B; font-size: 1rem; margin: 0 auto 32px auto;
        max-width: 560px; line-height: 1.6; text-align: center;
    }

    /* ---- Cards ---- */
    .card {
        background: #FFFFFF; border: 1px solid #D6DDE9; border-radius: 16px;
        padding: 24px; margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(30, 41, 59, 0.04), 0 1px 2px rgba(30, 41, 59, 0.02);
        transition: box-shadow 0.2s ease;
    }
    .card:hover {
        box-shadow: 0 4px 12px rgba(30, 41, 59, 0.06), 0 2px 4px rgba(30, 41, 59, 0.04);
    }
    .card-title {
        font-weight: 600; font-size: 0.95rem; color: #1E293B;
        margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
    }
    .card-title .icon {
        width: 28px; height: 28px; border-radius: 8px;
        background: #EFF6FF; color: #2563EB;
        display: flex; align-items: center; justify-content: center;
        font-size: 14px;
    }

    /* ---- KPI tiles ---- */
    .kpi-row { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
    .kpi {
        flex: 1; min-width: 160px;
        background: #FFFFFF; border: 1px solid #D6DDE9; border-radius: 16px;
        padding: 20px 22px;
        box-shadow: 0 1px 3px rgba(30, 41, 59, 0.04);
    }
    .kpi-label {
        font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em;
        text-transform: uppercase; color: #94A3B8; margin-bottom: 8px;
    }
    .kpi-value {
        font-family: 'IBM Plex Mono', monospace; font-size: 1.8rem;
        font-weight: 600; color: #1E293B; line-height: 1.2;
    }
    .kpi-value.accent { color: #2563EB; }
    .kpi-value.good { color: #059669; }
    .kpi-value.warn { color: #D97706; }
    .kpi-sub {
        font-size: 0.8rem; color: #94A3B8; margin-top: 4px;
    }

    /* ---- Status chips ---- */
    .chip {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 4px 12px; border-radius: 999px;
        font-size: 0.78rem; font-weight: 600;
    }
    .chip-ok { background: #ECFDF5; color: #059669; }
    .chip-ok::before { content: "●"; font-size: 0.5rem; }
    .chip-warn { background: #FFFBEB; color: #D97706; }
    .chip-warn::before { content: "●"; font-size: 0.5rem; }
    .chip-info { background: #EFF6FF; color: #2563EB; }
    .chip-info::before { content: "●"; font-size: 0.5rem; }

    /* ---- Upload zone ---- */
    section[data-testid="stFileUploaderDropzone"] {
        background: #FFFFFF; border: 2px dashed #CBD5E1; border-radius: 16px;
        padding: 40px 20px;
    }
    section[data-testid="stFileUploaderDropzone"]:hover {
        border-color: #2563EB; background: #FAFBFC;
    }
    section[data-testid="stFileUploaderDropzone"] > div > div > small {
        color: #64748B; font-size: 0.85rem;
    }

    /* ---- Buttons ---- */
    .stButton > button, .stDownloadButton > button {
        border-radius: 10px; font-weight: 600; border: none;
        padding: 10px 24px; font-size: 0.9rem;
        transition: all 0.2s ease;
    }
    .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
        background: #2563EB;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
    }
    .stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {
        background: #1D4ED8; transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.35);
    }
    .stButton > button[kind="secondary"], .stDownloadButton > button[kind="secondary"] {
        background: #FFFFFF; color: #1E293B; border: 1px solid #D6DDE9;
    }
    .stButton > button[kind="secondary"]:hover, .stDownloadButton > button[kind="secondary"]:hover {
        background: #F8FAFC; border-color: #CBD5E1;
    }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: #FFFFFF; border-right: 1px solid #D6DDE9;
    }
    section[data-testid="stSidebar"] > div {
        padding-top: 1.5rem;
    }
    section[data-testid="stSidebar"] h2 {
        font-size: 0.85rem; font-weight: 700; color: #1E293B;
        letter-spacing: 0.02em; text-transform: uppercase;
    }
    section[data-testid="stSidebar"] .stMarkdown p {
        color: #64748B; font-size: 0.85rem; line-height: 1.6;
    }

    /* ---- Dataframe ---- */
    [data-testid="stDataFrame"] {
        border: 1px solid #E2E8F0; border-radius: 12px; overflow: hidden;
    }
    [data-testid="stDataFrame"] th {
        background: #F8FAFC !important; color: #475569 !important;
        font-weight: 600 !important; font-size: 0.8rem !important;
        text-transform: uppercase; letter-spacing: 0.04em;
    }
    [data-testid="stDataFrame"] td {
        font-size: 0.88rem !important; color: #334155 !important;
    }

    /* ---- Expander ---- */
    details { 
        background: #FFFFFF; border: 1px solid #D6DDE9; border-radius: 12px;
        padding: 4px 16px; margin-bottom: 20px;
    }
    summary { font-weight: 600; color: #475569; font-size: 0.9rem; }
    summary:hover { color: #2563EB; }

    /* ---- Status widget ---- */
    [data-testid="stStatus"] {
        background: #FFFFFF; border: 1px solid #D6DDE9; border-radius: 12px;
    }

    /* ---- Divider ---- */
    hr { border-color: #E2E8F0; margin: 24px 0; }

    /* ---- Empty state ---- */
    .empty-state {
        text-align: center; padding: 60px 20px; color: #94A3B8;
        background: #FFFFFF; border: 1px solid #D6DDE9; border-radius: 16px;
    }
    .empty-state .icon {
        font-size: 3rem; margin-bottom: 16px; opacity: 0.5;
    }
    .empty-state h3 {
        color: #475569; font-weight: 600; margin-bottom: 8px;
    }

    /* ---- Section headers ---- */
    h3 {
        font-size: 1.1rem; font-weight: 700; color: #1E293B;
        margin: 32px 0 16px 0; letter-spacing: -0.01em;
    }

    /* ---- Scrollbar ---- */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #94A3B8; }
    </style>
    """
    ).strip(),
    unsafe_allow_html=True,
)

# ---------- Top Navigation Bar ----------
st.markdown(
    textwrap.dedent(
    """
    <div class="top-nav">
        <div class="nav-left">
            <div class="nav-brand">
                <div class="logo">⚡</div>
                <span>Suproc</span>
            </div>
            <div class="nav-tabs">
                <div class="nav-tab active">🧾 Expense Agent</div>
                <div class="nav-tab">Explore</div>
                <div class="nav-tab">Agents</div>
            </div>
        </div>
        <div class="nav-right">
            <div class="nav-avatar">V</div>
        </div>
    </div>
    """
    ).strip(),
    unsafe_allow_html=True,
)

# ---------- Header ----------
st.markdown(
    textwrap.dedent(
    """
    <div class="app-header">
        <p class="eyebrow">Connected Opportunity Network</p>
        <h1>Travel Expense Extraction <span>Agent</span></h1>
        <p class="app-subtitle">
            Upload receipts, invoices, or expense statements in any mix of formats —
            images, PDFs, Excel/CSV, or pasted text — and get back a validated,
            categorized expense report in seconds.
        </p>
    </div>
    """
    ).strip(),
    unsafe_allow_html=True,
)

with st.expander("How this agent works", expanded=False):
    st.markdown(
        textwrap.dedent(
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
        ).strip()
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
        textwrap.dedent(
        """
        - 🖼️ Images (jpg, png, webp)
        - 📄 PDF (digital or scanned)
        - 📊 Excel / CSV
        - 📝 Plain text
        """
        ).strip()
    )
    st.divider()
    st.caption("Built for the Suproc Agent Marketplace.")

# ---------- File upload ----------
st.markdown(
    '<div class="card-title"><span class="icon">📤</span>Upload expense files</div>',
    unsafe_allow_html=True,
)
uploaded_files = st.file_uploader(
    "Upload expense files",
    accept_multiple_files=True,
    type=["jpg", "jpeg", "png", "webp", "bmp", "pdf", "xlsx", "xls", "csv", "txt"],
    label_visibility="collapsed",
)

run_button = st.button("Extract expenses →", type="primary", disabled=not uploaded_files)

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
        textwrap.dedent(
        f"""
        <div class="kpi-row">
            <div class="kpi">
                <div class="kpi-label">Total Records</div>
                <div class="kpi-value">{summary.total_records}</div>
                <div class="kpi-sub">All extracted items</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Clean</div>
                <div class="kpi-value good">{summary.clean_records}</div>
                <div class="kpi-sub">Passed all checks</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Flagged</div>
                <div class="kpi-value warn">{summary.flagged_records}</div>
                <div class="kpi-sub">Needs review</div>
            </div>
            <div class="kpi">
                <div class="kpi-label">Duplicates</div>
                <div class="kpi-value accent">{summary.duplicate_count}</div>
                <div class="kpi-sub">Auto-detected</div>
            </div>
        </div>
        """
        ).strip(),
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title"><span class="icon">💱</span>Totals by currency</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="card-title"><span class="icon">📊</span>Totals by category</div>', unsafe_allow_html=True)
        if summary.total_by_category:
            cat_df = pd.DataFrame(
                [{"Category": c, "Total": float(v)} for c, v in summary.total_by_category.items()]
            )
            st.bar_chart(cat_df.set_index("Category"), color="#2563EB")
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
        "Download full Excel report ↓",
        data=st.session_state["report_bytes"],
        file_name="expense_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

elif not uploaded_files:
    st.markdown(
        textwrap.dedent(
        """
        <div class="empty-state">
            <div class="icon">📂</div>
            <h3>Ready to extract</h3>
            <p>Upload one or more expense files above to get started.</p>
        </div>
        """
        ).strip(),
        unsafe_allow_html=True,
    )
