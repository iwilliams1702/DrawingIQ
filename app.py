# Copyright (c) 2026 Isaiah Williams / DrawingIQ
# All rights reserved. Unauthorized copying, modification,
# or distribution of this software is strictly prohibited.
import streamlit as st
import os
import html as html_lib

for key in ["OPENAI_API_KEY","SUPABASE_URL","SUPABASE_ANON_KEY","APP_URL","SUPABASE_SERVICE_KEY"]:
    if key in st.secrets:
        os.environ[key] = st.secrets[key]

import json, io, csv, logging
from datetime import datetime, date, timedelta

_api_key = os.getenv("OPENAI_API_KEY","")
if not _api_key:
    st.error("OpenAI API key not configured. Add OPENAI_API_KEY to Streamlit secrets.")
    st.stop()

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="DrawingIQ", page_icon="⚙", layout="wide",
                   initial_sidebar_state="expanded", menu_items={})

from auth import (init_session, is_logged_in, get_current_user,
                  get_current_profile, logout, render_auth_page, render_landing_page, refresh_profile)
from database import (
    get_profile, save_analysis, get_analyses, get_analysis_by_id,
    delete_analysis, get_plan_limits, can_analyze,
    create_workspace, get_user_workspaces, get_workspace_members,
    invite_member, remove_member, get_usage_stats, PLAN_LIMITS, update_profile,
    save_material, get_materials, delete_material,
    get_effective_limits, is_in_trial,
    save_machine, get_machines, delete_machine,
    save_quote, get_quotes, get_quote_by_token, update_quote_status,
    save_job_actual, get_job_actuals, find_similar_parts,
    save_fai, get_fai_reports,
    save_job_to_queue, get_job_queue, update_job_status, delete_job_from_queue,
)
from billing import render_pricing_page, render_usage_bar, PLANS, enforce_free_limits
from analyzer import analyze_image, analyze_pdf_pages, estimate_quote
from pdf_utils import pdf_to_images, image_file_to_b64, get_pdf_page_count

init_session()

# CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
#MainMenu,footer,[data-testid="stToolbar"],.stDeployButton,
button[title="View app in Streamlit Community Cloud"]{display:none!important;}
header[data-testid="stHeader"]{background:transparent;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#020d1f 0%,#030f24 100%);border-right:1px solid rgba(30,100,255,0.15);}
[data-testid="stSidebar"] *{color:#7aa2d4!important;}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:#e2e8f0!important;}
.main{background:#f0f4ff;}
.app-header{background:linear-gradient(90deg,#020d1f,#030f24);color:#e2e8f0;padding:1rem 2rem;margin:-1rem -1rem 1.5rem -1rem;display:flex;align-items:center;justify-content:space-between;border-bottom:2px solid #1d4ed8;box-shadow:0 2px 20px rgba(0,0,0,0.3);}
.app-title{font-size:1.4rem;font-weight:800;letter-spacing:-0.02em;color:white;}
.app-title span{color:#3b82f6;}
.app-subtitle{font-size:0.7rem;color:#4a6fa5;letter-spacing:0.12em;text-transform:uppercase;}
.plan-badge{font-size:0.68rem;font-weight:700;padding:3px 9px;border-radius:4px;text-transform:uppercase;}
.badge-free{background:rgba(30,100,255,0.15);color:#60a5fa;border:1px solid rgba(30,100,255,0.3);}
.badge-starter{background:#bfdbfe;color:#1e40af;}
.badge-pro{background:#fde68a;color:#92400e;}
.badge-enterprise{background:#ddd6fe;color:#5b21b6;}
.logo-box{width:38px;height:38px;background:linear-gradient(135deg,#1d4ed8,#2563eb);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;box-shadow:0 0 12px rgba(37,99,235,0.4);}
.metric-strip{display:flex;gap:0.6rem;margin:1rem 0;flex-wrap:wrap;}
.metric-box{background:white;border:1px solid #dbeafe;border-radius:8px;padding:0.75rem 1rem;flex:1;min-width:95px;box-shadow:0 1px 4px rgba(30,100,255,0.05);}
.metric-box .label{font-size:0.66rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;}
.metric-box .value{font-size:1rem;font-weight:600;color:#0f172a;font-family:'IBM Plex Mono',monospace;margin-top:2px;}
.metric-box .value.small{font-size:0.85rem;}
.flag-item{border-left:3px solid #2563eb;padding:0.6rem 0.9rem;margin:0.35rem 0;border-radius:0 6px 6px 0;font-size:0.87rem;}
.flag-critical{border-left-color:#dc2626;background:#fff5f5;color:#2d0e0e;}
.flag-warning{border-left-color:#d97706;background:#fffbee;color:#3d2e00;}
.flag-info{border-left-color:#2563eb;background:#eff6ff;color:#1e3a5f;}
.flag-evidence{font-size:0.76rem;color:#9ca3af;margin-top:3px;font-family:'IBM Plex Mono',monospace;background:#f9fafb;padding:2px 5px;border-radius:3px;}
.dim-table{width:100%;border-collapse:collapse;font-size:0.84rem;}
.dim-table th{background:#eff6ff;text-align:left;padding:7px 10px;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;color:#1d4ed8;}
.dim-table td{padding:6px 10px;border-bottom:1px solid #dbeafe;color:#374151;font-family:'IBM Plex Mono',monospace;font-size:0.8rem;}
.dim-table .critical-row td{background:#fff8f8;}
.drawing-type-tag{display:inline-block;background:linear-gradient(135deg,#1d4ed8,#2563eb);color:white;font-size:0.75rem;font-weight:700;padding:4px 12px;border-radius:4px;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.75rem;}
.result-card{background:white;border:1px solid #dbeafe;border-radius:10px;padding:1.25rem;margin:0.75rem 0;box-shadow:0 2px 8px rgba(30,100,255,0.05);}
.quote-total{background:linear-gradient(135deg,#1d4ed8,#2563eb);color:white;border-radius:10px;padding:1.25rem;text-align:center;margin:1rem 0;box-shadow:0 4px 15px rgba(37,99,235,0.3);}
.quote-total .q-price{font-size:2.5rem;font-weight:800;font-family:'IBM Plex Mono',monospace;}
.quote-total .q-label{font-size:0.8rem;opacity:0.8;text-transform:uppercase;letter-spacing:0.1em;}
.quote-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f1f5f9;font-size:0.87rem;}
.quote-row:last-child{border-bottom:none;}
.quote-row .qr-label{color:#6b7280;}
.quote-row .qr-value{font-family:'IBM Plex Mono',monospace;font-weight:500;color:#0f172a;}
.dash-card{background:white;border:1px solid #dbeafe;border-radius:10px;padding:1.25rem;box-shadow:0 2px 8px rgba(30,100,255,0.05);margin-bottom:1rem;}
.dash-card h4{color:#1d4ed8;margin:0 0 0.75rem;font-size:0.88rem;text-transform:uppercase;letter-spacing:0.05em;}
.checklist-item{display:flex;align-items:flex-start;gap:0.6rem;padding:0.5rem 0;border-bottom:1px solid #f1f5f9;font-size:0.87rem;}
.checklist-item:last-child{border-bottom:none;}
.history-card{background:white;border:1px solid #dbeafe;border-radius:10px;padding:0.85rem 1.1rem;box-shadow:0 1px 4px rgba(30,100,255,0.06);margin-bottom:0.1rem;}
.drop-zone-hint{border:2px dashed #93c5fd;border-radius:12px;background:#eff6ff;padding:2rem 2rem 1rem;text-align:center;margin-bottom:0.5rem;}
.drop-zone-hint h3{color:#1d4ed8;font-weight:700;margin:0.4rem 0 0.2rem;}
.drop-zone-hint p{color:#60a5fa;font-size:0.83rem;margin:0;}
.team-member-row{background:white;border:1px solid #dbeafe;border-radius:8px;padding:0.7rem 1rem;margin:0.3rem 0;display:flex;align-items:center;gap:1rem;}
.avatar{width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#1d4ed8,#2563eb);color:white;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.78rem;flex-shrink:0;}
.role-badge{font-size:0.7rem;font-weight:600;padding:2px 8px;border-radius:10px;}
.role-owner{background:#fef3c7;color:#92400e;}
.role-admin{background:#e0f2fe;color:#075985;}
.role-member{background:#eff6ff;color:#1d4ed8;}
.role-viewer{background:#ede9fe;color:#5b21b6;}
.upgrade-banner{background:linear-gradient(135deg,#1d4ed8,#2563eb);color:white;border-radius:10px;padding:1rem 1.25rem;margin:0.5rem 0;text-align:center;box-shadow:0 4px 15px rgba(37,99,235,0.3);}
.upgrade-banner strong{display:block;margin-bottom:0.25rem;}
.empty-state{text-align:center;padding:3rem 2rem;color:#9ca3af;}
.empty-state .icon{font-size:2.5rem;}
.empty-state h3{color:#374151;margin:0.75rem 0 0.4rem;font-weight:600;}
.confirm-delete-row{background:#fff5f5;border:1px solid #fca5a5;border-radius:8px;padding:0.6rem 1rem;margin:0.2rem 0;font-size:0.85rem;color:#7f1d1d;}
button[kind="primary"]{background:linear-gradient(135deg,#1d4ed8,#2563eb)!important;border:none!important;}
</style>
""", unsafe_allow_html=True)

if not is_logged_in():
    render_landing_page()
    st.stop()

user    = get_current_user()
profile = get_current_profile() or {}
if not profile:
    refresh_profile()
    profile = get_current_profile() or {}

plan   = profile.get("plan","free")
# Dev account override - always give full access to the owner
_owner_email = "isaiah.williams2002@outlook.com"
if profile.get("email","") == _owner_email and plan == "free":
    plan = "pro"
    profile["plan"] = "pro"
limits = get_effective_limits(profile)
user_name = (user.get("full_name") or profile.get("full_name") or
             profile.get("email","") or user.get("email","")).strip() or "User"
user_initials = "".join([p[0].upper() for p in user_name.split()[:2]])
plan_badge = f'<span class="plan-badge badge-{plan}">{html_lib.escape(plan.upper())}</span>'

st.markdown(f"""
<div class="app-header">
  <div style="display:flex;align-items:center;gap:1rem;">
    <div class="logo-box">⚙</div>
    <div>
      <div class="app-title">Drawing<span>IQ</span></div>
      <div class="app-subtitle">Machine Shop Intelligence Platform</div>
    </div>
    {plan_badge}
  </div>
  <div style="display:flex;align-items:center;gap:0.75rem;font-size:0.85rem;">
    <div style="background:linear-gradient(135deg,#1d4ed8,#2563eb);border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-weight:700;color:white;font-size:0.78rem;">
      {html_lib.escape(user_initials)}
    </div>
    <span style="color:#7aa2d4;">{html_lib.escape(user_name)}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Onboarding for new users ─────────────────────────────────────────────────
_analyses_total = profile.get("analyses_total", 0)
_has_machines   = False
_has_materials  = False
try:
    _has_machines  = len(get_machines(user["id"])) > 0
    _has_materials = len(get_materials(user["id"])) > 0
except Exception:
    pass

_onboarding_done = st.session_state.get("onboarding_dismissed", False)
_show_onboarding = (not _onboarding_done and _analyses_total == 0
                    and not _has_machines and not _has_materials)

if _show_onboarding:
    with st.expander("👋 Welcome to DrawingIQ — Get started in 4 steps", expanded=True):
        oc1,oc2,oc3,oc4 = st.columns(4)
        steps = [
            ("⚙","Add your machines","Go to Shop Setup → Machine Profiles. Add your CNC machines and their tolerance capabilities.",_has_machines),
            ("🧱","Add your materials","Go to Shop Setup → Material Library. Add your common materials and prices for auto-quoting.",_has_materials),
            ("📐","Analyze your first drawing","Go to Analyze, upload any engineering drawing, and run your first analysis.",_analyses_total>0),
            ("💰","Generate your first quote","After analyzing a drawing, go to the Quote tab and run a cost estimate.",False),
        ]
        for col,(icon,title,desc,done) in zip([oc1,oc2,oc3,oc4], steps):
            with col:
                status_color = "#16a34a" if done else "#2563eb"
                status_icon  = "✅" if done else "○"
                st.markdown(f"""
                <div style='background:{"#f0fdf4" if done else "white"};border:1px solid {"#86efac" if done else "#dbeafe"};
                            border-radius:10px;padding:1rem;text-align:center;height:150px;'>
                    <div style='font-size:1.5rem;'>{icon}</div>
                    <div style='font-size:0.82rem;font-weight:600;color:#0f172a;margin:6px 0 4px;'>{title}</div>
                    <div style='font-size:0.75rem;color:#6b7280;line-height:1.4;'>{desc}</div>
                    <div style='margin-top:6px;font-size:0.85rem;color:{status_color};font-weight:700;'>{status_icon}</div>
                </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("✕ Dismiss — I know what I'm doing", use_container_width=True):
            st.session_state["onboarding_dismissed"] = True
            st.rerun()

with st.sidebar:
    st.markdown("### ⚙ DrawingIQ")
    st.markdown("---")
    used = profile.get("analyses_this_month",0)
    cap  = limits["analyses_per_month"]
    render_usage_bar(used, cap, plan)
    if plan == "free" and used >= 3:
        st.markdown('<div class="upgrade-banner"><strong>Upgrade for more analyses</strong>Starter: 50/mo · Pro: 300/mo</div>', unsafe_allow_html=True)
    st.markdown("---")
    workspaces   = get_user_workspaces(user["id"])
    workspace_id = None
    if workspaces and limits.get("team"):
        ws_options = {"Personal": None}
        for ws in workspaces:
            wsd = ws.get("workspaces") or {}
            ws_options[wsd.get("name","Unnamed")] = wsd.get("id")
        workspace_id = ws_options[st.selectbox("Workspace", list(ws_options.keys()))]
        st.markdown("---")
    NAV = ["📤 Analyze","📊 Dashboard","📋 History","🔍 Compare","✅ Review Checklist","💰 Quotes","🔬 FAI Reports","📈 Job Tracker","🔧 Shop Setup","👥 Team","💳 Billing","⚙ Account","📜 Terms & Privacy"]
    _forced    = st.session_state.pop("force_page", None)
    _nav_index = NAV.index(_forced) if _forced in NAV else 0
    page = st.radio("Navigate", NAV, index=_nav_index, label_visibility="collapsed")
    st.markdown("---")
    # Trial countdown
    _created = profile.get("created_at","")
    if _created and plan == "free":
        try:
            from datetime import timezone as _tz
            _cdt   = datetime.fromisoformat(_created.replace("Z","+00:00"))
            _dleft = max(0, 30 - (datetime.now(_tz.utc) - _cdt).days)
            _bpct  = int((30-_dleft)/30*100)
            _bcol  = "#dc2626" if _dleft<=5 else "#d97706" if _dleft<=10 else "#3b82f6"
            st.markdown(
                f"<div style='font-size:0.78rem;color:#7aa2d4;margin-bottom:3px;'>"
                f"Free trial: <strong style='color:#e2e8f0;'>{_dleft} days left</strong></div>"
                f"<div style='background:#1e3a5f;border-radius:4px;height:4px;margin-bottom:6px;'>"
                f"<div style='background:{_bcol};border-radius:4px;height:4px;width:{_bpct}%;'>"
                f"</div></div>",
                unsafe_allow_html=True
            )
            if _dleft <= 7:
                st.markdown(
                    "<div style='background:#dc2626;color:white;border-radius:6px;"
                    "padding:6px 10px;font-size:0.78rem;text-align:center;margin-top:4px;'>"
                    "<strong>Trial ending soon!</strong> Upgrade to keep access.</div>",
                    unsafe_allow_html=True
                )
        except Exception:
            pass
    st.markdown("---")
    if st.button("Sign Out", use_container_width=True):
        logout()

DISCIPLINES  = ["Auto-Detect","Mechanical / Machining","Structural / Civil","Electrical / Schematic","Architectural","PCB / Electronics","Welding / Fabrication"]
DETAIL_LEVELS = ["Quick Scan","Standard","Deep Review"]
MAX_FILE_MB   = 20

if "pref_discipline" not in st.session_state: st.session_state["pref_discipline"] = "Mechanical / Machining"
if "pref_detail"     not in st.session_state: st.session_state["pref_detail"]     = "Standard"
if "pending_delete"  not in st.session_state: st.session_state["pending_delete"]  = None

def friendly_error(exc):
    msg = str(exc).lower()
    if "rate_limit" in msg or "429" in msg: return "AI service is busy. Wait 30 seconds and retry."
    if "timeout"    in msg: return "Request timed out. Check connection and retry."
    if "json"       in msg or "decode" in msg: return "AI returned unexpected output. Try Deep Review."
    if "api_key"    in msg or "auth"   in msg: return "API authentication failed. Contact administrator."
    logger.error("Analysis error: %s", exc, exc_info=True)
    return "Analysis failed. Please retry or contact support."

def esc(v):
    return html_lib.escape(str(v) if v is not None else "Unknown")

def build_checklist(result):
    checks = []
    dims  = result.get("dimensions", [])
    flags = result.get("flags", [])
    def add(status, label, note=""):
        checks.append({"status": status, "label": label, "note": note})
    tb = result.get("title_block_found", False)
    add("pass" if tb else "fail","Title block found","No title block detected." if not tb else "")
    pn = result.get("part_number")
    add("pass" if pn else "warn","Part number present","No part number — assign before quoting." if not pn else str(pn))
    rev = result.get("revision")
    add("pass" if rev else "warn","Revision level present","No revision found." if not rev else str(rev))
    mat = result.get("material")
    add("pass" if mat else "fail","Material specified","Must be called out before machining." if not mat else str(mat))
    spec = result.get("material_spec")
    add("pass" if spec else "warn","Material spec/grade","e.g. ASTM A36, 6061-T6 for traceability." if not spec else str(spec))
    sf = result.get("surface_finish")
    add("pass" if sf else "warn","Surface finish specified","No surface finish callout." if not sf else str(sf))
    add("pass" if dims else "fail","Dimensions extracted",f"{len(dims)} found." if dims else "None readable.")
    crits = [d for d in dims if d.get("is_critical")]
    add("warn" if crits else "pass",f"{len(crits)} critical dimension(s)","Review carefully before setup." if crits else "")
    tsr = result.get("tolerance_stack_risk","Unknown")
    add("fail" if tsr=="High" else "warn" if tsr=="Medium" else "pass",f"Tolerance stack risk: {tsr}","High risk — verify assembly clearances." if tsr=="High" else "")
    crit_flags = [f for f in flags if f.get("severity")=="critical"]
    add("fail" if crit_flags else "pass",f"{len(crit_flags)} critical flag(s)","; ".join(f.get("category","") for f in crit_flags) if crit_flags else "None.")
    gdt = result.get("gdt_callouts",[])
    add("pass" if gdt else "warn","GD&T callouts",f"{len(gdt)} found." if gdt else "None — may be OK for simple parts.")
    stds = result.get("standards_referenced",[])
    add("pass" if stds else "warn","Standards referenced",", ".join(stds) if stds else "None called out.")
    conf = result.get("confidence_score",0)
    add("fail" if conf<50 else "warn" if conf<75 else "pass",f"Drawing readability: {conf}%","Upload higher-res scan." if conf<75 else "")
    return checks

def build_checklist_with_machines(result, machines):
    checks = build_checklist(result)
    if machines:
        cap_risks = check_machine_capability(result.get("dimensions",[]), machines)
        if cap_risks:
            checks.append({"status":"fail","label":f"{len(cap_risks)} dimension(s) exceed machine capability","note":"; ".join(f'{r["feature"]} ±{r["tolerance"]}' for r in cap_risks[:3])})
        else:
            checks.append({"status":"pass","label":"All tolerances within machine capability","note":""})
    return checks

def render_result(result, filename, analysis_id=None):
    flags    = result.get("flags",[])
    critical = [f for f in flags if f.get("severity")=="critical"]
    warnings = [f for f in flags if f.get("severity")=="warning"]
    info_f   = [f for f in flags if f.get("severity")=="info"]
    dims     = result.get("dimensions",[])
    conf     = result.get("confidence_score",0)
    clarity  = result.get("drawing_clarity","Unknown")
    clarity_color = {"Clear":"#16a34a","Partially Legible":"#d97706","Difficult to Read":"#dc2626","Unclear":"#dc2626"}.get(clarity,"#6b7280")
    crit_color = "#dc2626" if critical else "#16a34a"

    st.markdown(f'<span class="drawing-type-tag">{esc(result.get("drawing_type","Unknown"))}</span>', unsafe_allow_html=True)
    if conf < 60:
        st.warning(f"⚠️ Low confidence ({conf}%) — upload a cleaner scan for full accuracy.")
    if critical:
        st.error(f"🔴 {len(critical)} critical issue(s) require attention before machining.")

    st.markdown(f"""
    <div class="metric-strip">
      <div class="metric-box"><div class="label">Part</div><div class="value small">{esc(result.get("part_name"))}</div></div>
      <div class="metric-box"><div class="label">P/N</div><div class="value small">{esc(result.get("part_number"))}</div></div>
      <div class="metric-box"><div class="label">Rev</div><div class="value small">{esc(result.get("revision"))}</div></div>
      <div class="metric-box"><div class="label">Material</div><div class="value small">{esc(result.get("material"))}</div></div>
      <div class="metric-box"><div class="label">Spec</div><div class="value small">{esc(result.get("material_spec"))}</div></div>
      <div class="metric-box"><div class="label">Units</div><div class="value small">{esc(result.get("units"))}</div></div>
      <div class="metric-box"><div class="label">Scale</div><div class="value small">{esc(result.get("scale"))}</div></div>
      <div class="metric-box"><div class="label">Complexity</div><div class="value small">{esc(result.get("estimated_complexity"))}</div></div>
      <div class="metric-box"><div class="label">Setups</div><div class="value small">{esc(result.get("setup_count_estimate"))}</div></div>
      <div class="metric-box"><div class="label">Confidence</div><div class="value">{conf}%</div></div>
      <div class="metric-box"><div class="label">Clarity</div><div class="value small" style="color:{clarity_color}">{esc(clarity)}</div></div>
      <div class="metric-box"><div class="label">Tol.Stack</div><div class="value small">{esc(result.get("tolerance_stack_risk"))}</div></div>
      <div class="metric-box"><div class="label">Flags</div><div class="value small" style="color:{crit_color}">{len(critical)}🔴 {len(warnings)}⚠️ {len(info_f)}ℹ️</div></div>
    </div>""", unsafe_allow_html=True)

    tabs = st.tabs(["🚩 Flags","📐 Dimensions","🔧 Machinist Notes","📋 Specs","✅ Checklist","💰 Quote","📝 Raw Notes","✏️ Verify & Schedule","🖨 Print","⬇ Export"])
    t_flags,t_dims,t_notes,t_specs,t_checklist,t_quote,t_rawnotes,t_verify,t_print,t_export = tabs

    with t_flags:
        if not flags: st.success("✓ No flags raised — drawing looks clean.")
        for severity,label,cls in [("critical","🔴 Critical","flag-critical"),("warning","⚠️ Warnings","flag-warning"),("info","ℹ️ Info","flag-info")]:
            subset = [f for f in flags if f.get("severity")==severity]
            if not subset: continue
            st.markdown(f"**{label}**")
            for f in subset:
                ev = f.get("evidence","")
                ev_html = f'<div class="flag-evidence">Evidence: {esc(ev)}</div>' if ev else ""
                st.markdown(f'<div class="flag-item {cls}"><strong>{esc(f.get("category",""))}</strong>: {esc(f.get("description",""))}<br><span style="color:#6b7280;font-size:0.82rem;">→ {esc(f.get("recommendation",""))}</span>{ev_html}</div>', unsafe_allow_html=True)
        concerns = result.get("manufacturing_concerns",[])
        if concerns:
            st.markdown("---\n**Manufacturing Concerns**")
            for c in concerns: st.markdown(f"• {c}")

    with t_dims:
        if dims:
            rows = ""
            for d in dims:
                row_cls = "critical-row" if d.get("is_critical") else ""
                tol = esc(d.get("tolerance")) if d.get("tolerance") else "—"
                est = ' <span style="font-size:0.7rem;color:#9ca3af;">~est</span>' if d.get("is_estimated") else ""
                rows += f'<tr class="{row_cls}"><td>{esc(d.get("feature",""))}</td><td>{esc(d.get("value",""))}{est}</td><td>{tol}</td><td>{esc(d.get("unit",""))}</td><td>{esc(d.get("location_hint",""))}</td><td>{"🔴" if d.get("is_critical") else ""}</td></tr>'
            st.markdown(f'<table class="dim-table"><thead><tr><th>Feature</th><th>Value</th><th>Tolerance</th><th>Unit</th><th>View/Location</th><th></th></tr></thead><tbody>{rows}</tbody></table>', unsafe_allow_html=True)
        else:
            st.info("No dimensions extracted — try Deep Review or a cleaner scan.")
        gdt = result.get("gdt_callouts",[])
        if gdt:
            st.markdown("---\n**GD&T Callouts**")
            for g in gdt:
                dat = f' — Datum **{g.get("datum")}**' if g.get("datum") else ""
                est = " *(estimated)*" if g.get("is_estimated") else ""
                st.markdown(f'`{esc(g.get("symbol",""))}` **{esc(g.get("feature",""))}**: {esc(g.get("value",""))}{dat}{est}')

    with t_notes:
        note = result.get("machinist_notes","")
        if note:
            st.markdown(f'<div class="result-card"><p style="line-height:2;color:#1e293b;font-size:0.95rem;">{esc(note)}</p></div>', unsafe_allow_html=True)
        procs = result.get("recommended_processes",[])
        if procs:
            st.markdown("**Recommended Processes**")
            cols = st.columns(min(len(procs),4))
            for i,p in enumerate(procs):
                cols[i%len(cols)].markdown(f'<div style="background:#eff6ff;border-radius:6px;padding:0.5rem 0.8rem;font-size:0.82rem;text-align:center;font-weight:500;color:#1d4ed8;">{esc(p)}</div>', unsafe_allow_html=True)
        stds = result.get("standards_referenced",[])
        if stds: st.markdown("**Standards:** " + " · ".join(f"`{s}`" for s in stds))
        reason = result.get("complexity_reasoning","")
        if reason: st.markdown(f"**Complexity Reasoning:** {reason}")

    with t_specs:
        fields = [("Part Name","part_name"),("Part Number","part_number"),("Revision","revision"),("Scale","scale"),("Sheet","sheet_info"),("Units","units"),("Material","material"),("Material Spec","material_spec"),("Surface Finish","surface_finish"),("Heat Treatment","heat_treatment"),("Weight Est.","weight_estimate"),("Setups Est.","setup_count_estimate"),("Tol. Stack Risk","tolerance_stack_risk"),("Drawing Clarity","drawing_clarity"),("Title Block","title_block_found")]
        rows = "".join(f'<tr><td style="color:#6b7280;font-size:0.82rem;padding:6px 10px;">{label}</td><td style="font-family:IBM Plex Mono,monospace;font-size:0.82rem;padding:6px 10px;">{esc(result.get(key))}</td></tr>' for label,key in fields)
        st.markdown(f'<table class="dim-table"><tbody>{rows}</tbody></table>', unsafe_allow_html=True)
        with st.expander("Raw JSON"): st.json(result)

    with t_checklist:
        st.markdown("### ✅ Pre-Machining Readiness Checklist")
        checks = build_checklist(result)
        passed = sum(1 for c in checks if c["status"]=="pass")
        failed = sum(1 for c in checks if c["status"]=="fail")
        warned = sum(1 for c in checks if c["status"]=="warn")
        sc1,sc2,sc3 = st.columns(3)
        sc1.metric("Passed",passed); sc2.metric("Warnings",warned); sc3.metric("Failed",failed)
        if failed==0 and warned==0: st.success("🟢 Ready to machine.")
        elif failed==0: st.warning(f"🟡 {warned} item(s) to review.")
        else: st.error(f"🔴 {failed} item(s) must be resolved.")
        st.markdown("---")
        icons = {"pass":"✅","fail":"❌","warn":"⚠️"}
        for c in checks:
            note = f' <span style="color:#9ca3af;font-size:0.8rem;">— {esc(c["note"])}</span>' if c["note"] else ""
            st.markdown(f'<div class="checklist-item"><span>{icons[c["status"]]}</span><span><strong>{esc(c["label"])}</strong>{note}</span></div>', unsafe_allow_html=True)
        cl_txt = "\n".join(f'[{"PASS" if c["status"]=="pass" else "FAIL" if c["status"]=="fail" else "WARN"}] {c["label"]}' + (f' — {c["note"]}' if c["note"] else "") for c in checks)
        st.download_button("⬇ Download Checklist",f'DRAWINGIQ PRE-MACHINING CHECKLIST\nPart: {result.get("part_name","Unknown")} | File: {filename} | {datetime.now().strftime("%Y-%m-%d %H:%M")}\n{"="*60}\n{cl_txt}',file_name=f'{filename.rsplit(".",1)[0]}_checklist.txt',mime="text/plain",use_container_width=True)

    with t_quote:
        if not limits.get("quote", False):
            st.markdown('<div style="background:linear-gradient(135deg,#1d4ed8,#2563eb);color:white;border-radius:10px;padding:2rem;text-align:center;margin:1rem 0;"><div style="font-size:1.5rem;margin-bottom:0.5rem;">💰</div><div style="font-size:1.1rem;font-weight:700;margin-bottom:0.5rem;">Quote Engine — Starter Plan &amp; Above</div><div style="opacity:0.85;font-size:0.88rem;margin-bottom:1rem;">Generate instant job cost estimates, send customer approval links, and download professional quotes. Starting at $50/month.</div></div>', unsafe_allow_html=True)
            if st.button("🚀 Upgrade to Starter — $50/month", type="primary", use_container_width=True, key=f"upg_q_{analysis_id}"):
                st.session_state["force_page"] = "💳 Billing"; st.rerun()
        else:
            st.markdown("### 💰 Job Cost Estimator")
            st.caption("Enter your shop rates.")
            qr1,qr2,qr3 = st.columns(3)
            with qr1:
                machine_rate = st.number_input("Machine Rate ($/hr)",0.0,value=85.0,step=5.0,key=f"qmr_{analysis_id}")
                labor_rate   = st.number_input("Labor Rate ($/hr)",0.0,value=65.0,step=5.0,key=f"qlr_{analysis_id}")
                setup_cost   = st.number_input("Fixed Setup Cost ($)",0.0,value=50.0,step=10.0,key=f"qsc_{analysis_id}")
            with qr2:
                mat_cost_kg  = st.number_input("Material Cost ($/kg)",0.0,value=5.0,step=0.5,key=f"qmc_{analysis_id}")
                mat_density  = st.number_input("Material Density (kg/m³)",100.0,value=2700.0,step=100.0,key=f"qmd_{analysis_id}",help="Al=2700 · Steel=7850 · SS=8000 · Ti=4500")
                quantity     = st.number_input("Quantity",1,value=1,step=1,key=f"qqty_{analysis_id}")
            with qr3:
                overhead_pct = st.number_input("Overhead (%)",0.0,value=15.0,step=1.0,key=f"qoh_{analysis_id}")
                profit_pct   = st.number_input("Profit Margin (%)",0.0,value=20.0,step=1.0,key=f"qpm_{analysis_id}")
                rush_mult    = st.number_input("Rush Multiplier",1.0,value=1.0,step=0.1,key=f"qrm_{analysis_id}",help="1.0=standard · 1.5=rush · 2.0=emergency")
            qi1,qi2 = st.columns(2)
            with qi1:
                cust_name  = st.text_input("Customer Name",placeholder="Acme Corp",key=f"qcn_{analysis_id}")
                cust_email = st.text_input("Customer Email",placeholder="buyer@acme.com",key=f"qce_{analysis_id}")
            with qi2:
                quote_num  = st.text_input("Quote Number",placeholder="Q-2026-001",key=f"qqn_{analysis_id}")
                due_date   = st.text_input("Delivery Date",placeholder="2026-06-15",key=f"qdd_{analysis_id}")
            if st.button("⚙ Calculate Estimate",type="primary",key=f"qcalc_{analysis_id}",use_container_width=True):
                shop_rates = {"machine_rate_per_hr":machine_rate,"labor_rate_per_hr":labor_rate,"material_cost_per_kg":mat_cost_kg,"material_density_kg_m3":mat_density,"overhead_pct":overhead_pct,"profit_margin_pct":profit_pct,"setup_cost":setup_cost,"quantity":int(quantity)}
                q = estimate_quote(result,shop_rates)
                if rush_mult > 1.0:
                    q["total_job_cost"] = round(q["total_job_cost"]*rush_mult,2)
                    q["price_per_part"] = round(q["price_per_part"]*rush_mult,2)
                st.session_state[f"quote_{analysis_id}"]      = q
                st.session_state[f"quote_meta_{analysis_id}"] = {"customer_name":cust_name,"customer_email":cust_email,"quote_number":quote_num,"due_date":due_date}
            if f"quote_{analysis_id}" in st.session_state:
                q    = st.session_state[f"quote_{analysis_id}"]
                meta = st.session_state.get(f"quote_meta_{analysis_id}",{})
                st.markdown(f'<div class="quote-total"><div class="q-label">Price Per Part</div><div class="q-price">${q["price_per_part"]:,.2f}</div><div style="margin-top:0.5rem;opacity:0.8;font-size:0.85rem;">Total Job ({q["quantity"]} pcs): <strong>${q["total_job_cost"]:,.2f}</strong></div></div>', unsafe_allow_html=True)
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                for lbl,val,note in [("Machine Cost",f'${q["machine_cost"]:,.2f}',f'{q["machine_hours_per_part"]} hr/part'),("Labor Cost",f'${q["labor_cost"]:,.2f}',f'{q["labor_hours_per_part"]} hr/part'),("Material Cost",f'${q["material_cost"]:,.2f}',q["material_note"]),("Setup Cost",f'${q["setup_cost"]:,.2f}',""),("Overhead",f'${q["overhead_amount"]:,.2f}',""),("Profit",f'${q["profit_amount"]:,.2f}',"")]:
                    note_html = f' <span style="color:#9ca3af;font-size:0.78rem;">{esc(note)}</span>' if note else ""
                    st.markdown(f'<div class="quote-row"><span class="qr-label">{lbl}</span><span class="qr-value">{val}{note_html}</span></div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.caption(f"⚠️ {q['disclaimer']}")
                now_q = datetime.now().strftime("%Y-%m-%d")
                qlines = ["="*62,"              SHOP QUOTE — DrawingIQ","="*62,f'Quote #:        {meta.get("quote_number") or "N/A"}',f'Date:           {now_q}',f'Delivery:       {meta.get("due_date") or "TBD"}',"-"*62,f'Customer:       {meta.get("customer_name") or "N/A"}',f'Email:          {meta.get("customer_email") or "N/A"}',"-"*62,f'Part:           {result.get("part_name") or "Unknown"}',f'Material:       {result.get("material") or "Unknown"}',f'Drawing File:   {filename}',"-"*62,f'Quantity:       {q["quantity"]} pcs',f'Complexity:     {q["complexity"]}',"-"*62,f'Machine Cost:   ${q["machine_cost"]:,.2f}',f'Labor Cost:     ${q["labor_cost"]:,.2f}',f'Material Cost:  ${q["material_cost"]:,.2f}',f'Setup Cost:     ${q["setup_cost"]:,.2f}',f'Overhead:       ${q["overhead_amount"]:,.2f}',f'Profit:         ${q["profit_amount"]:,.2f}',"="*62,f'PRICE PER PART: ${q["price_per_part"]:,.2f}',f'TOTAL JOB:      ${q["total_job_cost"]:,.2f}',"="*62,"",q["disclaimer"]]
                st.download_button("⬇ Download Quote (.txt)","\n".join(qlines),file_name=f'quote_{meta.get("quote_number") or "estimate"}.txt',mime="text/plain",use_container_width=True)

    with t_rawnotes:
        st.markdown("### 📝 Raw Drawing Content")
        st.caption("Verbatim text extracted — no interpretation.")
        raw_notes = result.get("raw_notes",[])
        if raw_notes:
            for i,n in enumerate(raw_notes,1):
                st.markdown(f'<div class="flag-item flag-info"><strong>Note {i}:</strong> {esc(n)}</div>', unsafe_allow_html=True)
        else: st.info("No notes extracted.")
        rev_hist = result.get("revision_history",[])
        if rev_hist:
            st.markdown("---\n**Revision History**")
            for r in rev_hist: st.markdown(f"• {esc(r)}")
        related = result.get("related_parts",[])
        if related:
            st.markdown("---\n**Referenced Parts**")
            for p in related: st.markdown(f"• `{esc(p)}`")


    with t_verify:
        st.markdown("### ✏️ Verify & Schedule")
        st.caption("Review every AI-extracted value, correct anything wrong, assign to a machine, and schedule the job.")
        st.markdown("---")

        _aid = str(analysis_id or filename or "draft").replace(" ","_")
        vkey = f"vs_{_aid}"

        if vkey not in st.session_state:
            st.session_state[vkey] = {
                "dims":         {i: {"value": d.get("value",""), "tolerance": d.get("tolerance","") or "", "confirmed": False} for i,d in enumerate(dims)},
                "part_name":    result.get("part_name") or "",
                "part_number":  result.get("part_number") or "",
                "revision":     result.get("revision") or "",
                "material":     result.get("material") or "",
                "surface_finish": result.get("surface_finish") or "",
                "machine": "", "operator": "", "due_date": "",
                "job_number": "", "priority": "Normal",
                "status": "Pending", "notes": "", "verified": False,
            }
        vs = st.session_state[vkey]

        st.markdown("#### Step 1 — Verify Drawing Info")
        vf1,vf2,vf3 = st.columns(3)
        with vf1:
            vs["part_name"]     = st.text_input("Part Name",    value=vs["part_name"],     key=f"vf_pn_{vkey}",  placeholder="Enter part name")
            vs["material"]      = st.text_input("Material",     value=vs["material"],      key=f"vf_mat_{vkey}", placeholder="e.g. 6061-T6 Aluminum")
        with vf2:
            vs["part_number"]   = st.text_input("Part Number",  value=vs["part_number"],   key=f"vf_pno_{vkey}", placeholder="e.g. PN-001")
            vs["surface_finish"]= st.text_input("Surface Finish",value=vs["surface_finish"],key=f"vf_sf_{vkey}",  placeholder="e.g. 125 Ra")
        with vf3:
            vs["revision"]      = st.text_input("Revision",     value=vs["revision"],      key=f"vf_rev_{vkey}", placeholder="e.g. Rev A")

        st.markdown("---")
        st.markdown("#### Step 2 — Verify Dimensions")

        if dims:
            hc1,hc2,hc3,hc4,hc5 = st.columns([3,2,2,1,1])
            for h,t in zip([hc1,hc2,hc3,hc4,hc5],["Feature","Value","Tolerance","Unit","✓ OK"]):
                h.markdown(f"<span style='font-size:0.72rem;color:#6b7280;text-transform:uppercase;font-weight:600;'>{t}</span>", unsafe_allow_html=True)
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            for i,d in enumerate(dims):
                dc1,dc2,dc3,dc4,dc5 = st.columns([3,2,2,1,1])
                is_crit = d.get("is_critical",False)
                with dc1:
                    label_color = "#dc2626" if is_crit else "#374151"
                    st.markdown(f"<div style='padding:8px 0;font-size:0.85rem;color:{label_color};font-weight:{'600' if is_crit else '400'};'>{'🔴 ' if is_crit else ''}{esc(d.get('feature',''))}</div>", unsafe_allow_html=True)
                with dc2:
                    vs["dims"][i]["value"] = st.text_input("v", value=vs["dims"][i]["value"], key=f"vd_v_{vkey}_{i}", label_visibility="collapsed")
                with dc3:
                    vs["dims"][i]["tolerance"] = st.text_input("t", value=vs["dims"][i]["tolerance"], key=f"vd_t_{vkey}_{i}", label_visibility="collapsed", placeholder="N/A")
                with dc4:
                    st.markdown(f"<div style='padding:8px 0;font-size:0.82rem;color:#6b7280;'>{esc(d.get('unit',''))}</div>", unsafe_allow_html=True)
                with dc5:
                    vs["dims"][i]["confirmed"] = st.checkbox("", value=vs["dims"][i]["confirmed"], key=f"vd_c_{vkey}_{i}", label_visibility="collapsed")

            confirmed_n = sum(1 for d in vs["dims"].values() if d["confirmed"])
            total_n     = len(dims)
            pct_n       = int(confirmed_n/max(total_n,1)*100)
            bar_color   = "#16a34a" if pct_n==100 else "#2563eb"
            st.markdown(f"""
            <div style='background:#f8faff;border-radius:8px;padding:0.75rem 1rem;margin-top:0.5rem;display:flex;align-items:center;gap:1rem;'>
                <div style='flex:1;background:#e2e8f0;border-radius:4px;height:8px;'>
                    <div style='background:{bar_color};border-radius:4px;height:8px;width:{pct_n}%;'></div>
                </div>
                <span style='font-size:0.82rem;color:#374151;font-weight:500;white-space:nowrap;'>{confirmed_n}/{total_n} confirmed</span>
            </div>""", unsafe_allow_html=True)

            if st.button("✓ Confirm All Dimensions", key=f"conf_all_{vkey}"):
                for i in vs["dims"]:
                    vs["dims"][i]["confirmed"] = True
                st.rerun()
        else:
            st.info("No dimensions extracted. You can still assign this job below.")

        st.markdown("---")
        st.markdown("#### Step 3 — Assign to Machine & Schedule")

        try:
            machines_vs = get_machines(user["id"])
        except Exception:
            machines_vs = []

        sa1,sa2,sa3 = st.columns(3)
        with sa1:
            if machines_vs:
                mach_opts = ["-- Select Machine --"] + [m["name"] for m in machines_vs]
                sel_m = st.selectbox("Machine / Cell", mach_opts, key=f"vs_mach_{vkey}")
                vs["machine"] = "" if sel_m == "-- Select Machine --" else sel_m
            else:
                vs["machine"]   = st.text_input("Machine / Cell", value=vs["machine"], key=f"vs_mach_t_{vkey}", placeholder="Add machines in Shop Setup")
            vs["operator"]      = st.text_input("Operator",       value=vs["operator"], key=f"vs_op_{vkey}",   placeholder="Machinist name")
        with sa2:
            vs["job_number"]    = st.text_input("Job / WO #",     value=vs["job_number"], key=f"vs_job_{vkey}", placeholder="WO-2026-001")
            vs["due_date"]      = str(st.date_input("Due Date",   key=f"vs_due_{vkey}"))
        with sa3:
            vs["priority"]      = st.selectbox("Priority", ["Normal","Rush","Emergency","Low"],   key=f"vs_pri_{vkey}")
            vs["status"]        = st.selectbox("Status",   ["Pending","In Progress","On Hold","Complete"], key=f"vs_stat_{vkey}")

        vs["notes"] = st.text_area("Setup Notes", value=vs["notes"], key=f"vs_notes_{vkey}", placeholder="Special fixturing, customer requirements, known issues...", height=80)

        st.markdown("---")
        st.markdown("#### Step 4 — Sign Off & Save")

        confirmed_c  = sum(1 for d in vs["dims"].values() if d["confirmed"]) if dims else 0
        total_c      = len(dims)
        has_machine  = bool(vs.get("machine",""))
        has_material = bool(vs.get("material",""))
        r_score      = 0
        r_items      = []

        if total_c > 0 and confirmed_c == total_c: r_score+=40; r_items.append(("✅",f"All {total_c} dimensions confirmed"))
        elif total_c > 0: r_items.append(("⚠️",f"{confirmed_c}/{total_c} dimensions confirmed"))
        if has_material:  r_score+=20; r_items.append(("✅",f"Material: {vs['material']}"))
        else:             r_items.append(("❌","Material not specified"))
        if has_machine:   r_score+=20; r_items.append(("✅",f"Assigned to: {vs['machine']}"))
        else:             r_items.append(("⚠️","No machine assigned"))
        if vs.get("operator"):   r_score+=10; r_items.append(("✅",f"Operator: {vs['operator']}"))
        else:             r_items.append(("⚠️","No operator assigned"))
        if vs.get("job_number"): r_score+=10; r_items.append(("✅",f"Job #: {vs['job_number']}"))
        else:             r_items.append(("⚠️","No job number"))

        sc_color = "#16a34a" if r_score>=80 else "#d97706" if r_score>=50 else "#dc2626"
        items_html = "".join(f'<div style="font-size:0.83rem;padding:2px 0;">{icon} {esc(item)}</div>' for icon,item in r_items)
        st.markdown(f"""
        <div style='background:white;border:1px solid #dbeafe;border-radius:10px;padding:1rem 1.25rem;'>
            <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;'>
                <span style='font-weight:600;color:#0f172a;'>Job Readiness</span>
                <span style='font-size:1.5rem;font-weight:800;font-family:monospace;color:{sc_color};'>{r_score}%</span>
            </div>
            <div style='background:#f1f5f9;border-radius:4px;height:10px;margin-bottom:0.75rem;'>
                <div style='background:{sc_color};border-radius:4px;height:10px;width:{r_score}%;'></div>
            </div>
            {items_html}
        </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
        btn1,btn2 = st.columns([2,1])
        with btn1:
            if st.button("✅ Mark as Verified & Ready to Machine", type="primary", use_container_width=True, key=f"vs_verify_{vkey}"):
                vs["verified"]    = True
                vs["verified_by"] = user_name
                vs["verified_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state[vkey] = vs
                st.success(f"✅ Verified by {user_name} at {vs['verified_at']}. Job traveler updated.")
                st.balloons()
        with btn2:
            if vs.get("verified"):
                st.markdown(f"""
                <div style='background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:0.6rem 0.9rem;text-align:center;'>
                    <div style='color:#16a34a;font-weight:700;font-size:0.85rem;'>✅ VERIFIED</div>
                    <div style='color:#6b7280;font-size:0.72rem;margin-top:2px;'>{esc(vs.get("verified_at",""))}</div>
                    <div style='color:#6b7280;font-size:0.72rem;'>{esc(vs.get("verified_by",""))}</div>
                </div>""", unsafe_allow_html=True)

        if vs.get("verified"):
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if st.button("💾 Save to Production Queue", key=f"vs_save_{vkey}", use_container_width=True):
                job_entry = {
                    "id":          vkey,
                    "filename":    filename,
                    "part_name":   vs["part_name"]   or result.get("part_name","Unknown"),
                    "part_number": vs["part_number"],
                    "material":    vs["material"],
                    "machine":     vs["machine"],
                    "operator":    vs["operator"],
                    "job_number":  vs["job_number"],
                    "due_date":    vs["due_date"],
                    "priority":    vs["priority"],
                    "status":      vs["status"],
                    "notes":       vs["notes"],
                    "verified_by": vs.get("verified_by",""),
                    "verified_at": vs.get("verified_at",""),
                    "complexity":  result.get("estimated_complexity","Unknown"),
                    "analysis_id": str(analysis_id or ""),
                }
                try:
                    save_job_to_queue(user["id"], job_entry)
                    st.success("✅ Job saved to production queue! View it on the Dashboard.")
                except Exception as _save_err:
                    logger.error("Queue save error: %s", _save_err)
                    if "job_queue" not in st.session_state:
                        st.session_state["job_queue"] = []
                    existing = [j for j in st.session_state["job_queue"] if j["id"] != vkey]
                    existing.append(job_entry)
                    st.session_state["job_queue"] = existing


    with t_print:
        st.markdown("**🖨 Job Traveler / Setup Sheet**")
        pt1,pt2 = st.columns(2)
        with pt1:
            op_name    = st.text_input("Operator Name",key=f"pt_op_{analysis_id}")
            machine_id = st.text_input("Machine / Cell",placeholder="VMC-3",key=f"pt_mc_{analysis_id}")
        with pt2:
            job_number = st.text_input("Job / Work Order #",key=f"pt_job_{analysis_id}")
            due_date_p = st.text_input("Due Date",key=f"pt_due_{analysis_id}")
        # Pull verified data if available
        verify_key_p = f"vs_{str(analysis_id or filename or 'draft').replace(' ','_')}"
        vs_p = st.session_state.get(verify_key_p, {})
        verified_stamp = ""
        if vs_p.get("verified"):
            verified_stamp = f"AI ANALYZED — HUMAN VERIFIED by {vs_p.get('verified_by','')} at {vs_p.get('verified_at','')}"
            # Auto-fill from verified data if not manually entered
            if not op_name and vs_p.get("operator"):     op_name    = vs_p["operator"]
            if not machine_id and vs_p.get("machine"):   machine_id = vs_p["machine"]
            if not job_number and vs_p.get("job_number"):job_number = vs_p["job_number"]
            if not due_date_p and vs_p.get("due_date"):  due_date_p = vs_p["due_date"]

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = ["="*62,"       DRAWINGIQ — JOB TRAVELER / SETUP SHEET","="*62,
                 (verified_stamp if verified_stamp else "AI ANALYZED — AWAITING HUMAN VERIFICATION"),
                 "="*62,
                 f"File:           {filename}",f"Generated:      {now_str}",f"Job / WO #:     {job_number or 'N/A'}",f"Operator:       {op_name or 'N/A'}",f"Machine / Cell: {machine_id or 'N/A'}",f"Due Date:       {due_date_p or 'N/A'}", "-"*62,f"Part:           {result.get('part_name') or 'Unknown'}",f"Part Number:    {result.get('part_number') or 'Unknown'}",f"Revision:       {result.get('revision') or 'Unknown'}",f"Material:       {result.get('material') or 'Unknown'} ({result.get('material_spec') or 'No spec'})",f"Surface Finish: {result.get('surface_finish') or 'Unknown'}",f"Heat Treat:     {result.get('heat_treatment') or 'None'}",f"Units:          {result.get('units') or 'Unknown'}",f"Complexity:     {result.get('estimated_complexity') or 'Unknown'}",f"Confidence:     {conf}%  |  Clarity: {clarity}","-"*62,f"FLAGS — {len(critical)} critical  {len(warnings)} warnings","-"*62]
        for f in flags:
            lines.append(f"  [{f.get('severity','').upper()}] {f.get('category','')}: {f.get('description','')}")
            if f.get("recommendation"): lines.append(f"         → {f.get('recommendation')}")
        lines += ["-"*62,"MACHINIST NOTES:","-"*62,result.get("machinist_notes") or "—"]
        if dims:
            lines += ["","KEY DIMENSIONS:","-"*62]
            for d in dims:
                crit_m = "  *** CRITICAL ***" if d.get("is_critical") else ""
                lines.append(f"  {str(d.get('feature','')):<28} {d.get('value','')} {d.get('unit','')}  ±{d.get('tolerance','N/A')}{crit_m}")
        raw = result.get("raw_notes",[])
        if raw:
            lines += ["","DRAWING NOTES (VERBATIM):","-"*62]
            for i,n in enumerate(raw,1): lines.append(f"  {i}. {n}")
        lines += ["","SIGN-OFF:","-"*62,"Setup verified by: ___________________  Date: __________","First article OK:  ___________________  Date: __________","QC approved:       ___________________  Date: __________"]
        traveler_text = "\n".join(lines)
        st.text_area("Preview",traveler_text,height=300,key=f"pt_prev_{analysis_id}")
        st.download_button("⬇ Download Job Traveler (.txt)",traveler_text,file_name=f'{filename.rsplit(".",1)[0]}_traveler.txt',mime="text/plain",use_container_width=True)

    with t_export:
        if not limits.get("export"):
            st.markdown('<div class="upgrade-banner">Export requires Starter plan or higher.</div>', unsafe_allow_html=True)
        else:
            c1,c2 = st.columns(2)
            with c1:
                st.download_button("⬇ Full JSON",json.dumps(result,indent=2),file_name=f'{filename.rsplit(".",1)[0]}.json',mime="application/json",use_container_width=True)
            with c2:
                buf = io.StringIO(); w = csv.writer(buf)
                w.writerow(["Field","Value"])
                for k,v in result.items():
                    if isinstance(v,(str,int,float,bool)): w.writerow([k,v])
                for d in result.get("dimensions",[]):
                    w.writerow([f'DIM:{d.get("feature")}',f'{d.get("value")} {d.get("unit")} ±{d.get("tolerance","N/A")}'])
                for f in flags:
                    w.writerow([f'FLAG[{f.get("severity","").upper()}]',f'{f.get("category")}: {f.get("description")}'])
                st.download_button("⬇ CSV",buf.getvalue(),file_name=f'{filename.rsplit(".",1)[0]}.csv',mime="text/csv",use_container_width=True)

# PAGE: ANALYZE
# ─────────────────────────────────────────────────────────────────────────────
# HELPER: machine capability check
# ─────────────────────────────────────────────────────────────────────────────
def check_machine_capability(dims, machines):
    """Flag dimensions tighter than any machine in shop can hold."""
    if not machines or not dims:
        return []
    best_tol = min(m["tolerance_mm"] for m in machines)
    risks = []
    for d in dims:
        tol_str = d.get("tolerance","")
        if not tol_str or tol_str in ("N/A","—","Unknown","null","None"):
            continue
        try:
            tol_val = float(str(tol_str).replace("±","").replace("+/-","").strip().split("/")[0])
            unit = d.get("unit","mm")
            tol_mm = tol_val if "mm" in unit.lower() else tol_val * 25.4
            if tol_mm < best_tol:
                risks.append({
                    "feature": d.get("feature",""),
                    "tolerance": tol_str,
                    "unit": unit,
                    "tightest_machine": min(machines, key=lambda m: m["tolerance_mm"])["name"],
                    "machine_capability": best_tol,
                })
        except Exception:
            continue
    return risks

if page == "📤 Analyze":
    allowed,reason = can_analyze(profile)
    if allowed and profile.get("plan","free") == "free":
        allowed2, reason2 = enforce_free_limits(profile, user.get("email",""))
        if not allowed2:
            allowed, reason = allowed2, reason2
    if not allowed:
        st.error(reason)
        st.markdown('<div class="upgrade-banner" style="max-width:500px;margin:1rem auto;"><strong>Monthly limit reached</strong>Upgrade to continue.</div>', unsafe_allow_html=True)
        if st.button("View Upgrade Options",type="primary"): st.session_state["force_page"]="💳 Billing"; st.rerun()
        st.stop()
    qc1,qc2 = st.columns([3,2])
    with qc1:
        disc_idx   = DISCIPLINES.index(st.session_state["pref_discipline"]) if st.session_state["pref_discipline"] in DISCIPLINES else 0
        discipline = st.selectbox("Discipline",DISCIPLINES,index=disc_idx,key="qs_disc")
        st.session_state["pref_discipline"] = discipline
    with qc2:
        detail_level = st.select_slider("Detail Level",DETAIL_LEVELS,value=st.session_state["pref_detail"],key="qs_detail")
        st.session_state["pref_detail"] = detail_level
    accepted  = ["png","jpg","jpeg","webp"]+( ["pdf"] if limits.get("pdf") else [])
    max_batch = limits["batch_size"]
    fmt_str   = " · ".join(t.upper() for t in accepted)
    st.markdown(f'<div class="drop-zone-hint"><div style="font-size:2.2rem;">📐</div><h3>Drop your engineering drawing here</h3><p>{fmt_str} &nbsp;|&nbsp; Max {MAX_FILE_MB} MB &nbsp;|&nbsp; Up to {max_batch} file(s) on {plan.title()} plan</p></div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload",type=accepted,accept_multiple_files=(max_batch>1),label_visibility="collapsed")
    if not uploaded: uploaded=[]
    elif not isinstance(uploaded,list): uploaded=[uploaded]
    if len(uploaded)>max_batch: st.warning(f"Only first {max_batch} files analyzed."); uploaded=uploaded[:max_batch]
    if uploaded:
        if len(uploaded)==1:
            f=uploaded[0]; pc1,pc2=st.columns([1,2])
            with pc1:
                if not f.name.lower().endswith(".pdf"): prev=f.read(); f.seek(0); st.image(prev,use_container_width=True)
                else: st.info(f"📄 PDF: `{f.name}`")
            with pc2: st.markdown(f"**`{f.name}`**"); st.caption(f"{f.size/1024:.1f} KB · {discipline} · {detail_level}")
        else:
            cols=st.columns(min(len(uploaded),5))
            for i,f in enumerate(uploaded):
                with cols[i%5]:
                    if not f.name.lower().endswith(".pdf"): prev=f.read(); f.seek(0); st.image(prev,use_container_width=True,caption=f.name[:15])
                    else: st.markdown(f"📄 `{f.name[:15]}`")
        st.markdown("---")
        if st.button(f"⚙ Analyze {len(uploaded)} Drawing(s)",type="primary",use_container_width=True):
            for uf in uploaded:
                fname=uf.name; file_bytes=uf.read(); size_kb=len(file_bytes)/1024
                if size_kb>MAX_FILE_MB*1024: st.error(f"{fname} too large ({size_kb/1024:.1f} MB). Max {MAX_FILE_MB} MB."); continue
                with st.expander(f"📄 {fname}",expanded=True):
                    try:
                        if fname.lower().endswith(".pdf"):
                            with st.spinner("Converting PDF pages…"): pages=pdf_to_images(file_bytes,dpi=200,max_pages=10)
                            if not pages: st.error("Could not extract pages from PDF."); continue
                            st.caption(f"Extracted {len(pages)} page(s)")
                            with st.spinner(f"Analyzing {fname}…"): result=analyze_pdf_pages(pages,discipline,detail_level,_api_key)
                        else:
                            with st.spinner(f"Analyzing {fname}…"): b64,mime=image_file_to_b64(file_bytes,fname); result=analyze_image(b64,mime,discipline,detail_level,_api_key)
                        saved=save_analysis(user_id=user["id"],filename=fname,result=result,file_size_kb=size_kb,analysis_mode=discipline,detail_level=detail_level,workspace_id=workspace_id)
                        render_result(result,fname,saved.get("id"))
                        # ── Repeat part detection ──────────────────────────
                        try:
                            pname = result.get("part_name","")
                            pnum  = result.get("part_number","")
                            if pname or pnum:
                                similar = find_similar_parts(user["id"], pname, pnum)
                                similar = [s for s in similar if s.get("id") != saved.get("id")]
                                if similar:
                                    st.markdown("---")
                                    st.info(f"🔁 **Repeat Part Detected** — Found {len(similar)} previous analysis(es) matching this part.")
                                    for sim in similar[:3]:
                                        sim_date = str(sim.get("created_at",""))[:10]
                                        st.markdown(f"• **{esc(sim.get('filename',''))}** — {sim_date} · {esc(sim.get('material','?'))} · {esc(sim.get('estimated_complexity','?'))} complexity")
                        except Exception:
                            pass
                        # ── Machine capability check ────────────────────────
                        try:
                            machines = get_machines(user["id"])
                            if machines:
                                cap_risks = check_machine_capability(result.get("dimensions",[]), machines)
                                if cap_risks:
                                    st.warning(f"⚠️ **{len(cap_risks)} dimension(s)** may exceed your machines' capability:")
                                    for r in cap_risks:
                                        st.markdown(f"• `{esc(r['feature'])}` ±{esc(r['tolerance'])} — tighter than **{esc(r['tightest_machine'])}** can hold (±{r['machine_capability']} mm)")
                        except Exception:
                            pass
                    except Exception as e:
                        st.error(friendly_error(e))
                        if st.button("↩ Retry",key=f"retry_{fname}"): st.rerun()
            refresh_profile()
            profile = get_current_profile() or {}
    else:
        st.markdown('<div class="empty-state"><div class="icon">⚙</div><h3>Upload a drawing to get started</h3><p>Supports mechanical, structural, electrical, architectural, welding drawings.</p></div>', unsafe_allow_html=True)

# PAGE: DASHBOARD
elif page == "📊 Dashboard":
    st.markdown("## 📊 Shop Dashboard")
    stats    = get_usage_stats(user["id"])
    analyses = get_analyses(user["id"],limit=300,workspace_id=workspace_id)
    mc1,mc2,mc3,mc4,mc5 = st.columns(5)
    mc1.metric("This Month",stats.get("analyses_this_month",0))
    mc2.metric("All Time",stats.get("analyses_total",0))
    mc3.metric("Remaining",max(0,cap-stats.get("analyses_this_month",0)))
    mc4.metric("Critical Flags",sum(a.get("flag_critical_count",0) for a in analyses))
    avg_conf = round(sum(a.get("confidence_score",0) for a in analyses)/len(analyses)) if analyses else 0
    mc5.metric("Avg Confidence",f"{avg_conf}%")
    st.markdown("---")
    dc1,dc2 = st.columns(2)
    with dc1:
        type_counts={}
        for a in analyses:
            t=a.get("drawing_type") or "Unknown"; type_counts[t]=type_counts.get(t,0)+1
        st.markdown('<div class="dash-card"><h4>Drawing Types</h4>', unsafe_allow_html=True)
        for dtype,cnt in sorted(type_counts.items(),key=lambda x:-x[1]):
            pct=int(cnt/max(len(analyses),1)*100)
            st.markdown(f'<div style="margin-bottom:6px;"><div style="display:flex;justify-content:space-between;font-size:0.83rem;margin-bottom:2px;"><span>{esc(dtype)}</span><span style="color:#6b7280;">{cnt} ({pct}%)</span></div><div style="background:#f1f5f9;border-radius:4px;height:6px;"><div style="background:#2563eb;border-radius:4px;height:6px;width:{pct}%;"></div></div></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        cmp_counts={}
        for a in analyses:
            c=a.get("estimated_complexity") or "Unknown"; cmp_counts[c]=cmp_counts.get(c,0)+1
        cmp_colors={"Low":"#16a34a","Medium":"#d97706","High":"#dc2626","Very High":"#7c3aed","Unknown":"#9ca3af"}
        st.markdown('<div class="dash-card"><h4>Complexity Distribution</h4>', unsafe_allow_html=True)
        for cmp,cnt in sorted(cmp_counts.items(),key=lambda x:["Low","Medium","High","Very High","Unknown"].index(x[0]) if x[0] in ["Low","Medium","High","Very High","Unknown"] else 99):
            pct=int(cnt/max(len(analyses),1)*100); color=cmp_colors.get(cmp,"#9ca3af")
            st.markdown(f'<div style="margin-bottom:6px;"><div style="display:flex;justify-content:space-between;font-size:0.83rem;margin-bottom:2px;"><span style="color:{color};font-weight:500;">{esc(cmp)}</span><span style="color:#6b7280;">{cnt} ({pct}%)</span></div><div style="background:#f1f5f9;border-radius:4px;height:6px;"><div style="background:{color};border-radius:4px;height:6px;width:{pct}%;"></div></div></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with dc2:
        recent_crits=[a for a in analyses[:20] if a.get("flag_critical_count",0)>0]
        st.markdown('<div class="dash-card"><h4>Recent Critical Flags</h4>', unsafe_allow_html=True)
        if recent_crits:
            for a in recent_crits[:8]:
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f1f5f9;font-size:0.83rem;"><span>{esc(a.get("filename",""))}</span><span style="background:#fee2e2;color:#991b1b;font-size:0.7rem;font-weight:600;padding:1px 7px;border-radius:4px;">🔴 {a.get("flag_critical_count",0)}</span></div>', unsafe_allow_html=True)
        else: st.markdown('<p style="color:#9ca3af;font-size:0.85rem;">No critical flags recently.</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        mat_counts={}
        for a in analyses:
            m=a.get("material") or "Unknown"; mat_counts[m]=mat_counts.get(m,0)+1
        st.markdown('<div class="dash-card"><h4>Top Materials</h4>', unsafe_allow_html=True)
        for mat,cnt in sorted(mat_counts.items(),key=lambda x:-x[1])[:6]:
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:4px 0;font-size:0.83rem;border-bottom:1px solid #f1f5f9;"><span>{esc(mat)}</span><span style="color:#6b7280;font-family:monospace;">{cnt}</span></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Production Queue ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🏭 Production Queue")
    st.caption("Jobs that have been verified and scheduled. Update status as work progresses.")
    # Load from DB first, fallback to session state
    try:
        queue = get_job_queue(user["id"])
        # Also merge any session-state jobs not yet saved
        ss_queue = st.session_state.get("job_queue", [])
        db_ids   = {j.get("id") for j in queue}
        for ssj in ss_queue:
            if ssj.get("id") not in db_ids:
                queue.append(ssj)
    except Exception:
        queue = st.session_state.get("job_queue", [])
    if not queue:
        st.markdown('<div class="empty-state"><div class="icon">🏭</div><h3>No jobs in queue yet</h3><p>Verify and schedule a job from the Analyze page to see it here.</p></div>', unsafe_allow_html=True)
    else:
        priority_colors = {"Emergency":"#dc2626","Rush":"#d97706","Normal":"#2563eb","Low":"#6b7280"}
        status_colors   = {"Pending":"#6b7280","In Progress":"#2563eb","On Hold":"#d97706","Complete":"#16a34a"}

        # Summary metrics
        qm1,qm2,qm3,qm4 = st.columns(4)
        qm1.metric("Total Jobs",    len(queue))
        qm2.metric("In Progress",   sum(1 for j in queue if j.get("status")=="In Progress"))
        qm3.metric("Pending",       sum(1 for j in queue if j.get("status")=="Pending"))
        qm4.metric("Complete",      sum(1 for j in queue if j.get("status")=="Complete"))

        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

        # Sort by priority then due date
        priority_order = {"Emergency":0,"Rush":1,"Normal":2,"Low":3}
        sorted_queue   = sorted(queue, key=lambda x: (priority_order.get(x.get("priority","Normal"),2), x.get("due_date","")))

        for job in sorted_queue:
            pc     = priority_colors.get(job.get("priority","Normal"),"#2563eb")
            sc     = status_colors.get(job.get("status","Pending"),"#6b7280")
            jc1,jc2 = st.columns([5,1])
            with jc1:
                st.markdown(f"""
                <div style="background:white;border:1px solid #dbeafe;border-left:4px solid {pc};border-radius:10px;padding:0.9rem 1.1rem;margin-bottom:0.4rem;">
                    <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;margin-bottom:5px;">
                        <span style="font-weight:700;color:#0f172a;font-size:0.92rem;">{esc(job.get("part_name","Unknown"))}</span>
                        <span style="background:{sc}20;color:{sc};font-size:0.7rem;font-weight:700;padding:2px 8px;border-radius:4px;">{esc(job.get("status","Pending").upper())}</span>
                        <span style="background:{pc}15;color:{pc};font-size:0.7rem;font-weight:700;padding:2px 8px;border-radius:4px;">{esc(job.get("priority","Normal").upper())}</span>
                        <span style="margin-left:auto;font-size:0.75rem;color:#9ca3af;">Due: {esc(job.get("due_date","TBD"))}</span>
                    </div>
                    <div style="font-size:0.78rem;color:#6b7280;display:flex;gap:1rem;flex-wrap:wrap;">
                        <span>📄 {esc(job.get("filename",""))}</span>
                        <span>⚙ {esc(job.get("machine","No machine"))}</span>
                        <span>👷 {esc(job.get("operator","Unassigned"))}</span>
                        <span>🔢 {esc(job.get("job_number","No WO#"))}</span>
                        <span>🧱 {esc(job.get("material","Unknown"))}</span>
                        <span>✅ Verified by {esc(job.get("verified_by",""))}</span>
                    </div>
                    {('<div style="font-size:0.78rem;color:#374151;margin-top:5px;background:#f8faff;padding:4px 8px;border-radius:4px;">📝 ' + esc(job.get("notes","")) + '</div>') if job.get("notes") else ""}
                </div>""", unsafe_allow_html=True)
            with jc2:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                new_status = st.selectbox("Status", ["Pending","In Progress","On Hold","Complete"],
                    index=["Pending","In Progress","On Hold","Complete"].index(job.get("status","Pending")),
                    key=f"qs_stat_{job['id']}",
                    label_visibility="collapsed")
                if new_status != job.get("status"):
                    try:
                        update_job_status(job["id"], user["id"], new_status)
                    except Exception:
                        # Fallback session state
                        for j in st.session_state.get("job_queue",[]):
                            if j["id"] == job["id"]: j["status"] = new_status
                    st.rerun()
                if st.button("🗑", key=f"qs_del_{job['id']}"):
                    try:
                        delete_job_from_queue(job["id"], user["id"])
                    except Exception:
                        st.session_state["job_queue"] = [j for j in st.session_state.get("job_queue",[]) if j["id"] != job["id"]]
                    st.rerun()

# PAGE: HISTORY
elif page == "📋 History":
    st.markdown("## Analysis History")
    with st.spinner("Loading…"): analyses=get_analyses(user["id"],limit=200,workspace_id=workspace_id)
    if not analyses:
        st.markdown('<div class="empty-state"><div class="icon">📋</div><h3>No analyses yet</h3></div>', unsafe_allow_html=True)
    else:
        fc1,fc2,fc3,fc4=st.columns([2,1,1,1])
        with fc1: search=st.text_input("Search",placeholder="Part name, filename…",label_visibility="collapsed")
        with fc2: type_filter=st.selectbox("Type",["All Types","Mechanical","Structural","Electrical","Architectural","PCB","Welding"],label_visibility="collapsed")
        with fc3: date_filter=st.selectbox("Date",["All Time","Today","This Week","This Month"],label_visibility="collapsed")
        with fc4:
            if limits.get("export"):
                buf=io.StringIO(); w=csv.writer(buf)
                w.writerow(["ID","Filename","Date","Type","Part","Material","Complexity","Confidence","Critical","Warnings"])
                for a in analyses: w.writerow([a["id"],a["filename"],a["created_at"],a.get("drawing_type"),a.get("part_name"),a.get("material"),a.get("estimated_complexity"),a.get("confidence_score"),a.get("flag_critical_count",0),a.get("flag_warning_count",0)])
                st.download_button("⬇ Export CSV",buf.getvalue(),file_name=f'drawingiq_{datetime.now().strftime("%Y%m%d")}.csv',mime="text/csv",use_container_width=True)
            else:
                if st.button("⬇ Export (Starter+)",use_container_width=True): st.info("Upgrade to export.")
        filtered=analyses
        if search:
            s=search.lower(); filtered=[a for a in filtered if s in (a.get("filename","")).lower() or s in (a.get("part_name","") or "").lower()]
        if type_filter!="All Types": filtered=[a for a in filtered if a.get("drawing_type")==type_filter]
        if date_filter!="All Time":
            today=date.today()
            if date_filter=="Today": filtered=[a for a in filtered if str(a.get("created_at",""))[:10]==str(today)]
            elif date_filter=="This Week": cutoff=str(today-timedelta(days=7)); filtered=[a for a in filtered if str(a.get("created_at",""))[:10]>=cutoff]
            elif date_filter=="This Month": prefix=today.strftime("%Y-%m"); filtered=[a for a in filtered if str(a.get("created_at","")).startswith(prefix)]
        st.caption(f"Showing {len(filtered)} of {len(analyses)} analyses"); st.markdown("---")
        for a in filtered:
            crit=a.get("flag_critical_count",0); warn=a.get("flag_warning_count",0); dt=str(a.get("created_at",""))[:10]; aid=a["id"]
            if st.session_state["pending_delete"]==aid:
                st.markdown(f'<div class="confirm-delete-row">⚠️ Delete <strong>{esc(a.get("filename",""))}</strong>?</div>', unsafe_allow_html=True)
                cc1,cc2=st.columns(2)
                with cc1:
                    if st.button("✓ Yes",key=f"conf_{aid}",type="primary",use_container_width=True): delete_analysis(aid,user["id"]); st.session_state["pending_delete"]=None; st.rerun()
                with cc2:
                    if st.button("✗ Cancel",key=f"cancel_{aid}",use_container_width=True): st.session_state["pending_delete"]=None; st.rerun()
                continue
            flag_badges=""
            if crit: flag_badges+=f'<span style="background:#fee2e2;color:#991b1b;font-size:0.7rem;font-weight:600;padding:2px 7px;border-radius:4px;margin-left:5px;">🔴 {crit} critical</span>'
            if warn: flag_badges+=f'<span style="background:#fef3c7;color:#92400e;font-size:0.7rem;font-weight:600;padding:2px 7px;border-radius:4px;margin-left:5px;">⚠ {warn} warning</span>'
            card_col,btn_col=st.columns([6,1])
            with card_col:
                st.markdown(f'<div class="history-card"><div style="display:flex;align-items:center;gap:0.4rem;flex-wrap:wrap;"><span style="font-weight:600;color:#0f172a;font-size:0.92rem;">{esc(a.get("filename",""))}</span>{flag_badges}<span style="margin-left:auto;font-size:0.75rem;color:#9ca3af;">📅 {esc(dt)}</span></div><div style="font-size:0.77rem;color:#6b7280;margin-top:4px;display:flex;gap:1rem;flex-wrap:wrap;"><span>📐 {esc(a.get("drawing_type","Unknown"))}</span><span>🔩 {esc(a.get("part_name","Unknown"))}</span><span>🧱 {esc(a.get("material","Unknown"))}</span><span>⚙ {esc(a.get("estimated_complexity","Unknown"))}</span><span>🎯 {esc(a.get("confidence_score","?"))}%</span></div></div>', unsafe_allow_html=True)
            with btn_col:
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                if st.button("👁 View",key=f"view_{aid}",use_container_width=True): st.session_state["viewing_analysis"]=aid; st.rerun()
                if st.button("🗑 Del",key=f"del_{aid}",use_container_width=True): st.session_state["pending_delete"]=aid; st.rerun()
            st.markdown("<div style='margin-bottom:0.2rem'></div>", unsafe_allow_html=True)
        if "viewing_analysis" in st.session_state:
            aid=st.session_state["viewing_analysis"]; record=get_analysis_by_id(aid)
            if record:
                st.markdown("---"); st.markdown(f"### {esc(record['filename'])}")
                if st.button("✕ Close",key="close_view"): del st.session_state["viewing_analysis"]; st.rerun()
                render_result(record["result_json"],record["filename"],aid)
            else:
                st.warning("Analysis not found or access denied."); del st.session_state["viewing_analysis"]

# PAGE: COMPARE
elif page == "🔍 Compare":
    st.markdown("## 🔍 Side-by-Side Drawing Comparison")
    st.caption("Spot revision differences, material changes, or validate re-quotes.")
    with st.spinner("Loading…"): analyses=get_analyses(user["id"],limit=100,workspace_id=workspace_id)
    if len(analyses)<2: st.info("Need at least 2 analyses to compare.")
    else:
        options={f'{a.get("filename","")!s} — {str(a.get("created_at",""))[:10]}':a["id"] for a in analyses}
        keys=list(options.keys())
        cmp1,cmp2=st.columns(2)
        with cmp1: sel1=st.selectbox("Drawing A",keys,index=0,key="cmp_a")
        with cmp2: sel2=st.selectbox("Drawing B",keys,index=min(1,len(keys)-1),key="cmp_b")
        if st.button("Compare →",type="primary",use_container_width=True):
            r1=get_analysis_by_id(options[sel1]); r2=get_analysis_by_id(options[sel2])
            if r1 and r2:
                d1=r1["result_json"]; d2=r2["result_json"]; st.markdown("---")
                compare_fields=[("Drawing Type","drawing_type"),("Part Name","part_name"),("Part Number","part_number"),("Revision","revision"),("Material","material"),("Material Spec","material_spec"),("Surface Finish","surface_finish"),("Heat Treatment","heat_treatment"),("Scale","scale"),("Units","units"),("Complexity","estimated_complexity"),("Setups Est.","setup_count_estimate"),("Tol. Stack Risk","tolerance_stack_risk"),("Confidence","confidence_score")]
                h1,h2=st.columns(2); h1.markdown(f"**A: {esc(r1['filename'])}**"); h2.markdown(f"**B: {esc(r2['filename'])}**")
                for label,key in compare_fields:
                    v1=str(d1.get(key) or "Unknown"); v2=str(d2.get(key) or "Unknown")
                    changed=v1.lower()!=v2.lower(); bg="background:#fffbeb;" if changed else ""; badge=" 🔄" if changed else ""
                    fc1,fc2=st.columns(2)
                    with fc1: st.markdown(f'<div style="padding:5px 8px;border-radius:4px;{bg}font-size:0.85rem;margin-bottom:3px;"><span style="color:#6b7280;font-size:0.72rem;">{label}{badge}</span><br><strong>{esc(v1)}</strong></div>', unsafe_allow_html=True)
                    with fc2: st.markdown(f'<div style="padding:5px 8px;border-radius:4px;{bg}font-size:0.85rem;margin-bottom:3px;"><span style="color:#6b7280;font-size:0.72rem;">{label}{badge}</span><br><strong>{esc(v2)}</strong></div>', unsafe_allow_html=True)
                st.markdown("---\n**Flags**")
                fc1,fc2=st.columns(2)
                for col,dx in [(fc1,d1),(fc2,d2)]:
                    with col:
                        for f in dx.get("flags",[]):
                            cls="flag-critical" if f.get("severity")=="critical" else "flag-warning" if f.get("severity")=="warning" else "flag-info"
                            st.markdown(f'<div class="flag-item {cls}" style="font-size:0.82rem;">{esc(f.get("category",""))}: {esc(f.get("description",""))}</div>', unsafe_allow_html=True)

# PAGE: REVIEW CHECKLIST
elif page == "✅ Review Checklist":
    st.markdown("## ✅ Pre-Machining Review Checklist")
    with st.spinner("Loading…"): analyses=get_analyses(user["id"],limit=100,workspace_id=workspace_id)
    if not analyses: st.info("No analyses yet.")
    else:
        options={f'{a.get("filename","")!s} — {str(a.get("created_at",""))[:10]}':a["id"] for a in analyses}
        sel=st.selectbox("Select Drawing",list(options.keys()))
        if st.button("Generate Checklist",type="primary"):
            record=get_analysis_by_id(options[sel])
            if record:
                result=record["result_json"]; checks=build_checklist(result)
                passed=sum(1 for c in checks if c["status"]=="pass"); failed=sum(1 for c in checks if c["status"]=="fail"); warned=sum(1 for c in checks if c["status"]=="warn")
                sc1,sc2,sc3=st.columns(3); sc1.metric("Passed",passed); sc2.metric("Warnings",warned); sc3.metric("Failed",failed)
                if failed==0 and warned==0: st.success("🟢 Ready to machine.")
                elif failed==0: st.warning(f"🟡 {warned} item(s) to review.")
                else: st.error(f"🔴 {failed} item(s) must be resolved.")
                st.markdown("---"); icons={"pass":"✅","fail":"❌","warn":"⚠️"}
                for c in checks:
                    note=f' <span style="color:#9ca3af;font-size:0.8rem;">— {esc(c["note"])}</span>' if c["note"] else ""
                    st.markdown(f'<div class="checklist-item"><span>{icons[c["status"]]}</span><span><strong>{esc(c["label"])}</strong>{note}</span></div>', unsafe_allow_html=True)
                cl_txt="\n".join(f'[{"PASS" if c["status"]=="pass" else "FAIL" if c["status"]=="fail" else "WARN"}] {c["label"]}' + (f' — {c["note"]}' if c["note"] else "") for c in checks)
                st.download_button("⬇ Download Checklist",f'DRAWINGIQ PRE-MACHINING CHECKLIST\nPart: {result.get("part_name","Unknown")} | File: {record["filename"]} | {datetime.now().strftime("%Y-%m-%d %H:%M")}\n{"="*60}\n{cl_txt}',file_name=f'{record["filename"].rsplit(".",1)[0]}_checklist.txt',mime="text/plain",use_container_width=True)

# PAGE: TEAM
elif page == "👥 Team":
    st.markdown("## Team Workspaces")
    if not limits.get("team"):
        st.markdown('<div class="upgrade-banner" style="max-width:600px;"><strong>Team workspaces require Pro or Enterprise</strong></div>', unsafe_allow_html=True)
        if st.button("Upgrade to Pro →",type="primary"): st.session_state["force_page"]="💳 Billing"; st.rerun()
        st.stop()
    workspaces=get_user_workspaces(user["id"]); col1,col2=st.columns([2,1])
    with col2:
        with st.expander("+ Create Workspace"):
            ws_name=st.text_input("Workspace Name",placeholder="Acme Mfg – QA Team")
            if st.button("Create",type="primary"):
                if ws_name: create_workspace(user["id"],ws_name); st.success(f"Workspace '{ws_name}' created!"); st.rerun()
    if not workspaces:
        st.markdown('<div class="empty-state"><div class="icon">👥</div><h3>No workspaces yet</h3></div>', unsafe_allow_html=True)
    else:
        for ws_entry in workspaces:
            wsd=ws_entry.get("workspaces") or {}; ws_id=wsd.get("id"); ws_name=wsd.get("name","Unnamed"); my_role=ws_entry.get("role","member")
            with st.expander(f"🏢 {ws_name}  ({my_role})",expanded=True):
                members=get_workspace_members(ws_id)
                for m in members:
                    p=m.get("profiles") or {}; name=p.get("full_name") or p.get("email","Unknown"); email=p.get("email",""); role=m.get("role","member"); initials="".join([x[0].upper() for x in name.split()[:2]])
                    ca,cb=st.columns([4,1])
                    with ca: st.markdown(f'<div class="team-member-row"><div class="avatar">{esc(initials)}</div><div style="flex:1"><div style="font-weight:500;color:#0f172a;font-size:0.88rem;">{esc(name)}</div><div style="font-size:0.76rem;color:#6b7280;">{esc(email)}</div></div><span class="role-badge role-{esc(role)}">{esc(role)}</span></div>', unsafe_allow_html=True)
                    with cb:
                        uid=p.get("id")
                        if my_role in ("owner","admin") and uid and uid!=user["id"]:
                            if st.button("Remove",key=f"rm_{ws_id}_{uid}"): remove_member(ws_id,uid); st.rerun()
                if my_role in ("owner","admin"):
                    st.markdown("---"); i1,i2,i3=st.columns([3,1,1])
                    with i1: inv_email=st.text_input("Invite by email",key=f"inv_{ws_id}",placeholder="engineer@company.com",label_visibility="collapsed")
                    with i2: inv_role=st.selectbox("Role",["member","admin","viewer"],key=f"invr_{ws_id}",label_visibility="collapsed")
                    with i3:
                        if st.button("Invite",key=f"invbtn_{ws_id}",type="primary"):
                            try: invite_member(ws_id,user["id"],inv_email,inv_role); st.success(f"Invited {inv_email}!"); st.rerun()
                            except ValueError as e: st.error(str(e))

# PAGE: BILLING
elif page == "💳 Billing":
    render_pricing_page(user["id"],profile.get("email",""),plan)
    st.markdown("---"); st.markdown("### Your Usage"); stats=get_usage_stats(user["id"])
    bc1,bc2,bc3=st.columns(3); bc1.metric("This Month",stats.get("analyses_this_month",0)); bc2.metric("All Time",stats.get("analyses_total",0))
    lim=stats.get("limit_this_month",5); bc3.metric("Monthly Limit",lim if lim<99999 else "∞")

# PAGE: ACCOUNT
elif page == "⚙ Account":
    st.markdown("## Account Settings"); ac1,ac2=st.columns(2)
    with ac1:
        st.markdown("### Profile")
        new_name=st.text_input("Full Name",value=profile.get("full_name") or ""); new_company=st.text_input("Company",value=profile.get("company") or ""); st.text_input("Email",value=profile.get("email",""),disabled=True)
        if st.button("Save Profile",type="primary"): update_profile(user["id"],{"full_name":new_name,"company":new_company}); refresh_profile(); st.success("Profile updated!")
        st.markdown("### Analysis Defaults")
        pref_disc=st.selectbox("Default Discipline",DISCIPLINES,index=DISCIPLINES.index(st.session_state["pref_discipline"]) if st.session_state["pref_discipline"] in DISCIPLINES else 1)
        pref_detail=st.select_slider("Default Detail Level",DETAIL_LEVELS,value=st.session_state["pref_detail"])
        if st.button("Save Defaults"): st.session_state["pref_discipline"]=pref_disc; st.session_state["pref_detail"]=pref_detail; st.success("Saved!")
    with ac2:
        st.markdown("### Current Plan"); lim=get_plan_limits(plan)
        st.markdown(f"**Plan:** {plan.title()}"); st.markdown(f"**Analyses:** {profile.get('analyses_this_month',0)} / {lim['analyses_per_month']} this month"); st.markdown(f"**Batch size:** {lim['batch_size']} drawings"); st.markdown(f"**PDF:** {'✓' if lim['pdf'] else '✗'}"); st.markdown(f"**Team:** {'✓' if lim['team'] else '✗'}"); st.markdown(f"**Export:** {'✓' if lim['export'] else '✗'}")
        st.markdown("### API Keys"); st.info("🔒 Managed via Streamlit Secrets — never stored in database.")
    st.markdown("---"); st.markdown("### Danger Zone")
    with st.expander("Delete Account"):
        st.error("Permanently deletes account and all analyses.")
        if st.text_input("Type DELETE to confirm")=="DELETE":
            if st.button("Delete My Account",type="primary"): st.warning("Contact support@drawingiq.com to complete deletion.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: QUOTES PORTAL
# ─────────────────────────────────────────────────────────────────────────────
elif page == "💰 Quotes":
    st.markdown("## 💰 Quote Portal")
    st.caption("Manage sent quotes. Share approval links with customers.")

    qt1, qt2 = st.columns([3,1])
    with qt2:
        if st.button("↩ Back to Analyze", use_container_width=True):
            st.session_state["force_page"] = "📤 Analyze"; st.rerun()

    try:
        quotes = get_quotes(user["id"])
    except Exception:
        quotes = []
        st.warning("Quote table not set up yet. Run the SQL migration in Supabase first.")

    if not quotes:
        st.markdown('<div class="empty-state"><div class="icon">💰</div><h3>No quotes sent yet</h3><p>Generate a quote from any analysis and send it to your customer.</p></div>', unsafe_allow_html=True)
    else:
        status_colors = {"pending":"#d97706","approved":"#16a34a","declined":"#dc2626","revised":"#2563eb"}
        for q in quotes:
            sc = status_colors.get(q.get("status","pending"),"#6b7280")
            qd = q.get("quote_data") or {}
            qc1, qc2, qc3 = st.columns([4,1,1])
            with qc1:
                st.markdown(f"""
                <div class="history-card">
                  <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">
                    <strong style="color:#0f172a;">{esc(q.get("quote_number","N/A"))}</strong>
                    <span style="background:{sc}20;color:{sc};font-size:0.72rem;font-weight:600;padding:2px 8px;border-radius:4px;">{esc(q.get("status","pending").upper())}</span>
                    <span style="margin-left:auto;font-size:0.75rem;color:#9ca3af;">{esc(str(q.get("created_at",""))[:10])}</span>
                  </div>
                  <div style="font-size:0.78rem;color:#6b7280;margin-top:4px;display:flex;gap:1rem;flex-wrap:wrap;">
                    <span>👤 {esc(q.get("customer_name","Unknown"))}</span>
                    <span>✉️ {esc(q.get("customer_email",""))}</span>
                    <span>💵 ${qd.get("price_per_part",0):,.2f}/part · {qd.get("quantity",1)} pcs · ${qd.get("total_job_cost",0):,.2f} total</span>
                  </div>
                  {('<div style="font-size:0.78rem;color:#374151;margin-top:4px;background:#f8faff;padding:4px 8px;border-radius:4px;">Customer note: ' + esc(q.get("message","")) + '</div>') if q.get("message") else ""}
                </div>""", unsafe_allow_html=True)
            with qc2:
                app_url = os.getenv("APP_URL","https://drawingiq.streamlit.app")
                link = f"{app_url}?quote_token={q.get('token','')}"
                st.markdown(f"[🔗 Share Link]({link})")
            with qc3:
                if st.button("🗑", key=f"delq_{q['id']}"):
                    st.info("Delete quotes via Supabase dashboard.")
        
        st.markdown("---")
        st.markdown("### Quote Analytics")
        total_val  = sum((q.get("quote_data") or {}).get("total_job_cost",0) for q in quotes)
        approved   = [q for q in quotes if q.get("status")=="approved"]
        pending    = [q for q in quotes if q.get("status")=="pending"]
        win_rate   = round(len(approved)/len(quotes)*100) if quotes else 0
        qa1,qa2,qa3,qa4 = st.columns(4)
        qa1.metric("Total Quoted",  f"${total_val:,.0f}")
        qa2.metric("Quotes Sent",   len(quotes))
        qa3.metric("Approved",      len(approved))
        qa4.metric("Win Rate",      f"{win_rate}%")

    # ── Check for approval token in URL ──────────────────────────────────────
    params = st.query_params
    if "quote_token" in params:
        token  = params["quote_token"]
        try:
            qrec = get_quote_by_token(token)
        except Exception:
            qrec = None
        if qrec:
            qd = qrec.get("quote_data") or {}
            st.markdown("---")
            st.markdown("## 📋 Quote Approval")
            st.markdown(f"""
            <div style="background:white;border:1px solid #dbeafe;border-radius:12px;padding:2rem;max-width:600px;margin:0 auto;">
              <h3 style="color:#1d4ed8;margin:0 0 1rem;">Quote #{esc(qrec.get("quote_number",""))}</h3>
              <p style="color:#374151;">Dear <strong>{esc(qrec.get("customer_name",""))}</strong>,</p>
              <p style="color:#374151;">Please review the quote below and approve or request changes.</p>
              <div style="background:#f8faff;border-radius:8px;padding:1rem;margin:1rem 0;">
                <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:0.9rem;"><span style="color:#6b7280;">Quantity</span><strong>{qd.get("quantity",1)} pcs</strong></div>
                <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:0.9rem;"><span style="color:#6b7280;">Price Per Part</span><strong>${qd.get("price_per_part",0):,.2f}</strong></div>
                <div style="display:flex;justify-content:space-between;padding:4px 0;font-size:1rem;border-top:1px solid #dbeafe;margin-top:4px;"><span style="color:#1d4ed8;font-weight:700;">Total</span><strong style="color:#1d4ed8;font-size:1.2rem;">${qd.get("total_job_cost",0):,.2f}</strong></div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            cust_msg = st.text_area("Message to shop (optional)", key="cust_msg")
            ca1,ca2 = st.columns(2)
            with ca1:
                if st.button("✅ Approve Quote", type="primary", use_container_width=True):
                    update_quote_status(qrec["id"], "approved", cust_msg)
                    st.success("Quote approved! The shop has been notified.")
                    st.balloons()
            with ca2:
                if st.button("✏️ Request Changes", use_container_width=True):
                    update_quote_status(qrec["id"], "revised", cust_msg)
                    st.info("Change request sent to the shop.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: FAI REPORTS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🔬 FAI Reports":
    st.markdown("## 🔬 First Article Inspection (FAI)")
    st.caption("Enter actual measured dimensions after machining. App compares to drawing callouts and generates an AS9102-style FAI report.")

    with st.spinner("Loading analyses…"):
        analyses = get_analyses(user["id"], limit=100, workspace_id=workspace_id)

    if not analyses:
        st.info("No analyses yet. Upload a drawing first.")
    else:
        fa1, fa2 = st.columns([3,1])
        with fa1:
            options = {f'{a.get("filename","")!s} — P/N: {a.get("part_number","?") or "?"} — {str(a.get("created_at",""))[:10]}': a["id"] for a in analyses}
            sel_fai = st.selectbox("Select Drawing", list(options.keys()), key="fai_sel")
        with fa2:
            inspector = st.text_input("Inspector Name", key="fai_inspector")

        job_num_fai = st.text_input("Job / Work Order #", key="fai_job")

        record = get_analysis_by_id(options[sel_fai])
        if record:
            result  = record["result_json"]
            dims    = result.get("dimensions", [])

            if not dims:
                st.warning("No dimensions extracted from this drawing. Run a Deep Review analysis for best FAI results.")
            else:
                st.markdown("---")
                st.markdown("### Enter Actual Measurements")
                st.caption("Enter the actual measured value for each dimension. App will compare to nominal and flag out-of-tolerance features.")

                measurements = []
                for i, d in enumerate(dims):
                    nominal   = d.get("value","")
                    tol       = d.get("tolerance","")
                    unit      = d.get("unit","")
                    feature   = d.get("feature","")
                    is_crit   = d.get("is_critical", False)

                    mc1, mc2, mc3, mc4 = st.columns([3,2,2,1])
                    with mc1:
                        st.markdown(f"{'🔴 ' if is_crit else ''}`{esc(feature)}` — Nominal: **{esc(nominal)} {esc(unit)}** ±{esc(tol) if tol else 'N/A'}")
                    with mc2:
                        actual_val = st.text_input("Actual", key=f"fai_act_{i}", placeholder=nominal, label_visibility="collapsed")
                    with mc3:
                        fai_note = st.text_input("Note", key=f"fai_note_{i}", placeholder="Tool wear, fixture...", label_visibility="collapsed")
                    with mc4:
                        # Auto-determine pass/fail if we can parse numbers
                        status = "pending"
                        if actual_val:
                            try:
                                act_f  = float(actual_val)
                                nom_f  = float(str(nominal).replace("Ø","").replace("R","").strip())
                                tol_f  = float(str(tol).replace("±","").replace("+/-","").strip()) if tol else 0.1
                                status = "pass" if abs(act_f - nom_f) <= tol_f else "fail"
                                icon   = "✅" if status=="pass" else "❌"
                                st.markdown(f"<div style='padding-top:1.8rem;font-size:1.2rem;'>{icon}</div>", unsafe_allow_html=True)
                            except Exception:
                                status = "pending"
                    measurements.append({
                        "feature":  feature,
                        "nominal":  nominal,
                        "tolerance":tol,
                        "unit":     unit,
                        "actual":   actual_val,
                        "status":   status,
                        "note":     fai_note,
                        "critical": is_crit,
                    })

                st.markdown("---")
                if st.button("📋 Generate FAI Report", type="primary", use_container_width=True):
                    filled = [m for m in measurements if m.get("actual","").strip()]
                    if not filled:
                        st.error("Enter at least one actual measurement.")
                    else:
                        try:
                            fai_rec = save_fai(options[sel_fai], user["id"], measurements, inspector, job_num_fai)
                        except Exception:
                            fai_rec = {"id":"local"}

                        passed_m = [m for m in measurements if m.get("status")=="pass"]
                        failed_m = [m for m in measurements if m.get("status")=="fail"]
                        skip_m   = [m for m in measurements if m.get("status")=="pending"]

                        if failed_m:
                            st.error(f"🔴 FAI FAILED — {len(failed_m)} dimension(s) out of tolerance.")
                        else:
                            st.success(f"🟢 FAI PASSED — All {len(passed_m)} measured dimensions within tolerance.")

                        rc1,rc2,rc3 = st.columns(3)
                        rc1.metric("Passed",  len(passed_m))
                        rc2.metric("Failed",  len(failed_m))
                        rc3.metric("Skipped", len(skip_m))

                        # Build FAI report text
                        now_fai = datetime.now().strftime("%Y-%m-%d %H:%M")
                        fai_lines = [
                            "="*65,
                            "        FIRST ARTICLE INSPECTION REPORT — DrawingIQ",
                            "="*65,
                            f"Part:         {result.get('part_name') or 'Unknown'}",
                            f"Part Number:  {result.get('part_number') or 'Unknown'}",
                            f"Revision:     {result.get('revision') or 'Unknown'}",
                            f"Material:     {result.get('material') or 'Unknown'} ({result.get('material_spec') or 'N/A'})",
                            f"Drawing File: {record['filename']}",
                            f"Job / WO #:   {job_num_fai or 'N/A'}",
                            f"Inspector:    {inspector or 'N/A'}",
                            f"Date:         {now_fai}",
                            f"Result:       {'PASS' if not failed_m else 'FAIL'}",
                            "-"*65,
                            f"{'Feature':<28} {'Nominal':<12} {'Tolerance':<12} {'Actual':<12} {'Status':<8} Note",
                            "-"*65,
                        ]
                        for m in measurements:
                            if not m.get("actual","").strip():
                                continue
                            stat_str = m.get("status","pending").upper()
                            fai_lines.append(
                                f"{str(m.get('feature','')):<28} "
                                f"{str(m.get('nominal','')):<12} "
                                f"±{str(m.get('tolerance','N/A')):<11} "
                                f"{str(m.get('actual','')):<12} "
                                f"{stat_str:<8} "
                                f"{m.get('note','')}"
                            )
                        fai_lines += ["="*65, f"OVERALL: {'PASS' if not failed_m else 'FAIL'}", "="*65,
                                      "", "Signed: ___________________  Date: ___________"]
                        fai_text = "\n".join(fai_lines)

                        st.text_area("FAI Report Preview", fai_text, height=300, key="fai_preview")
                        st.download_button("⬇ Download FAI Report (.txt)", fai_text,
                                           file_name=f"FAI_{result.get('part_number') or 'part'}_{now_fai[:10]}.txt",
                                           mime="text/plain", use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: JOB TRACKER (Actual vs Estimated)
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📈 Job Tracker":
    st.markdown("## 📈 Job Tracker — Actual vs Estimated")
    st.caption("Log actual hours and costs after each job. App learns your shop's real rates and improves future quote accuracy.")

    jt_tab1, jt_tab2 = st.tabs(["📝 Log Actual Job", "📊 Performance Report"])

    with jt_tab1:
        with st.spinner("Loading analyses…"):
            analyses = get_analyses(user["id"], limit=100, workspace_id=workspace_id)

        if not analyses:
            st.info("No analyses yet.")
        else:
            jt_options = {f'{a.get("filename","")!s} — {a.get("part_name","?") or "?"} — {str(a.get("created_at",""))[:10]}': a["id"] for a in analyses}
            sel_jt = st.selectbox("Select Completed Job", list(jt_options.keys()))

            jc1, jc2, jc3 = st.columns(3)
            with jc1:
                act_machine = st.number_input("Actual Machine Hrs", 0.0, step=0.25, key="jt_mach")
                act_labor   = st.number_input("Actual Labor Hrs",   0.0, step=0.25, key="jt_lab")
            with jc2:
                act_material= st.number_input("Actual Material Cost ($)", 0.0, step=1.0, key="jt_mat")
                act_total   = st.number_input("Actual Total Cost ($)",    0.0, step=1.0, key="jt_tot")
            with jc3:
                jt_notes = st.text_area("Notes", placeholder="Setup issues, tool changes, material delays...", key="jt_notes", height=100)

            if st.button("💾 Save Job Actuals", type="primary", use_container_width=True):
                try:
                    save_job_actual(jt_options[sel_jt], user["id"], act_machine, act_labor, act_material, act_total, jt_notes)
                    st.success("Job actuals saved! Your quote accuracy report will update.")
                except Exception as e:
                    st.error(f"Could not save: {e}")

    with jt_tab2:
        try:
            actuals = get_job_actuals(user["id"], limit=100)
        except Exception:
            actuals = []
            st.warning("Job actuals table not set up yet. Run the SQL migration.")

        if not actuals:
            st.info("No job actuals logged yet. Complete some jobs and log actuals to see your performance.")
        else:
            st.markdown("### Quote Accuracy")
            total_est  = 0.0
            total_act  = 0.0
            over_count = 0
            under_count= 0

            for a in actuals:
                analysis = a.get("analyses") or {}
                result_j = analysis.get("result_json") or {}
                # Try to get estimated total from saved quote
                est_total = a.get("actual_total",0)  # fallback
                act_t     = a.get("actual_total",0)
                total_act += act_t

            pa1,pa2,pa3 = st.columns(3)
            pa1.metric("Jobs Tracked",    len(actuals))
            pa2.metric("Total Actual $",  f"${total_act:,.0f}")
            pa3.metric("Avg Actual Hrs",  f"{sum(a.get('actual_machine_hrs',0)+a.get('actual_labor_hrs',0) for a in actuals)/max(len(actuals),1):.1f} hr")

            st.markdown("---\n### Job Log")
            for a in actuals:
                analysis = a.get("analyses") or {}
                st.markdown(f"""
                <div class="history-card">
                  <div style="font-weight:600;color:#0f172a;">{esc(analysis.get("filename","Unknown"))}</div>
                  <div style="font-size:0.8rem;color:#6b7280;margin-top:4px;display:flex;gap:1.5rem;flex-wrap:wrap;">
                    <span>⚙ Machine: {a.get("actual_machine_hrs",0):.2f} hr</span>
                    <span>👷 Labor: {a.get("actual_labor_hrs",0):.2f} hr</span>
                    <span>🧱 Material: ${a.get("actual_material_cost",0):,.2f}</span>
                    <span>💵 Total: <strong>${a.get("actual_total",0):,.2f}</strong></span>
                    {('<span style="color:#374151;">📝 ' + esc(a.get("notes","")) + '</span>') if a.get("notes") else ""}
                  </div>
                </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: SHOP SETUP (Materials + Machines)
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🔧 Shop Setup":
    st.markdown("## 🔧 Shop Setup")
    st.caption("Configure your material price library and machine capabilities. These are used to auto-fill quotes and check tolerance feasibility.")

    ss_tab1, ss_tab2 = st.tabs(["🧱 Material Library", "⚙ Machine Profiles"])

    # ── MATERIAL LIBRARY ──────────────────────────────────────────────────────
    with ss_tab1:
        st.markdown("### 🧱 Material Price Library")
        st.caption("Add your materials once. Quotes will auto-suggest the right price and density.")

        with st.expander("➕ Add New Material", expanded=False):
            mc1,mc2,mc3 = st.columns(3)
            with mc1:
                mat_name    = st.text_input("Material Name", placeholder="6061 Aluminum", key="mat_name")
                mat_spec    = st.text_input("Spec / Grade",  placeholder="ASTM B221 T6511", key="mat_spec")
            with mc2:
                mat_form    = st.text_input("Form",          placeholder="Round Bar, Sheet, Plate", key="mat_form")
                mat_price   = st.number_input("Price ($/kg)", 0.0, value=5.0, step=0.1, key="mat_price")
            with mc3:
                mat_density = st.number_input("Density (kg/m³)", 100.0, value=2700.0, step=10.0, key="mat_density",
                                              help="Al=2700 · Steel=7850 · SS=8000 · Ti=4500 · Brass=8500")
                mat_supplier= st.text_input("Supplier", placeholder="McMaster, Online Metals", key="mat_sup")
            mat_notes_inp = st.text_input("Notes", placeholder="Lead time, min order qty...", key="mat_notes")
            if st.button("💾 Save Material", type="primary", key="save_mat"):
                if mat_name:
                    try:
                        save_material(user["id"], mat_name, mat_spec, mat_form,
                                      mat_price, mat_density, mat_supplier, mat_notes_inp)
                        st.success(f"Saved {mat_name}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not save material: {e}")
                else:
                    st.error("Material name is required.")

        try:
            materials = get_materials(user["id"])
        except Exception:
            materials = []
            st.warning("Materials table not set up. Run the SQL migration in Supabase first.")

        if materials:
            st.markdown(f"**{len(materials)} material(s) in your library**")
            hc1,hc2,hc3,hc4,hc5,hc6 = st.columns([3,2,2,2,2,1])
            for h,t in zip([hc1,hc2,hc3,hc4,hc5,hc6],["Name","Spec","Form","$/kg","Density","Del"]):
                h.markdown(f"<span style='font-size:0.72rem;color:#6b7280;text-transform:uppercase;'>{t}</span>", unsafe_allow_html=True)
            for m in materials:
                mc1,mc2,mc3,mc4,mc5,mc6 = st.columns([3,2,2,2,2,1])
                mc1.markdown(f"**{esc(m.get('name',''))}**")
                mc2.markdown(f"<span style='font-size:0.82rem;color:#6b7280;'>{esc(m.get('spec','—'))}</span>", unsafe_allow_html=True)
                mc3.markdown(f"<span style='font-size:0.82rem;'>{esc(m.get('form','—'))}</span>", unsafe_allow_html=True)
                mc4.markdown(f"<span style='font-family:monospace;'>${m.get('price_per_kg',0):.2f}</span>", unsafe_allow_html=True)
                mc5.markdown(f"<span style='font-family:monospace;'>{m.get('density_kg_m3',0):.0f} kg/m³</span>", unsafe_allow_html=True)
                with mc6:
                    if st.button("🗑", key=f"delmat_{m['id']}"):
                        try:
                            delete_material(m["id"], user["id"])
                            st.rerun()
                        except Exception:
                            st.error("Could not delete.")
        else:
            st.markdown('<div class="empty-state"><div class="icon">🧱</div><h3>No materials yet</h3><p>Add your commonly used materials to speed up quoting.</p></div>', unsafe_allow_html=True)

        # Default materials quick-add
        st.markdown("---")
        with st.expander("⚡ Quick-Add Common Materials"):
            st.caption("Click to add standard materials with typical values.")
            defaults = [
                ("6061-T6 Aluminum","ASTM B221","Round Bar",4.50,2700,"Online Metals"),
                ("304 Stainless Steel","ASTM A276","Round Bar",9.20,8000,"McMaster"),
                ("4140 Steel","ASTM A108","Round Bar",3.80,7850,"Metals Depot"),
                ("1018 Mild Steel","ASTM A108","Round Bar",2.40,7850,"Local supplier"),
                ("Grade 5 Titanium","ASTM B265","Sheet",52.00,4430,"TMS Titanium"),
                ("C360 Brass","ASTM B16","Round Bar",11.50,8500,"Online Metals"),
                ("Delrin (POM)","—","Round Bar",8.00,1410,"McMaster"),
                ("HDPE","—","Sheet",3.20,950,"McMaster"),
            ]
            for d in defaults:
                dname,dspec,dform,dprice,ddens,dsup = d
                if st.button(f"+ {dname}", key=f"qadd_{dname}"):
                    try:
                        save_material(user["id"], dname, dspec, dform, dprice, ddens, dsup, "")
                        st.success(f"Added {dname}!")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    # ── MACHINE PROFILES ──────────────────────────────────────────────────────
    with ss_tab2:
        st.markdown("### ⚙ Machine Capability Profiles")
        st.caption("Enter your machines and their tolerance capabilities. App will warn you when a drawing has tighter tolerances than your machines can hold.")

        with st.expander("➕ Add New Machine", expanded=False):
            mach1,mach2,mach3 = st.columns(3)
            with mach1:
                mach_name = st.text_input("Machine Name",  placeholder="Haas VF-2", key="mach_name")
                mach_type = st.selectbox("Type", ["CNC Mill","CNC Lathe","Manual Mill","Manual Lathe",
                                                   "Surface Grinder","EDM","5-Axis","Swiss Screw","Other"], key="mach_type")
            with mach2:
                mach_tol  = st.number_input("Best Tolerance (mm)", 0.001, value=0.05, step=0.001,
                                             format="%.4f", key="mach_tol",
                                             help="Tightest tolerance this machine can reliably hold")
                mach_rate = st.number_input("Rate ($/hr)", 0.0, value=85.0, step=5.0, key="mach_rate")
            with mach3:
                mach_notes= st.text_area("Notes", placeholder="Year, controller, special fixtures...",
                                          key="mach_notes", height=80)
            if st.button("💾 Save Machine", type="primary", key="save_mach"):
                if mach_name:
                    try:
                        save_machine(user["id"], mach_name, mach_type, mach_tol, mach_rate, mach_notes)
                        st.success(f"Saved {mach_name}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not save machine: {e}")
                else:
                    st.error("Machine name is required.")

        try:
            machines = get_machines(user["id"])
        except Exception:
            machines = []
            st.warning("Machines table not set up. Run the SQL migration in Supabase first.")

        if machines:
            st.markdown(f"**{len(machines)} machine(s) configured**")
            for m in machines:
                mm1,mm2,mm3,mm4,mm5 = st.columns([3,2,2,2,1])
                mm1.markdown(f"**{esc(m.get('name',''))}** <span style='font-size:0.78rem;color:#6b7280;'>{esc(m.get('machine_type',''))}</span>", unsafe_allow_html=True)
                mm2.markdown(f"<span style='font-size:0.82rem;'>±{m.get('tolerance_mm',0):.4f} mm</span>", unsafe_allow_html=True)
                mm3.markdown(f"<span style='font-family:monospace;'>${m.get('rate_per_hr',0):.0f}/hr</span>", unsafe_allow_html=True)
                mm4.markdown(f"<span style='font-size:0.78rem;color:#6b7280;'>{esc(m.get('notes',''))}</span>", unsafe_allow_html=True)
                with mm5:
                    if st.button("🗑", key=f"delmach_{m['id']}"):
                        try:
                            delete_machine(m["id"], user["id"])
                            st.rerun()
                        except Exception:
                            st.error("Could not delete.")
        else:
            st.markdown('<div class="empty-state"><div class="icon">⚙</div><h3>No machines yet</h3><p>Add your machines to enable tolerance feasibility checks.</p></div>', unsafe_allow_html=True)


# ── PAGE: TERMS & PRIVACY ─────────────────────────────────────────────────────
elif page == "📜 Terms & Privacy":
    from auth import TERMS_TEXT
    st.markdown("## 📜 Terms of Service & Privacy Policy")
    st.caption("Last updated: May 2026")
    tc1, tc2 = st.columns(2)
    with tc1:
        st.markdown("### Terms of Service")
        st.markdown("""
        **1. Service**
        DrawingIQ provides AI-powered engineering drawing analysis. Results are reference tools only.

        **2. Accuracy**
        Always verify AI results before machining. DrawingIQ is not liable for manufacturing errors or scrapped parts.

        **3. Payment**
        Subscriptions billed monthly. Cancel anytime. No refunds for partial months.

        **4. Your Data**
        Your drawings and analyses are stored securely in our database. We never share your data with third parties.

        **5. Copyright**
        Your drawings remain your property. You grant DrawingIQ a license to process them to provide the service.

        **6. Prohibited Use**
        Do not use DrawingIQ for illegal purposes or to infringe on third-party intellectual property.

        **7. Termination**
        We reserve the right to terminate accounts that violate these terms.

        **Contact:** support@drawingiq.com
        """)
    with tc2:
        st.markdown("### Privacy Policy")
        st.markdown("""
        **What we collect:**
        - Email address and name
        - Company name
        - Uploaded engineering drawings
        - Analysis results and job data
        - Usage statistics

        **How we use it:**
        - To provide the DrawingIQ service
        - To improve AI accuracy
        - To send important service updates

        **What we never do:**
        - Sell your data to third parties
        - Share drawings with other users
        - Store your credit card numbers
        - Use your data for advertising

        **Your rights:**
        - Delete your account and all data at any time
        - Export your analysis history at any time
        - Contact us to correct any information

        **Security:**
        All data encrypted at rest and in transit.
        Hosted on Supabase (SOC 2 compliant).

        **Contact:** support@drawingiq.com
        """)
    st.markdown("---")
    st.caption("© 2026 DrawingIQ. All rights reserved. Unauthorized copying or distribution prohibited.")