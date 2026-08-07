"""
Streamlit UI for the Travel Expense Extraction Agent.

Designed to run both locally (`streamlit run app.py`) and on any Docker-based
host (Render, etc) with zero changes.
"""

from __future__ import annotations

import tempfile
import textwrap
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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
#   Type:        Plus Jakarta Sans (UI), IBM Plex Mono (data / labels)
# ============================================================

CUSTOM_CSS = """
/* Placeholder type — swap this @import + the two font-family declarations
   below once the Suproc brand font is available. Everything else in this
   file references fonts only through these two spots. */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }

.stApp {
    background: radial-gradient(120% 100% at 50% 0%, #EEF2FC 0%, #F5F7FB 45%, #F5F7FB 100%) !important;
}
.block-container { max-width: 1080px; padding-top: 3rem; padding-bottom: 4rem; }

/* Streamlit's own toolbar (sidebar-collapse arrow + menu) sits fixed on top
   of the page. Give it a solid background instead of transparent, or content
   directly underneath (like our eyebrow label) gets visually clipped/cut. */
[data-testid="stHeader"] {
    background: #F5F7FB !important;
    height: 3.25rem;
}
[data-testid="stToolbar"] { right: 1rem; }

code, .mono, .stMarkdown code {
    font-family: 'IBM Plex Mono', monospace !important;
    background: #F2F4F7;
    color: #101828;
    padding: 2px 6px;
    border-radius: 6px;
    font-size: 0.85em;
}

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

/* ---- Expander ---- */
.stExpander {
    background: #FFFFFF !important;
    border: 1px solid #E3E8F1 !important;
    border-radius: 10px !important;
    overflow: hidden;
    margin-bottom: 20px !important;
}
.stExpander > details > summary {
    font-weight: 500;
    color: #344054;
    font-size: 0.9rem;
    padding: 10px 16px;
}
.stExpander > details > summary:hover {
    background: #F9FAFB;
}
.stExpander > details > div {
    padding: 0 16px 14px 16px;
    color: #475467;
    font-size: 0.9rem;
    line-height: 1.6;
}

/* ---- Cards ---- */
.card {
    background: #FFFFFF; border: 1px solid #E3E8F1; border-radius: 14px;
    padding: 20px 22px; margin-bottom: 18px;
    box-shadow: 0 1px 2px rgba(16,24,40,0.04);
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
    box-shadow: 0 1px 2px rgba(16,24,40,0.04);
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
    background: #FFFFFF !important;
    border: 1.5px dashed #C7D2E8 !important;
    border-radius: 14px !important;
    padding: 12px;
    transition: border-color 0.2s, background 0.2s;
}
section[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #2F5CFF !important;
    background: #F8FAFF !important;
}
section[data-testid="stFileUploaderDropzone"] > div > small {
    color: #667085 !important;
    font-size: 0.78rem !important;
}

/* ---- Buttons ---- */
.stButton > button, .stDownloadButton > button {
    border-radius: 999px !important; font-weight: 600 !important; border: none !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    padding: 0.55rem 1.4rem !important;
    transition: background 0.15s, transform 0.1s, box-shadow 0.15s !important;
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    background: #2F5CFF !important;
    box-shadow: 0 1px 2px rgba(47,92,255,0.15) !important;
}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {
    background: #1E3FCC !important;
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(47,92,255,0.28) !important;
}
.stButton > button[kind="primary"]:active, .stDownloadButton > button[kind="primary"]:active {
    transform: translateY(0);
}
.stButton > button[kind="primary"]:disabled {
    background: #B4C6FC !important;
    cursor: not-allowed !important;
    transform: none !important;
    box-shadow: none !important;
}
.stButton > button[kind="secondary"] {
    background: #FFFFFF !important;
    color: #101828 !important;
    border: 1px solid #D0D5DD !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #2F5CFF !important;
    color: #2F5CFF !important;
}

/* ---- Tabs (file upload vs paste text) ---- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #EEF1F7;
    padding: 4px;
    border-radius: 12px;
    width: fit-content;
}
.stTabs [data-baseweb="tab"] {
    height: 36px;
    border-radius: 8px !important;
    font-size: 0.85rem;
    font-weight: 600;
    color: #667085;
    padding: 0 16px;
}
.stTabs [aria-selected="true"] {
    background: #FFFFFF !important;
    color: #101828 !important;
    box-shadow: 0 1px 2px rgba(16,24,40,0.06);
}
.stTabs [data-testid="stMarkdownContainer"] p { font-size: 0.85rem; }

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #E3E8F1 !important;
}
section[data-testid="stSidebar"] .block-container { padding-top: 2rem; }

.sb-eyebrow {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem;
    font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
    color: #98A2B3; margin: 0 0 12px 0;
}
.sb-format {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 0;
    font-size: 0.85rem; color: #344054; font-weight: 500;
}
.sb-format .sb-icon {
    width: 26px; height: 26px; border-radius: 7px; flex-shrink: 0;
    background: #EEF2FF; color: #2F5CFF;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 700;
}
.sb-status {
    display: flex; align-items: center; gap: 8px;
    font-size: 0.8rem; color: #475467; font-weight: 500;
    margin-top: 22px; padding-top: 16px;
    border-top: 1px solid #E3E8F1;
}
.sb-status .dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #17803D; flex-shrink: 0;
    box-shadow: 0 0 0 3px #ECFDF3;
}
section[data-testid="stSidebar"] .stCaption {
    color: #98A2B3 !important;
    font-size: 0.75rem !important;
}

/* ---- Dataframe ---- */
[data-testid="stDataFrame"] {
    border: 1px solid #E3E8F1 !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] th {
    background: #F9FAFB !important;
    color: #475467 !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    border-bottom: 1px solid #E3E8F1 !important;
}
[data-testid="stDataFrame"] td {
    color: #344054 !important;
    font-size: 0.85rem !important;
    border-bottom: 1px solid #F2F4F7 !important;
}

/* ---- Status widget ---- */
[data-testid="stStatus"] {
    background: #FFFFFF !important;
    border: 1px solid #E3E8F1 !important;
    border-radius: 12px !important;
}

/* ---- Bar chart override ---- */
[data-testid="stVegaLiteChart"] {
    background: #FFFFFF !important;
    border-radius: 12px !important;
}

hr { border-color: #E3E8F1 !important; }
"""

