import streamlit as st
import os
import html as html_lib

# ── Secrets → env vars ────────────────────────────────────────────────────────
for key in ["OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_ANON_KEY",
            "APP_URL", "SUPABASE_SERVICE_KEY"]:
    if key in st.secrets:
        os.environ[key] = st.secrets[key]

# ── Stdlib imports ─────────────────────────────────────────────────────────────
import json
import io
import csv
import logging
from datetime import datetime, date

# ── Startup: fail fast on missing API key ─────────────────────────────────────
_api_key = os.getenv("OPENAI_API_KEY", "")
if not _api_key:
    st.error("⚠️ OpenAI API key is not configured. "
             "Please add OPENAI_API_KEY to your Streamlit secrets.")
    st.stop()

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="DrawingIQ",
    page_icon="⚙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Local imports ──────────────────────────────────────────────────────────────
from auth import (init_session, is_logged_in, get_current_user,
                  get_current_profile, logout, render_auth_page, refresh_profile)
from database import (
    get_profile, save_analysis, get_analyses, get_analysis_by_id,
    delete_analysis, get_plan_limits, can_analyze,
    create_workspace, get_user_workspaces, get_workspace_members,
    invite_member, remove_member, get_usage_stats, PLAN_LIMITS,
    update_profile,
)
from billing import render_pricing_page, render_usage_bar, PLANS
from analyzer import analyze_image, analyze_pdf_pages
from pdf_utils import pdf_to_images, image_file_to_b64, get_pdf_page_count

