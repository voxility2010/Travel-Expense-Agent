"""
Streamlit UI for the Travel Expense Extraction Agent.
Updated with Suproc Brand Design System, Blue Atmospheric Glow & Curved Globe Horizon.
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

# ---------- CSS & Atmosphere Background Injection ----------
# ---------- CSS & Atmosphere Background Injection ----------
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
    --app-canvas-bg: #ffffff;
    --app-text-primary: rgb(17 24 39);
    --app-text-secondary: rgb(71 85 105);
    
    --app-btn-primary-bg: radial-gradient(135% 118% at 0% 0%, rgba(226, 232, 240, .12), transparent 55%), linear-gradient(180deg, rgba(39, 51, 72, .9) 0%, rgba(17, 24, 39, .94) 100%);
    --app-btn-primary-bg-hover: radial-gradient(135% 118% at 0% 0%, rgba(241, 245, 249, .16), transparent 55%), linear-gradient(180deg, rgba(49, 63, 87, .94) 0%, rgba(24, 33, 49, .98) 100%);
    --app-btn-primary-border: rgba(203, 213, 225, .28);
    --app-btn-primary-text: rgb(248 250 252);
    --app-btn-primary-shadow: 0 12px 26px rgba(1, 8, 24, .32), inset 0 1px 0 rgba(241, 245, 249, .14), inset 0 -1px 0 rgba(2, 6, 18, .38);
    
    --app-btn-secondary-bg: radial-gradient(150% 100% at 0% 0%, rgba(255, 255, 255, .88), rgba(244, 247, 252, .82) 60%), linear-gradient(170deg, rgba(255, 255, 255, .92), rgba(242, 246, 252, .86));
    --app-btn-secondary-bg-hover: radial-gradient(150% 100% at 0% 0%, rgba(255, 255, 255, .96), rgba(247, 250, 255, .88) 60%), linear-gradient(170deg, rgba(255, 255, 255, .98), rgba(245, 248, 253, .9));
    --app-btn-secondary-border: rgba(134, 155, 183, .5);
    --app-btn-secondary-text: rgb(30 41 59);
    --app-btn-secondary-shadow: 0 6px 14px rgba(15, 23, 42, .08), inset 0 1px 0 rgba(255, 255, 255, .82);
    
    --app-link: #2563eb;
    --app-success: #0fc27b;
    --app-success-text: #095a39;
    
    --surface: rgba(255, 255, 255, .95);
    --surface-border: rgba(15, 23, 42, .08);
    --shadow-1: 0 8px 20px rgba(15, 23, 42, .04);
}

html, body, [class*="css"] { 
    font-family: 'Inter', -apple-system, sans-serif !important; 
    color: var(--app-text-primary) !important;
    background-color: var(--app-canvas-bg) !important;
    -webkit-font-smoothing: antialiased;
}

/* Prevent horizontal scrollbar during breakout */
body, .stApp {
    overflow-x: hidden !important;
}

/* Background Blue Radial Glow */
.stApp {
    background-color: #ffffff !important;
    background-image: 
        radial-gradient(ellipse 120% 70% at 50% -10%, rgba(186, 230, 253, 0.65), rgba(219, 234, 254, 0.35) 40%, rgba(255, 255, 255, 0) 75%) !important;
    background-attachment: fixed !important;
}

.block-container { 
    max-width: 1080px; 
    padding-top: 2rem; 
    padding-bottom: 4rem; 
    position: relative;
    z-index: 2;
}

[data-testid="stHeader"] {
    background: transparent !important;
    height: 3.25rem;
}

code, .mono, .stMarkdown code {
    font-family: 'IBM Plex Mono', monospace !important;
    background: rgba(36, 38, 41, .045);
    color: var(--app-text-primary);
    padding: 2px 6px;
    border-radius: 6px;
    font-size: 0.85em;
}

/* ---- Globe Arc Horizon Breakout (Spans 100% Screen Width) ---- */
.globe-horizon-container {
    position: relative;
    width: 100vw;
    left: 50%;
    right: 50%;
    margin-left: -50vw;
    margin-right: -50vw;
    height: 60px;
    margin-top: 1rem;
    margin-bottom: 2.5rem;
    overflow: hidden;
    display: flex;
    justify-content: center;
}

.globe-arc {
    position: absolute;
    top: 0;
    width: 140vw;
    height: 600px;
    border-radius: 50%;
    border-top: 1.5px solid rgba(96, 165, 250, 0.85);
    background: linear-gradient(180deg, rgba(239, 246, 255, 0.6) 0%, rgba(255, 255, 255, 0.95) 25%, #ffffff 100%);
    box-shadow: 0 -12px 28px -2px rgba(59, 130, 246, 0.35), inset 0 8px 16px rgba(255, 255, 255, 0.9);
}

/* ---- Card & Layout Elements ---- */
.stExpander, .card, section[data-testid="stSidebar"], [data-testid="stDataFrame"], [data-testid="stStatus"] {
    background: var(--surface) !important;
    border: 1px solid var(--surface-border) !important;
    border-radius: 12px !important;
    box-shadow: var(--shadow-1) !important;
    backdrop-filter: blur(8px);
}

.stExpander { margin-bottom: 20px !important; overflow: hidden; }
.stExpander > details > summary {
    font-weight: 500; color: var(--app-text-primary); font-size: 0.9rem; padding: 10px 16px;
}
.stExpander > details > summary:hover { background: rgba(36, 38, 41, .02); }
.stExpander > details > div {
    padding: 0 16px 14px 16px; color: var(--app-text-secondary); font-size: 0.9rem; line-height: 1.58;
}

.card { padding: 20px 22px; margin-bottom: 18px; }
.card-title {
    font-weight: 600; font-size: 0.95rem; color: var(--app-text-primary);
    margin-bottom: 14px; display: flex; align-items: center; gap: 8px;
}

/* ---- KPI Tiles ---- */
.kpi-row { display: flex; gap: 14px; margin-bottom: 18px; flex-wrap: wrap; }
.kpi {
    flex: 1; min-width: 140px;
    background: var(--surface); border: 1px solid var(--surface-border);
    border-radius: 12px; padding: 16px 18px; box-shadow: var(--shadow-1);
}
.kpi-label {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.06em;
    text-transform: uppercase; color: var(--app-text-secondary); margin-bottom: 6px;
}
.kpi-value {
    font-family: 'IBM Plex Mono', monospace; font-size: 1.6rem;
    font-weight: 600; color: var(--app-text-primary);
}
.kpi-value.accent { color: var(--app-link); }
.kpi-value.good { color: var(--app-success-text); }
.kpi-value.warn { color: #B54708; }

/* ---- Upload Zone ---- */
section[data-testid="stFileUploaderDropzone"] {
    background: var(--surface) !important;
    border: 1px dashed var(--app-btn-secondary-border) !important;
    border-radius: 12px !important;
    padding: 12px; transition: border-color 0.2s, background 0.2s;
}
section[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--app-link) !important;
    background: rgba(37, 99, 235, .02) !important;
}

/* ---- Buttons ---- */
.stButton > button, .stDownloadButton > button {
    border-radius: 999px !important; font-weight: 500 !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.48rem .9rem !important;
    font-size: .875rem !important;
    transition: all 0.18s ease !important;
}

.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
    background: var(--app-btn-primary-bg) !important;
    color: var(--app-btn-primary-text) !important;
    border: 1px solid var(--app-btn-primary-border) !important;
    box-shadow: var(--app-btn-primary-shadow) !important;
}
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {
    background: var(--app-btn-primary-bg-hover) !important;
    transform: translateY(-1px);
}

/* ---- Tabs ---- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: rgba(36, 38, 41, .045); padding: 4px;
    border-radius: 12px; width: fit-content;
}
.stTabs [data-baseweb="tab"] {
    height: 36px; border-radius: 8px !important; font-size: 0.85rem;
    font-weight: 500; color: var(--app-text-secondary); padding: 0 16px;
}
.stTabs [aria-selected="true"] {
    background: var(--surface) !important; color: var(--app-text-primary) !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, .08);
}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] { border-right: 1px solid var(--surface-border) !important; }
section[data-testid="stSidebar"] .block-container { padding-top: 2rem; }

.sb-eyebrow {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem;
    font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--app-text-secondary); margin: 0 0 12px 0;
}
.sb-format {
    display: flex; align-items: center; gap: 10px; padding: 8px 0;
    font-size: 0.85rem; color: var(--app-text-primary); font-weight: 500;
}
.sb-format .sb-icon {
    width: 26px; height: 26px; border-radius: 7px; flex-shrink: 0;
    background: rgba(37, 99, 235, .08); color: var(--app-link);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 700;
}
.sb-status {
    display: flex; align-items: center; gap: 8px; font-size: 0.8rem;
    color: var(--app-text-secondary); font-weight: 500; margin-top: 22px;
    padding-top: 16px; border-top: 1px solid var(--surface-border);
}
.sb-status .dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--app-success); flex-shrink: 0;
    box-shadow: 0 0 0 3px rgba(15, 194, 123, 0.2);
}

/* ---- Dataframe & Charts ---- */
[data-testid="stDataFrame"] th {
    background: rgba(36, 38, 41, .02) !important;
    color: var(--app-text-secondary) !important;
    font-weight: 500 !important; font-size: 0.82rem !important;
    border-bottom: 1px solid var(--surface-border) !important;
}
[data-testid="stDataFrame"] td {
    color: var(--app-text-primary) !important; font-size: 0.85rem !important;
    border-bottom: 1px solid rgba(15, 23, 42, .02) !important;
}
[data-testid="stVegaLiteChart"] {
    background: var(--surface) !important; border-radius: 12px !important;
}
hr { border-color: var(--surface-border) !important; }
"""

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
        link2.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap';
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

