from dotenv import load_dotenv
load_dotenv()

"""
app.py — DrawingIQ Main Application
Enterprise Engineering Drawing Analyzer
"""

import streamlit as st
import os
import json
import io
import csv
from datetime import datetime

# ─── Page config (must be first) ───────────────────────────────────────────────
st.set_page_config(
    page_title="DrawingIQ",
    page_icon="⚙",
    layout="wide",
    initial_sidebar_state="expanded",
)

from auth import init_session, is_logged_in, get_current_user, get_current_profile, logout, render_auth_page, refresh_profile
from database import (
    get_profile, save_analysis, get_analyses, get_analysis_by_id,
    delete_analysis, get_plan_limits, can_analyze,
    create_workspace, get_user_workspaces, get_workspace_members,
    invite_member, remove_member, get_usage_stats, PLAN_LIMITS
)
from billing import render_pricing_page, render_usage_bar, PLANS
from analyzer import analyze_image, analyze_pdf_pages
from pdf_utils import pdf_to_images, image_file_to_b64, get_pdf_page_count

# ─── Init session ───────────────────────────────────────────────────────────────
init_session()

# ─── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

[data-testid="stSidebar"] { background: #0f1117; border-right: 1px solid #1e2130; }
[data-testid="stSidebar"] * { color: #c8ccd8 !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #e8eaf0 !important; }

.main { background: #f5f6fa; }

.app-header {
    background: #0f1117; color: #e8eaf0;
    padding: 1.25rem 2rem; margin: -1rem -1rem 1.5rem -1rem;
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 2px solid #ff6b35;
}
.app-header-left  { display: flex; align-items: center; gap: 1rem; }
.app-title        { font-size: 1.5rem; font-weight: 600; letter-spacing: -0.02em; }
.app-subtitle     { font-size: 0.82rem; color: #8892a4; margin-top: 2px; }
.plan-badge       { font-size: 0.7rem; font-weight: 700; padding: 3px 9px; border-radius: 4px;
                    text-transform: uppercase; letter-spacing: 0.06em; }
.badge-free       { background: #e5e7eb; color: #374151; }
.badge-starter    { background: #bfdbfe; color: #1e40af; }
.badge-pro        { background: #fde68a; color: #92400e; }
.badge-enterprise { background: #ddd6fe; color: #5b21b6; }

.result-card { background:white; border:1px solid #e2e6f0; border-radius:10px; padding:1.5rem; margin:1rem 0; }
.metric-strip { display:flex; gap:0.75rem; margin:1rem 0; flex-wrap:wrap; }
.metric-box { background:white; border:1px solid #e2e6f0; border-radius:8px; padding:0.9rem 1.1rem; flex:1; min-width:110px; }
.metric-box .label { font-size:0.72rem; color:#6b7280; text-transform:uppercase; letter-spacing:0.05em; }
.metric-box .value { font-size:1.25rem; font-weight:600; color:#1a1d2e; font-family:'IBM Plex Mono',monospace; margin-top:3px; }
.metric-box .value.small { font-size:0.95rem; }

.flag-item { border-left:3px solid #ff6b35; padding:0.6rem 0.9rem; margin:0.4rem 0; border-radius:0 6px 6px 0; font-size:0.88rem; }
.flag-critical { border-left-color:#dc2626; background:#fff5f5; color:#2d0e0e; }
.flag-warning  { border-left-color:#d97706; background:#fffbee; color:#3d2e00; }
.flag-info     { border-left-color:#2563eb; background:#eff6ff; color:#1e3a5f; }

.drawing-type-tag { display:inline-block; background:#0f1117; color:#ff6b35; font-size:0.78rem;
    font-weight:700; padding:4px 12px; border-radius:4px; letter-spacing:0.08em;
    text-transform:uppercase; margin-bottom:1rem; }

.dim-table { width:100%; border-collapse:collapse; font-size:0.88rem; }
.dim-table th { background:#f0f2f8; text-align:left; padding:7px 10px; font-size:0.75rem;
    text-transform:uppercase; letter-spacing:0.05em; color:#4b5563; }
.dim-table td { padding:7px 10px; border-bottom:1px solid #f0f2f8; color:#374151;
    font-family:'IBM Plex Mono',monospace; font-size:0.83rem; }
.dim-table .critical-row td { background:#fff5f5; }

.history-row { background:white; border:1px solid #e2e6f0; border-radius:8px; padding:0.8rem 1rem;
    margin:0.4rem 0; display:flex; align-items:center; justify-content:space-between; }
.history-row:hover { border-color:#ff6b35; }

.team-member-row { background:white; border:1px solid #e2e6f0; border-radius:8px;
    padding:0.7rem 1rem; margin:0.3rem 0; display:flex; align-items:center; gap:1rem; }
.avatar { width:36px; height:36px; border-radius:50%; background:#0f1117; color:#ff6b35;
    display:flex; align-items:center; justify-content:center; font-weight:700; font-size:0.8rem;
    flex-shrink:0; }
.role-badge { font-size:0.72rem; font-weight:600; padding:2px 8px; border-radius:10px; }
.role-owner  { background:#fef3c7; color:#92400e; }
.role-admin  { background:#e0f2fe; color:#075985; }
.role-member { background:#f3f4f6; color:#374151; }
.role-viewer { background:#ede9fe; color:#5b21b6; }

.empty-state { text-align:center; padding:3rem 2rem; color:#9ca3af; }
.empty-state .icon { font-size:2.5rem; }
.empty-state h3 { color:#374151; margin:0.75rem 0 0.4rem; font-weight:600; }

.upgrade-banner { background:linear-gradient(135deg,#ff6b35,#ff8c5a); color:white;
    border-radius:10px; padding:1rem 1.25rem; margin:0.5rem 0; text-align:center; }
.upgrade-banner strong { display:block; margin-bottom:0.25rem; }

button[kind="primary"] { background:#ff6b35 !important; border:none !important; }
</style>
""", unsafe_allow_html=True)

# ─── Auth gate ──────────────────────────────────────────────────────────────────
if not is_logged_in():
    render_auth_page()
    st.stop()

# ─── Load user data ─────────────────────────────────────────────────────────────
user    = get_current_user()
profile = get_current_profile() or {}

if not profile:
    refresh_profile()
    profile = get_current_profile() or {}

plan        = profile.get("plan", "free")
limits      = get_plan_limits(plan)
plan_badge  = f'<span class="plan-badge badge-{plan}">{plan.upper()}</span>'
user_name   = profile.get("full_name") or profile.get("email", "User")
user_initials = "".join([p[0].upper() for p in user_name.split()[:2]])

# ─── Header ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="app-header">
    <div class="app-header-left">
        <div>⚙</div>
        <div>
            <div class="app-title">DrawingIQ</div>
            <div class="app-subtitle">Enterprise Engineering Drawing Intelligence</div>
        </div>
        {plan_badge}
    </div>
    <div style="display:flex;align-items:center;gap:0.75rem;font-size:0.85rem;color:#8892a4;">
        <div style="background:#1e2130;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-weight:700;color:#ff6b35;font-size:0.8rem;">{user_initials}</div>
        <span>{user_name}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### ⚙ DrawingIQ")

    # API Key
    api_key = st.text_input("OpenAI API Key", type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Set OPENAI_API_KEY in your .env to avoid entering this every time.")
    if not api_key:
        st.warning("⚠ Add your OpenAI API key above to analyze drawings.")

    st.markdown("---")

    # Usage
    used   = profile.get("analyses_this_month", 0)
    cap    = limits["analyses_per_month"]
    render_usage_bar(used, cap, plan)

    if plan == "free" and used >= 3:
        st.markdown("""
        <div class="upgrade-banner">
            <strong>Running low on analyses</strong>
            Upgrade for 50–300/month
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Analysis settings
    st.markdown("**Analysis Settings**")
    discipline = st.selectbox("Discipline", [
        "Auto-Detect", "Mechanical / Machining", "Structural / Civil",
        "Electrical / Schematic", "Architectural", "PCB / Electronics", "Welding / Fabrication",
    ])
    detail_level = st.select_slider("Detail Level",
        options=["Quick Scan", "Standard", "Deep Review"],
        value="Standard")

    # Team workspace selector
    workspaces = get_user_workspaces(user["id"])
    workspace_id = None
    if workspaces and limits.get("team"):
        ws_options = {"Personal": None}
        for ws in workspaces:
            ws_data = ws.get("workspaces") or {}
            ws_options[ws_data.get("name", "Unnamed")] = ws_data.get("id")
        selected_ws = st.selectbox("Workspace", list(ws_options.keys()))
        workspace_id = ws_options[selected_ws]

    st.markdown("---")

    # Nav
    page = st.radio("Navigate", ["📤 Analyze", "📋 History", "👥 Team", "💳 Billing", "⚙ Account"],
                    label_visibility="collapsed")

    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        logout()


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED: render_result (defined before pages so all pages can call it)
# ═══════════════════════════════════════════════════════════════════════════════
def render_result(result: dict, filename: str, analysis_id: str = None):
    flags    = result.get("flags", [])
    critical = [f for f in flags if f.get("severity") == "critical"]
    warnings = [f for f in flags if f.get("severity") == "warning"]
    info_f   = [f for f in flags if f.get("severity") == "info"]
    dims     = result.get("dimensions", [])
    conf     = result.get("confidence_score", 0)

    dtype = result.get("drawing_type", "Unknown")
    st.markdown(f'<span class="drawing-type-tag">{dtype}</span>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="metric-strip">
        <div class="metric-box"><div class="label">Part</div><div class="value small">{result.get("part_name","—")}</div></div>
        <div class="metric-box"><div class="label">P/N</div><div class="value small">{result.get("part_number") or "—"}</div></div>
        <div class="metric-box"><div class="label">Rev</div><div class="value small">{result.get("revision") or "—"}</div></div>
        <div class="metric-box"><div class="label">Material</div><div class="value small">{result.get("material","—")}</div></div>
        <div class="metric-box"><div class="label">Complexity</div><div class="value small">{result.get("estimated_complexity","—")}</div></div>
        <div class="metric-box"><div class="label">Confidence</div><div class="value">{conf}%</div></div>
        <div class="metric-box"><div class="label">Flags</div>
            <div class="value small" style="color:{'#dc2626' if critical else '#16a34a'}">{len(critical)}c · {len(warnings)}w</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🚩 Flags", "📐 Dimensions", "🔧 Machinist Notes", "📋 Specs", "⬇ Export"])

    with tab1:
        if not flags:
            st.success("✓ No flags raised. Drawing looks clean.")
        if critical:
            st.markdown("**Critical**")
            for f in critical:
                st.markdown(f'<div class="flag-item flag-critical"><strong>{f.get("category","")}</strong>: {f.get("description","")}<br><span style="color:#6b7280;font-size:0.82rem;">→ {f.get("recommendation","")}</span></div>', unsafe_allow_html=True)
        if warnings:
            st.markdown("**Warnings**")
            for f in warnings:
                st.markdown(f'<div class="flag-item flag-warning"><strong>{f.get("category","")}</strong>: {f.get("description","")}<br><span style="color:#6b7280;font-size:0.82rem;">→ {f.get("recommendation","")}</span></div>', unsafe_allow_html=True)
        if info_f:
            st.markdown("**Info**")
            for f in info_f:
                st.markdown(f'<div class="flag-item flag-info"><strong>{f.get("category","")}</strong>: {f.get("description","")}</div>', unsafe_allow_html=True)
        concerns = result.get("manufacturing_concerns", [])
        if concerns:
            st.markdown("---\n**Manufacturing Concerns**")
            for c in concerns: st.markdown(f"• {c}")

    with tab2:
        if dims:
            rows = "".join([
                f'<tr class="{"critical-row" if d.get("is_critical") else ""}"><td>{d.get("feature","")}</td><td>{d.get("value","")}</td><td>{d.get("tolerance") or "—"}</td><td>{d.get("unit","")}</td><td>{"🔴" if d.get("is_critical") else ""}</td></tr>'
                for d in dims
            ])
            st.markdown(f'<table class="dim-table"><thead><tr><th>Feature</th><th>Value</th><th>Tolerance</th><th>Unit</th><th></th></tr></thead><tbody>{rows}</tbody></table>', unsafe_allow_html=True)
        else:
            st.info("No structured dimensions extracted.")
        gdt = result.get("gdt_callouts", [])
        if gdt:
            st.markdown("**GD&T Callouts**")
            for g in gdt:
                sym = g.get("symbol","")
                feat = g.get("feature","")
                val  = g.get("value","")
                dat  = g.get("datum","")
                st.markdown(f"`{sym}` **{feat}**: {val}" + (f" (Datum {dat})" if dat else ""))

    with tab3:
        note = result.get("machinist_notes", "")
        if note:
            st.markdown(f'<div class="result-card"><p style="line-height:1.9;color:#374151;">{note}</p></div>', unsafe_allow_html=True)
        procs = result.get("recommended_processes", [])
        if procs:
            st.markdown("**Recommended Processes**")
            cols = st.columns(min(len(procs), 4))
            for i, p in enumerate(procs):
                cols[i % len(cols)].markdown(f'<div style="background:#f0f2f8;border-radius:6px;padding:0.5rem 0.8rem;font-size:0.83rem;text-align:center;font-weight:500;">{p}</div>', unsafe_allow_html=True)
        standards = result.get("standards_referenced", [])
        if standards:
            st.markdown("**Standards Referenced:** " + " · ".join([f"`{s}`" for s in standards]))

    with tab4:
        fields = [
            ("Part Name", "part_name"), ("Part Number", "part_number"), ("Revision", "revision"),
            ("Scale", "scale"), ("Sheet", "sheet_info"), ("Material", "material"),
            ("Material Spec", "material_spec"), ("Surface Finish", "surface_finish"),
            ("Heat Treatment", "heat_treatment"), ("Weight Estimate", "weight_estimate"),
        ]
        rows = "".join([
            f'<tr><td style="color:#6b7280;font-size:0.83rem;padding:7px 10px;">{label}</td><td style="font-family:IBM Plex Mono,monospace;font-size:0.83rem;padding:7px 10px;">{result.get(key) or "—"}</td></tr>'
            for label, key in fields
        ])
        st.markdown(f'<table class="dim-table"><tbody>{rows}</tbody></table>', unsafe_allow_html=True)
        with st.expander("Raw JSON"):
            st.json(result)

    with tab5:
        if not limits.get("export"):
            st.markdown('<div class="upgrade-banner">Export requires Starter plan or higher.</div>', unsafe_allow_html=True)
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("⬇ JSON", json.dumps(result, indent=2),
                    file_name=f"{filename.rsplit('.',1)[0]}.json", mime="application/json", use_container_width=True)
            with c2:
                csv_buf = io.StringIO()
                w = csv.writer(csv_buf)
                w.writerow(["Field", "Value"])
                for k, v in result.items():
                    if isinstance(v, (str, int, float)): w.writerow([k, v])
                for d in result.get("dimensions", []):
                    w.writerow([f"DIM:{d.get('feature')}", f"{d.get('value')} {d.get('unit')} ±{d.get('tolerance','N/A')}"])
                for f in result.get("flags", []):
                    w.writerow([f"FLAG[{f.get('severity','').upper()}]", f"{f.get('category')}: {f.get('description')}"])
                st.download_button("⬇ CSV", csv_buf.getvalue(),
                    file_name=f"{filename.rsplit('.',1)[0]}.csv", mime="text/csv", use_container_width=True)

            st.markdown("**Copy-Paste Summary**")
            summary = (
                f"DRAWINGIQ — {filename}\n"
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"{'─'*50}\n"
                f"Part: {result.get('part_name','—')}  P/N: {result.get('part_number','—')}  Rev: {result.get('revision','—')}\n"
                f"Material: {result.get('material','—')} ({result.get('material_spec','—')})\n"
                f"Type: {result.get('drawing_type','—')}  Complexity: {result.get('estimated_complexity','—')}  Confidence: {result.get('confidence_score',0)}%\n"
                f"\nFLAGS ({len(flags)}):\n"
            ) + "\n".join([f"  [{f.get('severity','').upper()}] {f.get('category')}: {f.get('description')}" for f in flags]) + (
                f"\n\nMACHINIST NOTES:\n{result.get('machinist_notes','—')}"
            )
            st.text_area("", summary, height=260)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ANALYZE
# ═══════════════════════════════════════════════════════════════════════════════
if page == "📤 Analyze":

    allowed, reason = can_analyze(profile)
    if not allowed:
        st.error(reason)
        st.markdown("""
        <div class="upgrade-banner" style="max-width:500px;margin:1rem auto;">
            <strong>Monthly limit reached</strong>
            Upgrade your plan to continue analyzing drawings this month.
        </div>
        """, unsafe_allow_html=True)
        if st.button("View Upgrade Options", type="primary"):
            st.session_state["force_page"] = "💳 Billing"
            st.rerun()
        st.stop()

    # Accept images + PDF based on plan
    accepted_types = ["png", "jpg", "jpeg", "webp"]
    if limits.get("pdf"):
        accepted_types.append("pdf")

    max_batch = limits["batch_size"]
    pdf_note  = " • PDF" if limits.get("pdf") else " • PDF (Starter+ only)"

    uploaded_files = st.file_uploader(
        "Upload engineering drawings",
        type=accepted_types,
        accept_multiple_files=(max_batch > 1),
        help=f"Max {max_batch} file(s) per batch on your {plan.title()} plan."
    )

    if not uploaded_files:
        if isinstance(uploaded_files, list):
            pass
        else:
            uploaded_files = []

    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files] if uploaded_files else []

    # Enforce batch limit
    if len(uploaded_files) > max_batch:
        st.warning(f"Your {plan.title()} plan allows {max_batch} drawing(s) per batch. Only the first {max_batch} will be analyzed.")
        uploaded_files = uploaded_files[:max_batch]

    if uploaded_files:
        # Preview
        if len(uploaded_files) == 1 and uploaded_files[0].name.lower().endswith(".pdf"):
            st.info(f"📄 PDF: `{uploaded_files[0].name}` — converting pages to images…")
        elif len(uploaded_files) == 1:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(uploaded_files[0], use_column_width=True)
            with col2:
                st.markdown(f"**`{uploaded_files[0].name}`**")
                st.caption(f"{uploaded_files[0].size / 1024:.1f} KB · {discipline} · {detail_level}")
        else:
            cols = st.columns(min(len(uploaded_files), 5))
            for i, f in enumerate(uploaded_files):
                with cols[i % 5]:
                    if not f.name.lower().endswith(".pdf"):
                        st.image(f, use_column_width=True, caption=f.name[:15])
                    else:
                        st.markdown(f"📄 `{f.name[:15]}`")

        st.markdown("---")

        if st.button(f"⚙ Analyze {len(uploaded_files)} Drawing(s)", type="primary", use_container_width=True):
            if not api_key:
                st.error("Enter your OpenAI API key in the sidebar first.")
            else:
                for uploaded_file in uploaded_files:
                    fname = uploaded_file.name
                    file_bytes = uploaded_file.read()
                    file_size_kb = len(file_bytes) / 1024

                    with st.expander(f"📄 {fname}", expanded=True):
                        with st.spinner(f"Analyzing {fname}…"):
                            try:
                                is_pdf = fname.lower().endswith(".pdf")

                                if is_pdf:
                                    pages = pdf_to_images(file_bytes, dpi=200, max_pages=10)
                                    if not pages:
                                        st.error("Could not extract pages from PDF.")
                                        continue
                                    st.caption(f"Extracted {len(pages)} page(s) from PDF")
                                    result = analyze_pdf_pages(pages, discipline, detail_level, api_key)
                                else:
                                    b64, mime = image_file_to_b64(file_bytes, fname)
                                    result = analyze_image(b64, mime, discipline, detail_level, api_key)

                                # Save to DB
                                saved = save_analysis(
                                    user_id=user["id"],
                                    filename=fname,
                                    result=result,
                                    file_size_kb=file_size_kb,
                                    analysis_mode=discipline,
                                    detail_level=detail_level,
                                    workspace_id=workspace_id,
                                )
                                refresh_profile()
                                profile = get_current_profile() or {}
                                render_result(result, fname, saved.get("id"))

                            except Exception as e:
                                st.error(f"Analysis failed: {str(e)}")

    else:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">⚙</div>
            <h3>Upload a drawing to get started</h3>
            <p>Supports mechanical, structural, electrical, architectural drawings<br>PNG · JPG · WEBP""" +
            (" · PDF" if limits.get("pdf") else "") + """</p>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: HISTORY
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📋 History":
    st.markdown("## Analysis History")

    analyses = get_analyses(user["id"], limit=100, workspace_id=workspace_id)

    if not analyses:
        st.markdown('<div class="empty-state"><div class="icon">📋</div><h3>No analyses yet</h3><p>Analyze your first drawing to see it here.</p></div>', unsafe_allow_html=True)
    else:
        # Filter bar
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search = st.text_input("Search", placeholder="Part name, filename…", label_visibility="collapsed")
        with col2:
            type_filter = st.selectbox("Type", ["All Types", "Mechanical", "Structural", "Electrical", "Architectural", "PCB", "Welding"], label_visibility="collapsed")
        with col3:
            # Export all
            if limits.get("export"):
                csv_buf = io.StringIO()
                w = csv.writer(csv_buf)
                w.writerow(["ID", "Filename", "Date", "Drawing Type", "Part Name", "Material",
                             "Complexity", "Confidence", "Critical Flags", "Warnings"])
                for a in analyses:
                    w.writerow([a["id"], a["filename"], a["created_at"], a.get("drawing_type"),
                                 a.get("part_name"), a.get("material"), a.get("estimated_complexity"),
                                 a.get("confidence_score"), a.get("flag_critical_count", 0),
                                 a.get("flag_warning_count", 0)])
                st.download_button("⬇ Export CSV", csv_buf.getvalue(),
                    file_name=f"drawingiq_history_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv", use_container_width=True)
            else:
                if st.button("⬇ Export (Starter+)", use_container_width=True):
                    st.info("Upgrade to Starter or higher to export history.")

        # Filter
        filtered = analyses
        if search:
            s = search.lower()
            filtered = [a for a in filtered if s in (a.get("filename") or "").lower()
                        or s in (a.get("part_name") or "").lower()]
        if type_filter != "All Types":
            filtered = [a for a in filtered if a.get("drawing_type") == type_filter]

        st.caption(f"Showing {len(filtered)} of {len(analyses)} analyses")
        st.markdown("---")

        for a in filtered:
            crit = a.get("flag_critical_count", 0)
            warn = a.get("flag_warning_count", 0)
            dt   = a.get("created_at", "")[:10]
            conf = a.get("confidence_score", 0)

            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"""
                <div class="history-row">
                    <div>
                        <div style="font-weight:600;color:#1a1d2e;font-size:0.92rem;">{a.get('filename','')}</div>
                        <div style="font-size:0.78rem;color:#6b7280;margin-top:2px;">
                            {a.get('drawing_type','—')} · {a.get('part_name','—')} · {a.get('material','—')}
                        </div>
                    </div>
                    <div style="text-align:right;font-size:0.78rem;">
                        <div style="color:#6b7280;">{dt}</div>
                        {'<span style="color:#dc2626;font-weight:600;">⚠ '+str(crit)+' critical</span>' if crit else ''}
                        {('<span style="color:#d97706;"> '+str(warn)+' warn</span>') if warn else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button(f"View", key=f"view_{a['id']}", use_container_width=True):
                    st.session_state["viewing_analysis"] = a["id"]
            with col3:
                if st.button("🗑", key=f"del_{a['id']}", help="Delete this analysis"):
                    delete_analysis(a["id"], user["id"])
                    st.rerun()

        # Show selected analysis
        if "viewing_analysis" in st.session_state:
            aid = st.session_state["viewing_analysis"]
            record = get_analysis_by_id(aid)
            if record:
                st.markdown("---")
                st.markdown(f"### {record['filename']}")
                render_result(record["result_json"], record["filename"], aid)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: TEAM
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "👥 Team":
    st.markdown("## Team Workspaces")

    if not limits.get("team"):
        st.markdown("""
        <div class="upgrade-banner" style="max-width:600px;">
            <strong>Team workspaces require Pro or Enterprise</strong>
            Collaborate with your team, share analyses, and manage drawing history together.
        </div>
        """, unsafe_allow_html=True)
        if st.button("Upgrade to Pro →", type="primary"):
            st.session_state["force_page"] = "💳 Billing"
            st.rerun()
        st.stop()

    workspaces = get_user_workspaces(user["id"])

    col1, col2 = st.columns([2, 1])
    with col2:
        with st.expander("+ Create Workspace"):
            ws_name = st.text_input("Workspace Name", placeholder="Acme Mfg – QA Team")
            if st.button("Create", type="primary"):
                if ws_name:
                    create_workspace(user["id"], ws_name)
                    st.success(f"Workspace '{ws_name}' created!")
                    st.rerun()

    if not workspaces:
        st.markdown('<div class="empty-state"><div class="icon">👥</div><h3>No workspaces yet</h3><p>Create a workspace to collaborate with your team.</p></div>', unsafe_allow_html=True)
    else:
        for ws_entry in workspaces:
            ws_data = ws_entry.get("workspaces") or {}
            ws_id   = ws_data.get("id")
            ws_name = ws_data.get("name", "Unnamed")
            my_role = ws_entry.get("role", "member")

            with st.expander(f"🏢 {ws_name}  ({my_role})", expanded=True):
                members = get_workspace_members(ws_id)

                # Member list
                for m in members:
                    p = m.get("profiles") or {}
                    name    = p.get("full_name") or p.get("email", "Unknown")
                    email   = p.get("email", "")
                    role    = m.get("role", "member")
                    initials = "".join([x[0].upper() for x in name.split()[:2]])

                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        st.markdown(f"""
                        <div class="team-member-row">
                            <div class="avatar">{initials}</div>
                            <div style="flex:1">
                                <div style="font-weight:500;color:#1a1d2e;font-size:0.9rem;">{name}</div>
                                <div style="font-size:0.78rem;color:#6b7280;">{email}</div>
                            </div>
                            <span class="role-badge role-{role}">{role}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_b:
                        uid = p.get("id")
                        if my_role in ("owner", "admin") and uid and uid != user["id"]:
                            if st.button("Remove", key=f"rm_{ws_id}_{uid}"):
                                remove_member(ws_id, uid)
                                st.rerun()

                # Invite
                if my_role in ("owner", "admin"):
                    st.markdown("---")
                    inv_col1, inv_col2, inv_col3 = st.columns([3, 1, 1])
                    with inv_col1:
                        inv_email = st.text_input("Invite by email", key=f"inv_email_{ws_id}", placeholder="engineer@company.com", label_visibility="collapsed")
                    with inv_col2:
                        inv_role = st.selectbox("Role", ["member", "admin", "viewer"], key=f"inv_role_{ws_id}", label_visibility="collapsed")
                    with inv_col3:
                        if st.button("Invite", key=f"invite_{ws_id}", type="primary"):
                            try:
                                invite_member(ws_id, user["id"], inv_email, inv_role)
                                st.success(f"Invited {inv_email}!")
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: BILLING
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "💳 Billing":
    render_pricing_page(user["id"], profile.get("email", ""), plan)

    # Show current stats
    st.markdown("---")
    st.markdown("### Your Usage")
    stats = get_usage_stats(user["id"])
    col1, col2, col3 = st.columns(3)
    col1.metric("This Month", stats.get("analyses_this_month", 0))
    col2.metric("All Time", stats.get("analyses_total", 0))
    col3.metric("Limit / Month", stats.get("limit_this_month", 5) if stats.get("limit_this_month", 5) < 99999 else "∞")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: ACCOUNT
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚙ Account":
    st.markdown("## Account Settings")
    from database import update_profile

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("### Profile")
        new_name    = st.text_input("Full Name",    value=profile.get("full_name") or "")
        new_company = st.text_input("Company",      value=profile.get("company") or "")
        st.text_input("Email", value=profile.get("email", ""), disabled=True)
        if st.button("Save Profile", type="primary"):
            update_profile(user["id"], {"full_name": new_name, "company": new_company})
            refresh_profile()
            st.success("Profile updated!")
    with col2:
        st.markdown("### API Keys")
        st.text_input("OpenAI API Key", type="password",
            value=os.getenv("OPENAI_API_KEY", ""),
            help="Set OPENAI_API_KEY in your .env or Streamlit secrets for permanent storage.")
        st.caption("API keys are never stored in our database.")

        st.markdown("### Current Plan")
        st.markdown(f"**Plan:** {plan.title()}")
        lim = get_plan_limits(plan)
        st.markdown(f"**Analyses:** {profile.get('analyses_this_month',0)} / {lim['analyses_per_month']} this month")
        st.markdown(f"**Batch size:** {lim['batch_size']} drawings")
        st.markdown(f"**PDF support:** {'✓' if lim['pdf'] else '✗'}")
        st.markdown(f"**Team workspaces:** {'✓' if lim['team'] else '✗'}")

    st.markdown("---")
    st.markdown("### Danger Zone")
    with st.expander("Delete Account"):
        st.error("This will permanently delete your account and all analyses. This cannot be undone.")
        confirm = st.text_input("Type DELETE to confirm")
        if st.button("Delete My Account", type="primary"):
            if confirm == "DELETE":
                st.warning("Please contact support@drawingiq.com to delete your account.")
            else:
                st.error("Type DELETE to confirm.")