init_session()

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Hide Streamlit share / deploy button */
#MainMenu { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { display: none !important; }
footer { visibility: hidden; }
.stDeployButton { display: none !important; }
button[title="View app in Streamlit Community Cloud"] { display: none !important; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020d1f 0%, #030f24 100%);
    border-right: 1px solid rgba(30,100,255,0.2);
}
[data-testid="stSidebar"] * { color: #7aa2d4 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #e2e8f0 !important; }

.main { background: #f0f4ff; }

.app-header {
    background: linear-gradient(90deg, #020d1f, #030f24);
    color: #e2e8f0;
    padding: 1rem 2rem; margin: -1rem -1rem 1.5rem -1rem;
    display: flex; align-items: center; justify-content: space-between;
    border-bottom: 2px solid #1d4ed8;
    box-shadow: 0 2px 20px rgba(0,0,0,0.3);
}
.app-header-left { display: flex; align-items: center; gap: 1rem; }
.app-title { font-size: 1.4rem; font-weight: 700; letter-spacing: -0.02em; color: white; }
.app-title span { color: #3b82f6; }
.app-subtitle { font-size: 0.72rem; color: #4a6fa5; margin-top: 2px;
                letter-spacing: 0.1em; text-transform: uppercase; }
.plan-badge { font-size: 0.7rem; font-weight: 700; padding: 3px 9px;
              border-radius: 4px; text-transform: uppercase; letter-spacing: 0.06em; }
.badge-free       { background: rgba(30,100,255,0.15); color: #60a5fa;
                    border: 1px solid rgba(30,100,255,0.3); }
.badge-starter    { background: #bfdbfe; color: #1e40af; }
.badge-pro        { background: #fde68a; color: #92400e; }
.badge-enterprise { background: #ddd6fe; color: #5b21b6; }

.logo-box {
    width: 38px; height: 38px;
    background: linear-gradient(135deg, #1d4ed8, #2563eb);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem;
    box-shadow: 0 0 12px rgba(37,99,235,0.4);
}

/* ── Quick-settings bar ── */
.quick-bar {
    background: white; border: 1px solid #dbeafe; border-radius: 10px;
    padding: 0.9rem 1.25rem; margin-bottom: 1rem;
    display: flex; gap: 1.5rem; align-items: center; flex-wrap: wrap;
    box-shadow: 0 2px 8px rgba(30,100,255,0.05);
}
.quick-bar-label { font-size: 0.75rem; color: #6b7280; text-transform: uppercase;
                   letter-spacing: 0.05em; margin-bottom: 2px; }

/* ── Drop zone ── */
.drop-zone-hint {
    border: 2px dashed #93c5fd; border-radius: 12px;
    background: #eff6ff; padding: 2.5rem 2rem; text-align: center;
    margin-bottom: 1rem; color: #1d4ed8;
}
.drop-zone-hint .dz-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
.drop-zone-hint h3 { color: #1d4ed8; font-weight: 600; margin-bottom: 0.25rem; }
.drop-zone-hint p  { color: #60a5fa; font-size: 0.85rem; }

/* ── Result cards ── */
.result-card { background:white; border:1px solid #dbeafe; border-radius:10px;
               padding:1.5rem; margin:1rem 0;
               box-shadow:0 2px 8px rgba(30,100,255,0.06); }
.metric-strip { display:flex; gap:0.75rem; margin:1rem 0; flex-wrap:wrap; }
.metric-box { background:white; border:1px solid #dbeafe; border-radius:8px;
              padding:0.9rem 1.1rem; flex:1; min-width:110px;
              box-shadow:0 2px 8px rgba(30,100,255,0.05); }
.metric-box .label { font-size:0.72rem; color:#6b7280; text-transform:uppercase;
                     letter-spacing:0.05em; }
.metric-box .value { font-size:1.25rem; font-weight:600; color:#0f172a;
                     font-family:'IBM Plex Mono',monospace; margin-top:3px; }
.metric-box .value.small { font-size:0.95rem; }

.flag-item { border-left:3px solid #2563eb; padding:0.6rem 0.9rem;
             margin:0.4rem 0; border-radius:0 6px 6px 0; font-size:0.88rem; }
.flag-critical { border-left-color:#dc2626; background:#fff5f5; color:#2d0e0e; }
.flag-warning  { border-left-color:#d97706; background:#fffbee; color:#3d2e00; }
.flag-info     { border-left-color:#2563eb; background:#eff6ff; color:#1e3a5f; }

.drawing-type-tag {
    display:inline-block;
    background:linear-gradient(135deg,#1d4ed8,#2563eb);
    color:white; font-size:0.78rem; font-weight:700; padding:4px 12px;
    border-radius:4px; letter-spacing:0.08em; text-transform:uppercase;
    margin-bottom:1rem; box-shadow:0 2px 8px rgba(37,99,235,0.3);
}

.dim-table { width:100%; border-collapse:collapse; font-size:0.88rem; }
.dim-table th { background:#eff6ff; text-align:left; padding:7px 10px;
                font-size:0.75rem; text-transform:uppercase;
                letter-spacing:0.05em; color:#1d4ed8; }
.dim-table td { padding:7px 10px; border-bottom:1px solid #dbeafe;
                color:#374151; font-family:'IBM Plex Mono',monospace;
                font-size:0.83rem; }
.dim-table .critical-row td { background:#fff5f5; }

.history-row {
    background:white; border:1px solid #dbeafe; border-radius:8px;
    padding:0.8rem 1rem; margin:0.4rem 0;
    box-shadow:0 1px 4px rgba(30,100,255,0.06);
}
.history-row:hover { border-color:#2563eb;
                     box-shadow:0 2px 12px rgba(37,99,235,0.15); }

.team-member-row { background:white; border:1px solid #dbeafe; border-radius:8px;
                   padding:0.7rem 1rem; margin:0.3rem 0;
                   display:flex; align-items:center; gap:1rem; }
.avatar { width:36px; height:36px; border-radius:50%;
          background:linear-gradient(135deg,#1d4ed8,#2563eb); color:white;
          display:flex; align-items:center; justify-content:center;
          font-weight:700; font-size:0.8rem; flex-shrink:0; }
.role-badge { font-size:0.72rem; font-weight:600; padding:2px 8px;
              border-radius:10px; }
.role-owner  { background:#fef3c7; color:#92400e; }
.role-admin  { background:#e0f2fe; color:#075985; }
.role-member { background:#eff6ff; color:#1d4ed8; }
.role-viewer { background:#ede9fe; color:#5b21b6; }

.empty-state { text-align:center; padding:3rem 2rem; color:#9ca3af; }
.empty-state .icon { font-size:2.5rem; }
.empty-state h3 { color:#374151; margin:0.75rem 0 0.4rem; font-weight:600; }

.upgrade-banner {
    background:linear-gradient(135deg,#1d4ed8,#2563eb); color:white;
    border-radius:10px; padding:1rem 1.25rem; margin:0.5rem 0;
    text-align:center; box-shadow:0 4px 15px rgba(37,99,235,0.3);
}
.upgrade-banner strong { display:block; margin-bottom:0.25rem; }

button[kind="primary"] { background:linear-gradient(135deg,#1d4ed8,#2563eb) !important;
                         border:none !important; }

/* Confirm-delete warning row */
.confirm-delete-row {
    background:#fff5f5; border:1px solid #fca5a5; border-radius:8px;
    padding:0.6rem 1rem; margin:0.2rem 0; display:flex;
    align-items:center; gap:0.75rem; font-size:0.85rem; color:#7f1d1d;
}
</style>
""", unsafe_allow_html=True)

# ── Auth gate ──────────────────────────────────────────────────────────────────
if not is_logged_in():
    render_auth_page()
    st.stop()

user    = get_current_user()
profile = get_current_profile() or {}

if not profile:
    refresh_profile()
    profile = get_current_profile() or {}

plan        = profile.get("plan", "free")
limits      = get_plan_limits(plan)
plan_badge  = f'<span class="plan-badge badge-{plan}">{html_lib.escape(plan.upper())}</span>'
user_name = (
    user.get("full_name")               # set at login time
    or profile.get("full_name")         # from DB profile
    or profile.get("email", "")         # fallback to email
    or user.get("email", "")
).strip() or "User"
user_initials = "".join([p[0].upper() for p in user_name.split()[:2]])
safe_name     = html_lib.escape(user_name)
safe_initials = html_lib.escape(user_initials)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="app-header">
    <div class="app-header-left">
        <div class="logo-box">⚙</div>
        <div>
            <div class="app-title">Drawing<span>IQ</span></div>
            <div class="app-subtitle">Enterprise Engineering Drawing Intelligence</div>
        </div>
        {plan_badge}
    </div>
    <div style="display:flex;align-items:center;gap:0.75rem;font-size:0.85rem;color:#4a6fa5;">
        <div style="background:linear-gradient(135deg,#1d4ed8,#2563eb);border-radius:50%;
                    width:32px;height:32px;display:flex;align-items:center;
                    justify-content:center;font-weight:700;color:white;font-size:0.8rem;">
            {safe_initials}
        </div>
        <span style="color:#7aa2d4;">{safe_name}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙ DrawingIQ")
    st.markdown("---")

    used = profile.get("analyses_this_month", 0)
    cap  = limits["analyses_per_month"]
    render_usage_bar(used, cap, plan)

    if plan == "free" and used >= 3:
        st.markdown("""
        <div class="upgrade-banner">
            <strong>Running low on analyses</strong>
            Upgrade for 50–300/month
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    workspaces   = get_user_workspaces(user["id"])
    workspace_id = None
    if workspaces and limits.get("team"):
        ws_options = {"Personal": None}
        for ws in workspaces:
            ws_data = ws.get("workspaces") or {}
            ws_options[ws_data.get("name", "Unnamed")] = ws_data.get("id")
        selected_ws  = st.selectbox("Workspace", list(ws_options.keys()))
        workspace_id = ws_options[selected_ws]
        st.markdown("---")

    # ── Navigation (force_page support) ───────────────────────────────────────
    NAV_ITEMS = ["📤 Analyze", "📋 History", "👥 Team", "💳 Billing", "⚙ Account"]
    _forced    = st.session_state.pop("force_page", None)
    _nav_index = NAV_ITEMS.index(_forced) if _forced in NAV_ITEMS else 0

    page = st.radio("Navigate", NAV_ITEMS,
                    index=_nav_index,
                    label_visibility="collapsed")

    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        logout()


# ── Friendly error messages ────────────────────────────────────────────────────
def friendly_error(exc: Exception) -> str:
    msg = str(exc)
    if "rate_limit" in msg.lower() or "429" in msg:
        return "The AI service is busy right now. Please wait a moment and try again."
    if "timeout" in msg.lower():
        return "The request timed out. Check your connection and try again."
    if "json" in msg.lower() or "decode" in msg.lower():
        return "The AI returned an unexpected response. Please try again."
    if "api_key" in msg.lower() or "authentication" in msg.lower():
        return "API authentication failed. Please contact your administrator."
    logger.error("Analysis error: %s", exc, exc_info=True)
    return "Analysis failed. Please try again or contact support if this persists."


# ── Result renderer ────────────────────────────────────────────────────────────
def render_result(result: dict, filename: str, analysis_id: str = None):
    flags    = result.get("flags", [])
    critical = [f for f in flags if f.get("severity") == "critical"]
    warnings = [f for f in flags if f.get("severity") == "warning"]
    info_f   = [f for f in flags if f.get("severity") == "info"]
    dims     = result.get("dimensions", [])
    conf     = result.get("confidence_score", 0)

    dtype   = html_lib.escape(str(result.get("drawing_type", "Unknown")))
    clarity = result.get("drawing_clarity", "Unknown")
    clarity_color = {
        "Clear": "#16a34a", "Partially Legible": "#d97706",
        "Difficult to Read": "#dc2626", "Unclear": "#dc2626",
    }.get(clarity, "#6b7280")

    st.markdown(f'<span class="drawing-type-tag">{dtype}</span>',
                unsafe_allow_html=True)

    if conf < 60:
        st.warning(
            f"⚠️ **Low confidence ({conf}%)** — The drawing may be blurry or low-resolution. "
            f"Results may be incomplete. Upload a cleaner scan for best accuracy."
        )

    pn  = html_lib.escape(str(result.get("part_name")  or "Unknown"))
    pno = html_lib.escape(str(result.get("part_number") or "Unknown"))
    rev = html_lib.escape(str(result.get("revision")    or "Unknown"))
    mat = html_lib.escape(str(result.get("material")    or "Unknown"))
    unt = html_lib.escape(str(result.get("units")       or "Unknown"))
    cmp = html_lib.escape(str(result.get("estimated_complexity") or "Unknown"))
    tsr = html_lib.escape(str(result.get("tolerance_stack_risk") or "Unknown"))
    crit_color = '#dc2626' if critical else '#16a34a'

    st.markdown(f"""
    <div class="metric-strip">
        <div class="metric-box"><div class="label">Part</div><div class="value small">{pn}</div></div>
        <div class="metric-box"><div class="label">P/N</div><div class="value small">{pno}</div></div>
        <div class="metric-box"><div class="label">Rev</div><div class="value small">{rev}</div></div>
        <div class="metric-box"><div class="label">Material</div><div class="value small">{mat}</div></div>
        <div class="metric-box"><div class="label">Units</div><div class="value small">{unt}</div></div>
        <div class="metric-box"><div class="label">Complexity</div><div class="value small">{cmp}</div></div>
        <div class="metric-box"><div class="label">Confidence</div><div class="value">{conf}%</div></div>
        <div class="metric-box"><div class="label">Clarity</div>
            <div class="value small" style="color:{clarity_color}">{html_lib.escape(clarity)}</div></div>
        <div class="metric-box"><div class="label">Flags</div>
            <div class="value small" style="color:{crit_color}">{len(critical)}c · {len(warnings)}w</div></div>
        <div class="metric-box"><div class="label">Tol. Stack Risk</div>
            <div class="value small">{tsr}</div></div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🚩 Flags", "📐 Dimensions", "🔧 Machinist Notes",
        "📋 Specs", "💰 Quote", "📝 Raw Notes", "🖨 Print", "⬇ Export"
    ])

    with tab1:
        if not flags:
            st.success("✓ No flags raised. Drawing looks clean.")
        if critical:
            st.markdown("**Critical**")
            for f in critical:
                st.markdown(
                    f'<div class="flag-item flag-critical">'
                    f'<strong>{html_lib.escape(str(f.get("category","")))}</strong>: '
                    f'{html_lib.escape(str(f.get("description","")))}<br>'
                    f'<span style="color:#6b7280;font-size:0.82rem;">→ '
                    f'{html_lib.escape(str(f.get("recommendation","")))}</span></div>',
                    unsafe_allow_html=True,
                )
        if warnings:
            st.markdown("**Warnings**")
            for f in warnings:
                st.markdown(
                    f'<div class="flag-item flag-warning">'
                    f'<strong>{html_lib.escape(str(f.get("category","")))}</strong>: '
                    f'{html_lib.escape(str(f.get("description","")))}<br>'
                    f'<span style="color:#6b7280;font-size:0.82rem;">→ '
                    f'{html_lib.escape(str(f.get("recommendation","")))}</span></div>',
                    unsafe_allow_html=True,
                )
        if info_f:
            st.markdown("**Info**")
            for f in info_f:
                st.markdown(
                    f'<div class="flag-item flag-info">'
                    f'<strong>{html_lib.escape(str(f.get("category","")))}</strong>: '
                    f'{html_lib.escape(str(f.get("description","")))}</div>',
                    unsafe_allow_html=True,
                )
        concerns = result.get("manufacturing_concerns", [])
        if concerns:
            st.markdown("---\n**Manufacturing Concerns**")
            for c in concerns:
                st.markdown(f"• {c}")

    with tab2:
        if dims:
            rows = "".join([
                f'<tr class="{"critical-row" if d.get("is_critical") else ""}">'
                f'<td>{html_lib.escape(str(d.get("feature","")))}</td>'
                f'<td>{html_lib.escape(str(d.get("value","")))}</td>'
                f'<td>{html_lib.escape(str(d.get("tolerance") or "—"))}</td>'
                f'<td>{html_lib.escape(str(d.get("unit","")))}</td>'
                f'<td>{"🔴" if d.get("is_critical") else ""}</td></tr>'
                for d in dims
            ])
            st.markdown(
                f'<table class="dim-table"><thead><tr>'
                f'<th>Feature</th><th>Value</th><th>Tolerance</th>'
                f'<th>Unit</th><th></th></tr></thead><tbody>{rows}</tbody></table>',
                unsafe_allow_html=True,
            )
        else:
            st.info("No structured dimensions extracted.")

        gdt = result.get("gdt_callouts", [])
        if gdt:
            st.markdown("**GD&T Callouts**")
            for g in gdt:
                sym  = g.get("symbol", "")
                feat = g.get("feature", "")
                val  = g.get("value", "")
                dat  = g.get("datum", "")
                st.markdown(f"`{sym}` **{feat}**: {val}" +
                            (f" (Datum {dat})" if dat else ""))

    with tab3:
        note = result.get("machinist_notes", "")
        if note:
            st.markdown(
                f'<div class="result-card">'
                f'<p style="line-height:1.9;color:#374151;">'
                f'{html_lib.escape(str(note))}</p></div>',
                unsafe_allow_html=True,
            )
        procs = result.get("recommended_processes", [])
        if procs:
            st.markdown("**Recommended Processes**")
            cols = st.columns(min(len(procs), 4))
            for i, p in enumerate(procs):
                cols[i % len(cols)].markdown(
                    f'<div style="background:#eff6ff;border-radius:6px;padding:0.5rem 0.8rem;'
                    f'font-size:0.83rem;text-align:center;font-weight:500;color:#1d4ed8;">'
                    f'{html_lib.escape(str(p))}</div>',
                    unsafe_allow_html=True,
                )
        standards = result.get("standards_referenced", [])
        if standards:
            st.markdown("**Standards Referenced:** " +
                        " · ".join([f"`{s}`" for s in standards]))

    with tab4:
        fields = [
            ("Part Name",     "part_name"),
            ("Part Number",   "part_number"),
            ("Revision",      "revision"),
            ("Scale",         "scale"),
            ("Sheet",         "sheet_info"),
            ("Material",      "material"),
            ("Material Spec", "material_spec"),
            ("Surface Finish","surface_finish"),
            ("Heat Treatment","heat_treatment"),
            ("Weight Estimate","weight_estimate"),
        ]
        rows = "".join([
            f'<tr>'
            f'<td style="color:#6b7280;font-size:0.83rem;padding:7px 10px;">{label}</td>'
            f'<td style="font-family:IBM Plex Mono,monospace;font-size:0.83rem;padding:7px 10px;">'
            f'{html_lib.escape(str(result.get(key) or "—"))}</td></tr>'
            for label, key in fields
        ])
        st.markdown(
            f'<table class="dim-table"><tbody>{rows}</tbody></table>',
            unsafe_allow_html=True,
        )
        with st.expander("Raw JSON"):
            st.json(result)

    # ── Quote tab ─────────────────────────────────────────────────────────────
    with tab5:
        from analyzer import estimate_quote
        st.markdown("### 💰 Job Cost Estimator")
        st.caption(
            "Enter your shop rates below. The estimate is based on detected complexity "
            "and visible drawing features. Always review before sending to a customer."
        )

        if result.get("estimated_complexity", "Unknown") == "Unknown":
            st.warning("Complexity could not be determined from this drawing. "
                       "Enter hours manually or re-analyze with Deep Review.")

        st.markdown("---")
        st.markdown("**Shop Rates**")
        qc1, qc2, qc3 = st.columns(3)
        with qc1:
            machine_rate = st.number_input("Machine Rate ($/hr)", min_value=0.0, value=85.0, step=5.0, key=f"q_mr_{analysis_id}")
            labor_rate   = st.number_input("Labor Rate ($/hr)",   min_value=0.0, value=65.0, step=5.0, key=f"q_lr_{analysis_id}")
        with qc2:
            mat_cost_kg  = st.number_input("Material Cost ($/kg)", min_value=0.0, value=5.0, step=0.5, key=f"q_mc_{analysis_id}")
            mat_density  = st.number_input("Material Density (kg/m³)", min_value=100.0, value=2700.0, step=100.0,
                                           key=f"q_md_{analysis_id}",
                                           help="Al=2700, Steel=7850, SS=8000, Ti=4500, Brass=8500, Copper=8960")
        with qc3:
            overhead_pct = st.number_input("Overhead (%)",      min_value=0.0, value=15.0, step=1.0, key=f"q_oh_{analysis_id}")
            profit_pct   = st.number_input("Profit Margin (%)", min_value=0.0, value=20.0, step=1.0, key=f"q_pm_{analysis_id}")

        qc4, qc5 = st.columns(2)
        with qc4:
            setup_cost = st.number_input("Fixed Setup Cost ($)", min_value=0.0, value=50.0, step=10.0, key=f"q_sc_{analysis_id}")
        with qc5:
            quantity   = st.number_input("Quantity", min_value=1, value=1, step=1, key=f"q_qty_{analysis_id}")

        st.markdown("**Customer Info (for quote export)**")
        qd1, qd2 = st.columns(2)
        with qd1:
            customer_name = st.text_input("Customer Name", placeholder="Acme Corp", key=f"q_cn_{analysis_id}")
            customer_email= st.text_input("Customer Email", placeholder="buyer@acme.com", key=f"q_ce_{analysis_id}")
        with qd2:
            quote_number  = st.text_input("Quote #", placeholder="Q-2026-001", key=f"q_qn_{analysis_id}")
            due_date      = st.text_input("Delivery / Due Date", placeholder="2026-06-01", key=f"q_dd_{analysis_id}")

        shop_notes = st.text_area("Internal Notes (not shown on quote)", placeholder="Needs 4th axis, check stock...", key=f"q_sn_{analysis_id}", height=80)

        st.markdown("---")
        if st.button("⚙ Calculate Estimate", type="primary", key=f"q_calc_{analysis_id}"):
            shop_rates = {
                "machine_rate_per_hr":    machine_rate,
                "labor_rate_per_hr":      labor_rate,
                "material_cost_per_kg":   mat_cost_kg,
                "material_density_kg_m3": mat_density,
                "overhead_pct":           overhead_pct,
                "profit_margin_pct":      profit_pct,
                "setup_cost":             setup_cost,
                "quantity":               quantity,
            }
            q = estimate_quote(result, shop_rates)
            st.session_state[f"quote_{analysis_id}"] = q
            st.session_state[f"quote_meta_{analysis_id}"] = {
                "customer_name":  customer_name,
                "customer_email": customer_email,
                "quote_number":   quote_number,
                "due_date":       due_date,
                "shop_notes":     shop_notes,
            }

        if f"quote_{analysis_id}" in st.session_state:
            q    = st.session_state[f"quote_{analysis_id}"]
            meta = st.session_state.get(f"quote_meta_{analysis_id}", {})

            st.markdown("#### Estimate Results")
            rc1, rc2, rc3, rc4 = st.columns(4)
            rc1.metric("Price Per Part", f"${q['price_per_part']:,.2f}")
            rc2.metric("Total Job Cost", f"${q['total_job_cost']:,.2f}")
            rc3.metric("Quantity",       str(q['quantity']))
            rc4.metric("Complexity",     q['complexity'])

            st.markdown(f"""
            <div class="result-card" style="font-size:0.88rem;">
            <table style="width:100%;border-collapse:collapse;">
            <tr><td style="padding:5px 10px;color:#6b7280;">Machine Cost</td><td style="font-family:monospace;padding:5px 10px;">${q['machine_cost']:,.2f}</td>
                <td style="padding:5px 10px;color:#6b7280;">Machine Hrs/Part</td><td style="font-family:monospace;padding:5px 10px;">{q['machine_hours_per_part']} hr</td></tr>
            <tr style="background:#f8faff;"><td style="padding:5px 10px;color:#6b7280;">Labor Cost</td><td style="font-family:monospace;padding:5px 10px;">${q['labor_cost']:,.2f}</td>
                <td style="padding:5px 10px;color:#6b7280;">Labor Hrs/Part</td><td style="font-family:monospace;padding:5px 10px;">{q['labor_hours_per_part']} hr</td></tr>
            <tr><td style="padding:5px 10px;color:#6b7280;">Material Cost</td><td style="font-family:monospace;padding:5px 10px;">${q['material_cost']:,.2f}</td>
                <td style="padding:5px 10px;color:#6b7280;">Material Note</td><td style="font-family:monospace;padding:5px 10px;font-size:0.8rem;">{html_lib.escape(q['material_note'])}</td></tr>
            <tr style="background:#f8faff;"><td style="padding:5px 10px;color:#6b7280;">Setup Cost</td><td style="font-family:monospace;padding:5px 10px;">${q['setup_cost']:,.2f}</td>
                <td style="padding:5px 10px;color:#6b7280;">Setups</td><td style="font-family:monospace;padding:5px 10px;">{q['setup_count']}</td></tr>
            <tr><td style="padding:5px 10px;color:#6b7280;">Overhead</td><td style="font-family:monospace;padding:5px 10px;">${q['overhead_amount']:,.2f}</td>
                <td style="padding:5px 10px;color:#6b7280;">Profit</td><td style="font-family:monospace;padding:5px 10px;">${q['profit_amount']:,.2f}</td></tr>
            <tr style="background:#eff6ff;font-weight:700;"><td style="padding:7px 10px;color:#1d4ed8;">TOTAL JOB</td><td style="font-family:monospace;padding:7px 10px;color:#1d4ed8;">${q['total_job_cost']:,.2f}</td>
                <td style="padding:7px 10px;color:#1d4ed8;">PER PART</td><td style="font-family:monospace;padding:7px 10px;color:#1d4ed8;">${q['price_per_part']:,.2f}</td></tr>
            </table>
            </div>
            """, unsafe_allow_html=True)

            st.caption(f"⚠️ {q['disclaimer']}")

            # Export quote as text
            now_q = datetime.now().strftime("%Y-%m-%d")
            quote_lines = [
                "=" * 60,
                "               DRAWINGIQ — SHOP QUOTE",
                "=" * 60,
                f"Quote #:       {meta.get('quote_number') or 'N/A'}",
                f"Date:          {now_q}",
                f"Delivery:      {meta.get('due_date') or 'TBD'}",
                "-" * 60,
                f"Customer:      {meta.get('customer_name') or 'N/A'}",
                f"Email:         {meta.get('customer_email') or 'N/A'}",
                "-" * 60,
                f"Part:          {result.get('part_name') or 'Unknown'}",
                f"Part Number:   {result.get('part_number') or 'Unknown'}",
                f"Revision:      {result.get('revision') or 'Unknown'}",
                f"Material:      {result.get('material') or 'Unknown'}",
                f"Drawing File:  {filename}",
                "-" * 60,
                f"Quantity:      {q['quantity']} pcs",
                f"Complexity:    {q['complexity']}",
                f"Setups:        {q['setup_count']}",
                "-" * 60,
                f"Machine Cost:  ${q['machine_cost']:,.2f}",
                f"Labor Cost:    ${q['labor_cost']:,.2f}",
                f"Material Cost: ${q['material_cost']:,.2f}",
                f"Setup Cost:    ${q['setup_cost']:,.2f}",
                f"Overhead:      ${q['overhead_amount']:,.2f}",
                f"Profit:        ${q['profit_amount']:,.2f}",
                "=" * 60,
                f"TOTAL JOB:     ${q['total_job_cost']:,.2f}",
                f"PRICE/PART:    ${q['price_per_part']:,.2f}",
                "=" * 60,
                "",
                "DISCLAIMER:",
                q['disclaimer'],
            ]
            quote_text = "\n".join(quote_lines)
            st.download_button(
                "⬇ Download Quote (.txt)",
                quote_text,
                file_name=f"quote_{meta.get('quote_number') or filename.rsplit('.',1)[0]}.txt",
                mime="text/plain",
                use_container_width=True,
            )

    # ── Raw Notes tab ──────────────────────────────────────────────────────────
    with tab6:
        st.markdown("### 📝 Raw Drawing Notes")
        st.caption("Verbatim text extracted directly from the drawing. No interpretation.")
        raw_notes = result.get("raw_notes", [])
        if raw_notes:
            for i, note in enumerate(raw_notes, 1):
                st.markdown(
                    f'<div class="flag-item flag-info">'
                    f'<strong>Note {i}:</strong> {html_lib.escape(str(note))}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No general notes were extracted from this drawing.")

        rev_hist = result.get("revision_history", [])
        if rev_hist:
            st.markdown("---\n**Revision History**")
            for r in rev_hist:
                st.markdown(f"• {html_lib.escape(str(r))}")

        related = result.get("related_parts", [])
        if related:
            st.markdown("---\n**Referenced Part Numbers**")
            for p in related:
                st.markdown(f"• `{html_lib.escape(str(p))}`")

    # ── Print tab ──────────────────────────────────────────────────────────────
    with tab7:
        st.markdown("**Print-Ready Job Traveler Summary**")
        st.caption("Copy or print this block and attach it to your job traveler.")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines   = [
            f"DRAWINGIQ JOB TRAVELER — {filename}",
            f"Generated: {now_str}",
            "=" * 60,
            f"Part:      {result.get('part_name','—')}",
            f"P/N:       {result.get('part_number','—')}",
            f"Revision:  {result.get('revision','—')}",
            f"Material:  {result.get('material','—')} ({result.get('material_spec','—')})",
            f"Finish:    {result.get('surface_finish','—')}",
            f"Heat Treat:{result.get('heat_treatment','—')}",
            f"Scale:     {result.get('scale','—')}",
            f"Sheet:     {result.get('sheet_info','—')}",
            f"Type:      {result.get('drawing_type','—')}",
            f"Complexity:{result.get('estimated_complexity','—')}",
            f"Confidence:{result.get('confidence_score',0)}%",
            "",
            f"FLAGS ({len(flags)} total — {len(critical)} critical, {len(warnings)} warnings):",
            "-" * 60,
        ]
        for f in flags:
            sev  = f.get("severity", "").upper()
            cat  = f.get("category", "")
            desc = f.get("description", "")
            rec  = f.get("recommendation", "")
            lines.append(f"  [{sev}] {cat}: {desc}")
            if rec:
                lines.append(f"         → {rec}")
        lines += [
            "",
            "MACHINIST NOTES:",
            "-" * 60,
            result.get("machinist_notes", "—"),
        ]
        if dims:
            lines += ["", "KEY DIMENSIONS:", "-" * 60]
            for d in dims:
                crit_mark = " *** CRITICAL ***" if d.get("is_critical") else ""
                lines.append(
                    f"  {d.get('feature',''): <30} "
                    f"{d.get('value','')} {d.get('unit','')}  "
                    f"±{d.get('tolerance','N/A')}{crit_mark}"
                )
        procs_txt = result.get("recommended_processes", [])
        if procs_txt:
            lines += ["", "RECOMMENDED PROCESSES:", "-" * 60]
            for p in procs_txt:
                lines.append(f"  • {p}")

        traveler_text = "\n".join(lines)
        st.text_area("Job Traveler", traveler_text, height=380,
                     key=f"print_{analysis_id or filename}")
        st.download_button(
            "⬇ Download Job Traveler (.txt)",
            traveler_text,
            file_name=f"{filename.rsplit('.',1)[0]}_traveler.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # ── Export tab ─────────────────────────────────────────────────────────────
    with tab8:
        if not limits.get("export"):
            st.markdown(
                '<div class="upgrade-banner">Export requires Starter plan or higher.</div>',
                unsafe_allow_html=True,
            )
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "⬇ JSON",
                    json.dumps(result, indent=2),
                    file_name=f"{filename.rsplit('.',1)[0]}.json",
                    mime="application/json",
                    use_container_width=True,
                )
            with c2:
                csv_buf = io.StringIO()
                w = csv.writer(csv_buf)
                w.writerow(["Field", "Value"])
                for k, v in result.items():
                    if isinstance(v, (str, int, float)):
                        w.writerow([k, v])
                for d in result.get("dimensions", []):
                    w.writerow([
                        f"DIM:{d.get('feature')}",
                        f"{d.get('value')} {d.get('unit')} ±{d.get('tolerance','N/A')}",
                    ])
                for f in result.get("flags", []):
                    w.writerow([
                        f"FLAG[{f.get('severity','').upper()}]",
                        f"{f.get('category')}: {f.get('description')}",
                    ])
                st.download_button(
                    "⬇ CSV",
                    csv_buf.getvalue(),
                    file_name=f"{filename.rsplit('.',1)[0]}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ANALYZE
# ══════════════════════════════════════════════════════════════════════════════
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

    # ── Quick-settings bar (sticky above uploader) ─────────────────────────────
    DISCIPLINES = [
        "Auto-Detect",
        "Mechanical / Machining",
        "Structural / Civil",
        "Electrical / Schematic",
        "Architectural",
        "PCB / Electronics",
        "Welding / Fabrication",
    ]
    DETAIL_LEVELS = ["Quick Scan", "Standard", "Deep Review"]

    # Persist last-used settings across reruns
    if "pref_discipline" not in st.session_state:
        st.session_state["pref_discipline"] = "Mechanical / Machining"
    if "pref_detail" not in st.session_state:
        st.session_state["pref_detail"] = "Standard"

    qc1, qc2, qc3 = st.columns([3, 2, 1])
    with qc1:
        discipline = st.selectbox(
            "Discipline",
            DISCIPLINES,
            index=DISCIPLINES.index(st.session_state["pref_discipline"])
                  if st.session_state["pref_discipline"] in DISCIPLINES else 0,
            key="qs_discipline",
        )
        st.session_state["pref_discipline"] = discipline
    with qc2:
        detail_level = st.select_slider(
            "Detail Level",
            options=DETAIL_LEVELS,
            value=st.session_state["pref_detail"],
            key="qs_detail",
        )
        st.session_state["pref_detail"] = detail_level
    with qc3:
        st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)
        st.caption(f"Plan: **{plan.title()}**")
        st.caption(f"{used}/{cap} this month")

    st.markdown("---")

    # ── File uploader with visible drop zone hint ──────────────────────────────
    accepted_types = ["png", "jpg", "jpeg", "webp"]
    if limits.get("pdf"):
        accepted_types.append("pdf")

    max_batch = limits["batch_size"]
    MAX_FILE_MB = 20

    fmt_list = " · ".join(t.upper() for t in accepted_types)
    st.markdown(f"""
    <div class="drop-zone-hint">
        <div class="dz-icon">📐</div>
        <h3>Drop your engineering drawing here</h3>
        <p>Supports {fmt_list} &nbsp;|&nbsp; Max {MAX_FILE_MB} MB per file
        &nbsp;|&nbsp; Up to {max_batch} file(s) on {plan.title()} plan</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload engineering drawings",
        type=accepted_types,
        accept_multiple_files=(max_batch > 1),
        label_visibility="collapsed",
    )

    # Normalise to list
    if not uploaded_files:
        uploaded_files = []
    elif not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]

    if len(uploaded_files) > max_batch:
        st.warning(
            f"Your {plan.title()} plan allows {max_batch} drawing(s) per batch. "
            f"Only the first {max_batch} will be analyzed."
        )
        uploaded_files = uploaded_files[:max_batch]

    if uploaded_files:
        # ── Preview ────────────────────────────────────────────────────────────
        if len(uploaded_files) == 1:
            f = uploaded_files[0]
            col1, col2 = st.columns([1, 2])
            with col1:
                if not f.name.lower().endswith(".pdf"):
                    # Read bytes for preview, then seek back so analyze can re-read
                    preview_bytes = f.read()
                    f.seek(0)
                    st.image(preview_bytes, use_container_width=True)
                else:
                    st.info(f"📄 PDF: `{f.name}`")
            with col2:
                st.markdown(f"**`{f.name}`**")
                st.caption(
                    f"{f.size / 1024:.1f} KB · {discipline} · {detail_level}"
                )
        else:
            cols = st.columns(min(len(uploaded_files), 5))
            for i, f in enumerate(uploaded_files):
                with cols[i % 5]:
                    if not f.name.lower().endswith(".pdf"):
                        preview_bytes = f.read()
                        f.seek(0)
                        st.image(preview_bytes, use_container_width=True,
                                 caption=f.name[:15])
                    else:
                        st.markdown(f"📄 `{f.name[:15]}`")

        st.markdown("---")

        if st.button(
            f"⚙ Analyze {len(uploaded_files)} Drawing(s)",
            type="primary",
            use_container_width=True,
        ):
            for uploaded_file in uploaded_files:
                fname      = uploaded_file.name
                file_bytes = uploaded_file.read()
                file_size_kb = len(file_bytes) / 1024

                # ── File-size guard ────────────────────────────────────────────
                if file_size_kb > MAX_FILE_MB * 1024:
                    st.error(
                        f"**{fname}** is {file_size_kb/1024:.1f} MB — "
                        f"max allowed is {MAX_FILE_MB} MB. Skipping."
                    )
                    continue

                with st.expander(f"📄 {fname}", expanded=True):
                    try:
                        is_pdf = fname.lower().endswith(".pdf")
                        if is_pdf:
                            with st.spinner("Converting PDF pages to images…"):
                                pages = pdf_to_images(file_bytes, dpi=200, max_pages=10)
                            if not pages:
                                st.error("Could not extract pages from PDF.")
                                continue
                            st.caption(f"Extracted {len(pages)} page(s) from PDF")
                            with st.spinner(f"Analyzing {fname}…"):
                                result = analyze_pdf_pages(
                                    pages, discipline, detail_level, _api_key
                                )
                        else:
                            with st.spinner(f"Analyzing {fname}…"):
                                b64, mime = image_file_to_b64(file_bytes, fname)
                                result = analyze_image(
                                    b64, mime, discipline, detail_level, _api_key
                                )

                        saved = save_analysis(
                            user_id=user["id"],
                            filename=fname,
                            result=result,
                            file_size_kb=file_size_kb,
                            analysis_mode=discipline,
                            detail_level=detail_level,
                            workspace_id=workspace_id,
                        )
                        render_result(result, fname, saved.get("id"))

                    except Exception as e:
                        st.error(friendly_error(e))
                        retry_key = f"retry_{fname}"
                        if st.button("↩ Retry this file", key=retry_key):
                            st.rerun()

            # ── Refresh profile once after all files are done ──────────────────
            refresh_profile()
            profile = get_current_profile() or {}

    else:
        # ── Empty state ────────────────────────────────────────────────────────
        st.markdown("""
        <div class="empty-state">
            <div class="icon">⚙</div>
            <h3>Upload a drawing to get started</h3>
            <p>Supports mechanical, structural, electrical, architectural drawings</p>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HISTORY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 History":
    st.markdown("## Analysis History")

    with st.spinner("Loading history…"):
        analyses = get_analyses(user["id"], limit=100, workspace_id=workspace_id)

    if not analyses:
        st.markdown(
            '<div class="empty-state"><div class="icon">📋</div>'
            '<h3>No analyses yet</h3>'
            '<p>Analyze your first drawing to see it here.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        # ── Filters row ────────────────────────────────────────────────────────
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            search = st.text_input(
                "Search",
                placeholder="Part name, filename…",
                label_visibility="collapsed",
            )
        with col2:
            type_filter = st.selectbox(
                "Type",
                ["All Types", "Mechanical", "Structural",
                 "Electrical", "Architectural", "PCB", "Welding"],
                label_visibility="collapsed",
            )
        with col3:
            date_filter = st.selectbox(
                "Date range",
                ["All Time", "Today", "This Week", "This Month"],
                label_visibility="collapsed",
            )
        with col4:
            if limits.get("export"):
                csv_buf = io.StringIO()
                w = csv.writer(csv_buf)
                w.writerow([
                    "ID", "Filename", "Date", "Drawing Type",
                    "Part Name", "Material", "Complexity",
                    "Confidence", "Critical Flags", "Warnings",
                ])
                for a in analyses:
                    w.writerow([
                        a["id"], a["filename"], a["created_at"],
                        a.get("drawing_type"), a.get("part_name"),
                        a.get("material"), a.get("estimated_complexity"),
                        a.get("confidence_score"),
                        a.get("flag_critical_count", 0),
                        a.get("flag_warning_count", 0),
                    ])
                st.download_button(
                    "⬇ Export CSV",
                    csv_buf.getvalue(),
                    file_name=(f"drawingiq_history_"
                               f"{datetime.now().strftime('%Y%m%d')}.csv"),
                    mime="text/csv",
                    use_container_width=True,
                )
            else:
                if st.button("⬇ Export (Starter+)", use_container_width=True):
                    st.info("Upgrade to Starter or higher to export history.")

        # ── Filtering logic ────────────────────────────────────────────────────
        filtered = analyses
        if search:
            s = search.lower()
            filtered = [
                a for a in filtered
                if s in (a.get("filename") or "").lower()
                or s in (a.get("part_name") or "").lower()
            ]
        if type_filter != "All Types":
            filtered = [
                a for a in filtered
                if a.get("drawing_type") == type_filter
            ]
        if date_filter != "All Time":
            today = date.today()
            if date_filter == "Today":
                filtered = [
                    a for a in filtered
                    if str(a.get("created_at", ""))[:10] == str(today)
                ]
            elif date_filter == "This Week":
                from datetime import timedelta
                week_ago = today - timedelta(days=7)
                filtered = [
                    a for a in filtered
                    if str(a.get("created_at", ""))[:10] >= str(week_ago)
                ]
            elif date_filter == "This Month":
                prefix = today.strftime("%Y-%m")
                filtered = [
                    a for a in filtered
                    if str(a.get("created_at", "")).startswith(prefix)
                ]

        st.caption(f"Showing {len(filtered)} of {len(analyses)} analyses")
        st.markdown("---")

        # ── History rows with confirm-delete ───────────────────────────────────
        if "pending_delete" not in st.session_state:
            st.session_state["pending_delete"] = None

        for a in filtered:
            crit = a.get("flag_critical_count", 0)
            warn = a.get("flag_warning_count", 0)
            dt   = html_lib.escape(str(a.get("created_at", "")[:10]))
            aid  = a["id"]

            # Confirm-delete state
            if st.session_state["pending_delete"] == aid:
                st.markdown(
                    f'<div class="confirm-delete-row">'
                    f'⚠️ Delete <strong>{html_lib.escape(a.get("filename",""))}</strong>? '
                    f'This cannot be undone.</div>',
                    unsafe_allow_html=True,
                )
                cc1, cc2 = st.columns([1, 1])
                with cc1:
                    if st.button("✓ Yes, delete", key=f"conf_{aid}",
                                 type="primary", use_container_width=True):
                        delete_analysis(aid, user["id"])
                        st.session_state["pending_delete"] = None
                        st.rerun()
                with cc2:
                    if st.button("✗ Cancel", key=f"cancel_{aid}",
                                 use_container_width=True):
                        st.session_state["pending_delete"] = None
                        st.rerun()
                continue

            flag_badges = ""
            if crit:
                flag_badges += (
                    f'<span style="background:#fee2e2;color:#991b1b;font-size:0.72rem;'
                    f'font-weight:600;padding:2px 8px;border-radius:4px;margin-left:6px;">'
                    f'🔴 {crit} critical</span>'
                )
            if warn:
                flag_badges += (
                    f'<span style="background:#fef3c7;color:#92400e;font-size:0.72rem;'
                    f'font-weight:600;padding:2px 8px;border-radius:4px;margin-left:6px;">'
                    f'⚠ {warn} warning</span>'
                )

            card_col, btn_col = st.columns([6, 1])
            with card_col:
                st.markdown(f"""
                <div style="background:white;border:1px solid #dbeafe;border-radius:10px;
                            padding:0.85rem 1.1rem;box-shadow:0 1px 4px rgba(30,100,255,0.06);">
                    <div style="display:flex;align-items:center;gap:0.4rem;flex-wrap:wrap;">
                        <span style="font-weight:600;color:#0f172a;font-size:0.92rem;">
                            {html_lib.escape(str(a.get('filename','')))}
                        </span>
                        {flag_badges}
                        <span style="margin-left:auto;font-size:0.75rem;color:#9ca3af;">📅 {dt}</span>
                    </div>
                    <div style="font-size:0.78rem;color:#6b7280;margin-top:5px;display:flex;gap:1rem;flex-wrap:wrap;">
                        <span>📐 {html_lib.escape(str(a.get('drawing_type','—')))}</span>
                        <span>🔩 {html_lib.escape(str(a.get('part_name','—')))}</span>
                        <span>🧱 {html_lib.escape(str(a.get('material','—')))}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                if st.button("👁 View", key=f"view_{aid}", use_container_width=True):
                    st.session_state["viewing_analysis"] = aid
                    st.rerun()
                if st.button("🗑 Del", key=f"del_{aid}", use_container_width=True):
                    st.session_state["pending_delete"] = aid
                    st.rerun()
            st.markdown("<div style='margin-bottom:0.25rem'></div>", unsafe_allow_html=True)

        # ── Expanded view anchored at bottom ───────────────────────────────────
        if "viewing_analysis" in st.session_state:
            aid    = st.session_state["viewing_analysis"]
            # Ownership-checked fetch
            record = get_analysis_by_id(aid, user_id=user["id"])
            if record:
                st.markdown("---")
                st.markdown(f"### {html_lib.escape(str(record['filename']))}")
                if st.button("✕ Close", key="close_view"):
                    del st.session_state["viewing_analysis"]
                    st.rerun()
                render_result(record["result_json"], record["filename"], aid)
            else:
                st.warning("Analysis not found or you don't have permission to view it.")
                del st.session_state["viewing_analysis"]


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TEAM
# ══════════════════════════════════════════════════════════════════════════════
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
            ws_name = st.text_input("Workspace Name",
                                    placeholder="Acme Mfg – QA Team")
            if st.button("Create", type="primary"):
                if ws_name:
                    create_workspace(user["id"], ws_name)
                    st.success(f"Workspace '{ws_name}' created!")
                    st.rerun()

    if not workspaces:
        st.markdown(
            '<div class="empty-state"><div class="icon">👥</div>'
            '<h3>No workspaces yet</h3>'
            '<p>Create a workspace to collaborate with your team.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        for ws_entry in workspaces:
            ws_data = ws_entry.get("workspaces") or {}
            ws_id   = ws_data.get("id")
            ws_name = ws_data.get("name", "Unnamed")
            my_role = ws_entry.get("role", "member")

            with st.expander(f"🏢 {ws_name}  ({my_role})", expanded=True):
                members = get_workspace_members(ws_id)
                for m in members:
                    p        = m.get("profiles") or {}
                    name     = p.get("full_name") or p.get("email", "Unknown")
                    email    = p.get("email", "")
                    role     = m.get("role", "member")
                    initials = "".join([x[0].upper() for x in name.split()[:2]])
                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        st.markdown(f"""
                        <div class="team-member-row">
                            <div class="avatar">{html_lib.escape(initials)}</div>
                            <div style="flex:1">
                                <div style="font-weight:500;color:#0f172a;font-size:0.9rem;">
                                    {html_lib.escape(name)}
                                </div>
                                <div style="font-size:0.78rem;color:#6b7280;">
                                    {html_lib.escape(email)}
                                </div>
                            </div>
                            <span class="role-badge role-{html_lib.escape(role)}">
                                {html_lib.escape(role)}
                            </span>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_b:
                        uid = p.get("id")
                        if my_role in ("owner", "admin") and uid and uid != user["id"]:
                            if st.button("Remove", key=f"rm_{ws_id}_{uid}"):
                                remove_member(ws_id, uid)
                                st.rerun()

                if my_role in ("owner", "admin"):
                    st.markdown("---")
                    inv1, inv2, inv3 = st.columns([3, 1, 1])
                    with inv1:
                        inv_email = st.text_input(
                            "Invite by email",
                            key=f"inv_email_{ws_id}",
                            placeholder="engineer@company.com",
                            label_visibility="collapsed",
                        )
                    with inv2:
                        inv_role = st.selectbox(
                            "Role",
                            ["member", "admin", "viewer"],
                            key=f"inv_role_{ws_id}",
                            label_visibility="collapsed",
                        )
                    with inv3:
                        if st.button("Invite", key=f"invite_{ws_id}",
                                     type="primary"):
                            try:
                                invite_member(ws_id, user["id"],
                                              inv_email, inv_role)
                                st.success(f"Invited {inv_email}!")
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: BILLING
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💳 Billing":
    render_pricing_page(user["id"], profile.get("email", ""), plan)
    st.markdown("---")
    st.markdown("### Your Usage")
    stats = get_usage_stats(user["id"])
    col1, col2, col3 = st.columns(3)
    col1.metric("This Month",   stats.get("analyses_this_month", 0))
    col2.metric("All Time",     stats.get("analyses_total", 0))
    limit_val = stats.get("limit_this_month", 5)
    col3.metric("Limit / Month", limit_val if limit_val < 99999 else "∞")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ACCOUNT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙ Account":
    st.markdown("## Account Settings")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("### Profile")
        new_name    = st.text_input("Full Name", value=profile.get("full_name") or "")
        new_company = st.text_input("Company",   value=profile.get("company") or "")
        st.text_input("Email", value=profile.get("email", ""), disabled=True)
        if st.button("Save Profile", type="primary"):
            update_profile(user["id"], {"full_name": new_name, "company": new_company})
            refresh_profile()
            st.success("Profile updated!")

    with col2:
        st.markdown("### API Keys")
        st.info("🔒 API keys are managed securely via Streamlit Secrets.")
        st.caption("API keys are never stored in our database.")

        st.markdown("### Current Plan")
        st.markdown(f"**Plan:** {plan.title()}")
        lim = get_plan_limits(plan)
        st.markdown(
            f"**Analyses:** {profile.get('analyses_this_month',0)} / "
            f"{lim['analyses_per_month']} this month"
        )
        st.markdown(f"**Batch size:** {lim['batch_size']} drawings")
        st.markdown(f"**PDF support:** {'✓' if lim['pdf'] else '✗'}")
        st.markdown(f"**Team workspaces:** {'✓' if lim['team'] else '✗'}")

    st.markdown("---")
    st.markdown("### Analysis Preferences")
    pref_disc   = st.selectbox(
        "Default Discipline",
        ["Auto-Detect", "Mechanical / Machining", "Structural / Civil",
         "Electrical / Schematic", "Architectural",
         "PCB / Electronics", "Welding / Fabrication"],
        index=0,
        key="acct_disc",
    )
    pref_detail = st.select_slider(
        "Default Detail Level",
        options=["Quick Scan", "Standard", "Deep Review"],
        value="Standard",
        key="acct_detail",
    )
    if st.button("Save Preferences"):
        st.session_state["pref_discipline"] = pref_disc
        st.session_state["pref_detail"]     = pref_detail
        st.success("Preferences saved for this session!")

    st.markdown("---")
    st.markdown("### Danger Zone")
    with st.expander("Delete Account"):
        st.error(
            "This will permanently delete your account and all analyses. "
            "This cannot be undone."
        )
        confirm = st.text_input("Type DELETE to confirm")
        if st.button("Delete My Account", type="primary"):
            if confirm == "DELETE":
                st.warning(
                    "Please contact support@drawingiq.com to delete your account."
                )
            else:
                st.error("Type DELETE to confirm.")