# ---------- Hero Header with Globe Arc ----------
st.markdown(
    textwrap.dedent(
        """
        <div style="display: flex; flex-direction: column; align-items: center; text-align: center; padding: 2.5rem 0 1rem 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;">
            <div style="display: inline-flex; align-items: center; gap: 8px; margin-bottom: 1.25rem;">
                <span style="display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; background-color: #dbeafe; border-radius: 50%;">
                    <span style="width: 7px; height: 7px; background-color: #2563eb; border-radius: 50%;"></span>
                </span>
                <span style="font-size: 0.78rem; font-weight: 700; letter-spacing: 0.08em; color: #2563eb; text-transform: uppercase;">SUPROC AGENT MARKETPLACE</span>
            </div>
            <h1 style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; font-size: 3.5rem !important; font-weight: 350 !important; color: #1a1a1a !important; line-height: 1.12 !important; letter-spacing: -0.035em !important; margin: 0 0 1.25rem 0 !important; text-align: center !important;">
                Travel Expense <span style="color: #2563eb; font-weight: 400;">Generator.</span>
            </h1>
            <p style="color: #4b5563; font-size: 1.1rem; font-weight: 400; max-width: 640px; line-height: 1.6; margin: 0 auto;">
                Upload receipts, invoices, or expense statements in any mix of formats — 
                images, PDFs, Excel/CSV, or pasted text — and get back a validated, 
                categorized expense report in seconds.
            </p>
        </div>
        <div class="globe-horizon-container">
            <div class="globe-arc"></div>
        </div>
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

# ---------- File Upload / Input ----------
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

# ---------- Results Display ----------
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
            st.bar_chart(cat_df.set_index("Category"), color="#2563eb", horizontal=True)
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
        <div class="card" style="text-align:center; padding: 48px 20px; color:var(--app-text-secondary); margin-top: 18px;">
            Upload one or more expense files above to get started.
        </div>
        """
        ).strip(),
        unsafe_allow_html=True,
    )
