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
                   initial_sidebar_state="expanded")

from auth import (init_session, is_logged_in, get_current_user,
                  get_current_profile, logout, render_auth_page, refresh_profile)
from database import (
    get_profile, save_analysis, get_analyses, get_analysis_by_id,
    delete_analysis, get_plan_limits, can_analyze,
    create_workspace, get_user_workspaces, get_workspace_members,
    invite_member, remove_member, get_usage_stats, PLAN_LIMITS, update_profile,
)
from billing import render_pricing_page, render_usage_bar, PLANS
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
    render_auth_page()
    st.stop()

user    = get_current_user()
profile = get_current_profile() or {}
if not profile:
    refresh_profile()
    profile = get_current_profile() or {}

plan   = profile.get("plan","free")
limits = get_plan_limits(plan)
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
    NAV = ["📤 Analyze","📊 Dashboard","📋 History","🔍 Compare","✅ Review Checklist","👥 Team","💳 Billing","⚙ Account"]
    _forced    = st.session_state.pop("force_page", None)
    _nav_index = NAV.index(_forced) if _forced in NAV else 0
    page = st.radio("Navigate", NAV, index=_nav_index, label_visibility="collapsed")
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

    tabs = st.tabs(["🚩 Flags","📐 Dimensions","🔧 Machinist Notes","📋 Specs","✅ Checklist","💰 Quote","📝 Raw Notes","🖨 Print","⬇ Export"])
    t_flags,t_dims,t_notes,t_specs,t_checklist,t_quote,t_rawnotes,t_print,t_export = tabs

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
        st.markdown("### 💰 Job Cost Estimator")
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
            qlines = ["="*62,"              SHOP QUOTE — DrawingIQ","="*62,f'Quote #:        {meta.get("quote_number") or "N/A"}',f'Date:           {now_q}',f'Delivery:       {meta.get("due_date") or "TBD"}',"-"*62,f'Customer:       {meta.get("customer_name") or "N/A"}',f'Email:          {meta.get("customer_email") or "N/A"}',"-"*62,f'Part:           {result.get("part_name") or "Unknown"}',f'Part Number:    {result.get("part_number") or "Unknown"}',f'Revision:       {result.get("revision") or "Unknown"}',f'Material:       {result.get("material") or "Unknown"}',f'Drawing File:   {filename}',"-"*62,f'Quantity:       {q["quantity"]} pcs',f'Complexity:     {q["complexity"]}',f'Machine Hrs:    {q["machine_hours_per_part"]} hr/part',f'Labor Hrs:      {q["labor_hours_per_part"]} hr/part',"-"*62,f'Machine Cost:   ${q["machine_cost"]:,.2f}',f'Labor Cost:     ${q["labor_cost"]:,.2f}',f'Material Cost:  ${q["material_cost"]:,.2f}',f'Setup Cost:     ${q["setup_cost"]:,.2f}',f'Overhead:       ${q["overhead_amount"]:,.2f}',f'Profit:         ${q["profit_amount"]:,.2f}',"="*62,f'PRICE PER PART: ${q["price_per_part"]:,.2f}',f'TOTAL JOB:      ${q["total_job_cost"]:,.2f}',"="*62,"",q["disclaimer"]]
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

    with t_print:
        st.markdown("**🖨 Job Traveler / Setup Sheet**")
        pt1,pt2 = st.columns(2)
        with pt1:
            op_name    = st.text_input("Operator Name",key=f"pt_op_{analysis_id}")
            machine_id = st.text_input("Machine / Cell",placeholder="VMC-3",key=f"pt_mc_{analysis_id}")
        with pt2:
            job_number = st.text_input("Job / Work Order #",key=f"pt_job_{analysis_id}")
            due_date_p = st.text_input("Due Date",key=f"pt_due_{analysis_id}")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = ["="*62,"       DRAWINGIQ — JOB TRAVELER / SETUP SHEET","="*62,f"File:           {filename}",f"Generated:      {now_str}",f"Job / WO #:     {job_number or 'N/A'}",f"Operator:       {op_name or 'N/A'}",f"Machine / Cell: {machine_id or 'N/A'}",f"Due Date:       {due_date_p or 'N/A'}", "-"*62,f"Part:           {result.get('part_name') or 'Unknown'}",f"Part Number:    {result.get('part_number') or 'Unknown'}",f"Revision:       {result.get('revision') or 'Unknown'}",f"Material:       {result.get('material') or 'Unknown'} ({result.get('material_spec') or 'No spec'})",f"Surface Finish: {result.get('surface_finish') or 'Unknown'}",f"Heat Treat:     {result.get('heat_treatment') or 'None'}",f"Units:          {result.get('units') or 'Unknown'}",f"Complexity:     {result.get('estimated_complexity') or 'Unknown'}",f"Confidence:     {conf}%  |  Clarity: {clarity}","-"*62,f"FLAGS — {len(critical)} critical  {len(warnings)} warnings","-"*62]
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
if page == "📤 Analyze":
    allowed,reason = can_analyze(profile)
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
                    except Exception as e:
                        st.error(friendly_error(e))
                        if st.button("↩ Retry",key=f"retry_{fname}"): st.rerun()
            refresh_profile(); profile.update(get_current_profile() or {})
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
            aid=st.session_state["viewing_analysis"]; record=get_analysis_by_id(aid,user_id=user["id"])
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
            r1=get_analysis_by_id(options[sel1],user_id=user["id"]); r2=get_analysis_by_id(options[sel2],user_id=user["id"])
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
            record=get_analysis_by_id(options[sel],user_id=user["id"])
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