# Inject CSS via components.html into parent <head> — bypasses Streamlit's sanitizer
_css_escaped = CUSTOM_CSS.replace("`", "\\`")

components.html(
    f"""
    <script>
    (function() {{
        const parentDoc = window.parent.document;
        if (parentDoc.getElementById('custom-app-css')) return;
        
        const link1 = parentDoc.createElement('link');
        link1.rel = 'preconnect';
        link1.href = 'https://fonts.googleapis.com';
        parentDoc.head.appendChild(link1);

        const link2 = parentDoc.createElement('link');
        link2.rel = 'stylesheet';
        link2.href = 'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap';
        parentDoc.head.appendChild(link2);

        const style = parentDoc.createElement('style');
        style.id = 'custom-app-css';
        style.innerHTML = `{_css_escaped}`;
        parentDoc.head.appendChild(style);
    }})();
    </script>
    """,
    height=0,
)

# ---------- Header ----------
st.markdown(
    textwrap.dedent(
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
    """
    ).strip(),
    unsafe_allow_html=True,
)

with st.expander("How this works", expanded=False):
    st.markdown(
        textwrap.dedent(
        """
        **1. You upload your expenses** — a photo of a receipt, a PDF invoice,
        an Excel sheet, whatever you have.

        **2. The agent reads them** — it pulls out the vendor name, date,
        and amount from each one automatically.

        **3. It double-checks everything** — flags anything that looks off,
        like a duplicate receipt, a date that doesn't make sense, or an
        unusually large amount.

        **4. It sorts each expense into a category** — travel, food, lodging,
        and so on.

        **5. You get one clean Excel file** — ready to download, with a
        summary and every expense listed out.
        """
        ).strip()
    )

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(
        textwrap.dedent(
        """
        <p class="sb-eyebrow">Supported formats</p>
        <div class="sb-format"><div class="sb-icon">IMG</div> Images — jpg, png, webp</div>
        <div class="sb-format"><div class="sb-icon">PDF</div> PDF — digital or scanned</div>
        <div class="sb-format"><div class="sb-icon">XLS</div> Excel / CSV</div>
        <div class="sb-format"><div class="sb-icon">TXT</div> Pasted text</div>
        <div class="sb-status"><div class="dot"></div> Agent online — Suproc Agent Marketplace</div>
        """
        ).strip(),
        unsafe_allow_html=True,
    )

# ---------- File upload ----------
st.markdown('<div class="card-title">Upload expense files</div>', unsafe_allow_html=True)

tab_upload, tab_paste = st.tabs(["Upload files", "Paste text"])

with tab_upload:
    uploaded_files = st.file_uploader(
        "Upload expense files",
        accept_multiple_files=True,
        type=["jpg", "jpeg", "png", "webp", "bmp", "pdf", "xlsx", "xls", "csv", "txt"],
        label_visibility="collapsed",
    )

with tab_paste:
    pasted_text = st.text_area(
        "Paste expense text",
        placeholder="Paste a receipt, invoice text, or a list of expenses here — "
                    "e.g. \"Uber to airport, 14 Mar 2026, ₹840\"",
        height=160,
        label_visibility="collapsed",
    )

has_input = bool(uploaded_files) or bool(pasted_text and pasted_text.strip())
run_button = st.button("Extract expenses", type="primary", disabled=not has_input)

if run_button and has_input:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_paths = []
        for uf in uploaded_files or []:
            path = Path(tmp_dir) / uf.name
            path.write_bytes(uf.getbuffer())
            tmp_paths.append(str(path))

        if pasted_text and pasted_text.strip():
            pasted_path = Path(tmp_dir) / "pasted_text.txt"
            pasted_path.write_text(pasted_text.strip(), encoding="utf-8")
            tmp_paths.append(str(pasted_path))

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
        """
        ).strip(),
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
            st.bar_chart(cat_df.set_index("Category"), color="#2F5CFF", horizontal=True)
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
            "Category": r.category.value if hasattr(r.category, 'value') else str(r.category),
            "Method": r.extraction_method,
            "Status": "Clean" if r.is_clean() else "Flagged: " + ", ".join(f.value if hasattr(f, 'value') else str(f) for f in r.flags),
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

elif not has_input:
    st.markdown(
        textwrap.dedent(
        """
        <div class="card" style="text-align:center; padding: 48px 20px; color:#667085; margin-top: 18px;">
            Upload one or more expense files above to get started.
        </div>
        """
        ).strip(),
        unsafe_allow_html=True,
    )
