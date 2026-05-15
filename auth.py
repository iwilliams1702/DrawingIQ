"""
auth.py — Authentication using Supabase Auth
Handles: signup, login, logout, password reset, session persistence in Streamlit
"""

import streamlit as st
from supabase import create_client, Client
import os
from database import get_profile, update_profile

SUPABASE_URL      = os.getenv("SUPABASE_URL")
SUPABASE_KEY      = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


def get_service_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_auth_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def init_session():
    defaults = {
        "user":          None,
        "profile":       None,
        "access_token":  None,
        "refresh_token": None,
        "auth_view":     "login",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def is_logged_in() -> bool:
    return st.session_state.get("user") is not None


def get_current_user() -> dict | None:
    return st.session_state.get("user")


def get_current_profile() -> dict | None:
    return st.session_state.get("profile")


def refresh_profile():
    user = get_current_user()
    if user:
        profile = get_profile(user["id"])
        st.session_state.profile = profile
        if profile and profile.get("full_name"):
            st.session_state.user["full_name"] = profile["full_name"]


def login(email: str, password: str) -> tuple[bool, str]:
    try:
        client = get_auth_client()
        res    = client.auth.sign_in_with_password({"email": email, "password": password})
        user    = res.user
        session = res.session
        if not user:
            return False, "Invalid email or password."
        fresh_profile = get_profile(user.id) or {}
        full_name = (
            fresh_profile.get("full_name")
            or user.user_metadata.get("full_name", "")
            or email.split("@")[0]
        )
        st.session_state.user = {
            "id":        user.id,
            "email":     user.email,
            "full_name": full_name,
        }
        st.session_state.access_token  = session.access_token
        st.session_state.refresh_token = session.refresh_token
        st.session_state.profile       = fresh_profile
        return True, f"Welcome back, {full_name}!"
    except Exception as e:
        msg = str(e)
        if "Invalid login" in msg or "invalid_credentials" in msg:
            return False, "Incorrect email or password."
        return False, f"Login error: {msg}"


def signup(email: str, password: str, full_name: str, company: str = "") -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    try:
        client = get_auth_client()
        res    = client.auth.sign_up({
            "email":    email,
            "password": password,
            "options":  {"data": {"full_name": full_name}},
        })
        user = res.user
        if not user:
            return False, "Signup failed. Please try again."
        import time
        time.sleep(1)
        try:
            get_service_client().table("profiles").upsert({
                "id":        user.id,
                "email":     email,
                "full_name": full_name,
                "company":   company,
            }).execute()
        except Exception:
            pass
        return True, "Account created! You can now log in."
    except Exception as e:
        msg = str(e)
        if "already registered" in msg.lower() or "already exists" in msg.lower():
            return False, "An account with this email already exists."
        return False, f"Signup error: {msg}"


def logout():
    try:
        client = get_auth_client()
        client.auth.sign_out()
    except Exception:
        pass
    for key in ["user", "profile", "access_token", "refresh_token"]:
        st.session_state[key] = None
    st.rerun()


def send_password_reset(email: str) -> tuple[bool, str]:
    try:
        client = get_auth_client()
        client.auth.reset_password_email(email)
        return True, "Password reset email sent. Check your inbox."
    except Exception as e:
        return False, f"Error: {str(e)}"


TERMS_TEXT = """
DRAWINGIQ TERMS OF SERVICE
Last updated: May 2026

By using DrawingIQ you agree to these terms.

1. SERVICE: DrawingIQ provides AI-powered engineering drawing analysis tools.
2. ACCURACY: AI analysis is provided as a reference tool only. Always verify results before machining.
3. LIABILITY: DrawingIQ is not liable for manufacturing errors, scrapped parts, or production losses.
4. PAYMENT: Subscriptions are billed monthly. Cancel anytime. No refunds for partial months.
5. DATA: Your drawings and analyses are stored securely. We never share your data with third parties.
6. COPYRIGHT: Your drawings remain your property. You grant DrawingIQ a license to process them.
7. PROHIBITED: Do not use DrawingIQ for illegal purposes or to infringe on third-party IP.
8. CONTACT: support@drawingiq.com
"""


# ── Shared CSS for auth pages ──────────────────────────────────────────────────
AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

[data-testid="stAppViewContainer"] {
    background: #080c14;
    min-height: 100vh;
}
[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
#MainMenu { display: none !important; }
footer { display: none !important; }
[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }

.diq-auth-wrap {
    font-family: 'DM Sans', sans-serif;
    background: #080c14;
    min-height: 100vh;
    display: flex;
    align-items: stretch;
}

/* LEFT PANEL */
.diq-left {
    flex: 1;
    background: #080c14;
    padding: 3rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
    overflow: hidden;
}

.diq-left::before {
    content: '';
    position: absolute;
    top: -200px; left: -200px;
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(37,99,235,0.12) 0%, transparent 70%);
    pointer-events: none;
}

.diq-left::after {
    content: '';
    position: absolute;
    bottom: -100px; right: -100px;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%);
    pointer-events: none;
}

.diq-logo {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 4rem;
}

.diq-logo-icon {
    width: 44px; height: 44px;
    background: linear-gradient(135deg, #1d4ed8, #4f46e5);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem;
}

.diq-logo-text {
    font-family: 'Syne', sans-serif;
    font-size: 1.4rem;
    font-weight: 800;
    color: #fff;
    letter-spacing: -0.02em;
}

.diq-logo-text span { color: #3b82f6; }

.diq-hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(37,99,235,0.12);
    border: 1px solid rgba(37,99,235,0.25);
    color: #60a5fa;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 5px 14px;
    border-radius: 100px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
}

.diq-hero-badge::before {
    content: '';
    width: 6px; height: 6px;
    background: #3b82f6;
    border-radius: 50%;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
}

.diq-hero-h1 {
    font-family: 'Syne', sans-serif;
    font-size: 3.2rem;
    font-weight: 800;
    color: #fff;
    line-height: 1.08;
    letter-spacing: -0.03em;
    margin-bottom: 1.25rem;
}

.diq-hero-h1 .accent { color: #3b82f6; }
.diq-hero-h1 .accent2 { color: #818cf8; }

.diq-hero-sub {
    font-size: 1.05rem;
    color: #64748b;
    line-height: 1.7;
    max-width: 480px;
    margin-bottom: 2.5rem;
    font-weight: 300;
}

.diq-stats {
    display: flex;
    gap: 2rem;
    margin-bottom: 3rem;
}

.diq-stat-num {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    color: #fff;
    letter-spacing: -0.02em;
}

.diq-stat-label {
    font-size: 0.75rem;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 2px;
}

.diq-features {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
}

.diq-feature-row {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.88rem;
    color: #94a3b8;
}

.diq-feature-icon {
    width: 28px; height: 28px;
    background: rgba(37,99,235,0.1);
    border: 1px solid rgba(37,99,235,0.2);
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem;
    flex-shrink: 0;
}

/* RIGHT PANEL */
.diq-right {
    width: 480px;
    background: #0d1117;
    border-left: 1px solid rgba(255,255,255,0.06);
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 3rem 2.5rem;
}

.diq-form-header {
    margin-bottom: 2rem;
}

.diq-form-title {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.02em;
    margin-bottom: 0.4rem;
}

.diq-form-sub {
    font-size: 0.85rem;
    color: #475569;
}

.diq-form-sub a {
    color: #3b82f6;
    text-decoration: none;
}

.diq-input-group {
    margin-bottom: 1rem;
}

.diq-label {
    display: block;
    font-size: 0.78rem;
    font-weight: 500;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.4rem;
}

.diq-divider {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 1.5rem 0;
    color: #1e293b;
    font-size: 0.78rem;
}

.diq-divider::before,
.diq-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: rgba(255,255,255,0.06);
}

.diq-switch-link {
    text-align: center;
    margin-top: 1.5rem;
    font-size: 0.83rem;
    color: #475569;
}

.diq-switch-link a {
    color: #3b82f6;
    text-decoration: none;
    font-weight: 500;
}

/* Streamlit widget overrides */
[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: #f1f5f9 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    padding: 0.65rem 0.9rem !important;
    transition: border-color 0.2s !important;
}

[data-testid="stTextInput"] input:focus {
    border-color: rgba(59,130,246,0.5) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
    background: rgba(255,255,255,0.06) !important;
}

[data-testid="stTextInput"] label {
    color: #64748b !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    font-family: 'DM Sans', sans-serif !important;
}

[data-testid="stCheckbox"] label {
    color: #64748b !important;
    font-size: 0.83rem !important;
    font-family: 'DM Sans', sans-serif !important;
}

[data-testid="stButton"] button {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    transition: all 0.2s !important;
}

[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #1d4ed8, #4f46e5) !important;
    border: none !important;
    font-size: 0.9rem !important;
    padding: 0.65rem !important;
    letter-spacing: 0.01em !important;
}

[data-testid="stButton"] button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(37,99,235,0.35) !important;
}

[data-testid="stButton"] button[kind="secondary"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #94a3b8 !important;
    font-size: 0.83rem !important;
}

[data-testid="stButton"] button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.08) !important;
    border-color: rgba(255,255,255,0.2) !important;
    color: #f1f5f9 !important;
}

[data-testid="stAlert"] {
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
}

/* Landing page styles */
.diq-landing {
    font-family: 'DM Sans', sans-serif;
    background: #080c14;
    min-height: 100vh;
}

.diq-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.25rem 3rem;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    position: sticky;
    top: 0;
    background: rgba(8,12,20,0.95);
    backdrop-filter: blur(20px);
    z-index: 100;
}

.diq-hero-section {
    padding: 5rem 3rem 4rem;
    max-width: 1100px;
    margin: 0 auto;
    text-align: center;
}

.diq-hero-section .diq-hero-h1 {
    font-size: 4rem;
    margin: 0 auto 1.5rem;
    max-width: 750px;
}

.diq-hero-section .diq-hero-sub {
    font-size: 1.15rem;
    margin: 0 auto 3rem;
    max-width: 580px;
    text-align: center;
}

.diq-cta-row {
    display: flex;
    gap: 1rem;
    justify-content: center;
    margin-bottom: 4rem;
}

.diq-btn-primary {
    background: linear-gradient(135deg, #1d4ed8, #4f46e5);
    color: white;
    padding: 0.85rem 2rem;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.95rem;
    border: none;
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
    transition: all 0.2s;
}

.diq-btn-secondary {
    background: rgba(255,255,255,0.06);
    color: #94a3b8;
    padding: 0.85rem 2rem;
    border-radius: 8px;
    font-weight: 500;
    font-size: 0.95rem;
    border: 1px solid rgba(255,255,255,0.1);
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
}

.diq-feature-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 16px;
    overflow: hidden;
    max-width: 1000px;
    margin: 0 auto 5rem;
}

.diq-feature-card {
    background: #0d1117;
    padding: 2rem;
    transition: background 0.2s;
}

.diq-feature-card:hover {
    background: #111827;
}

.diq-feature-card-icon {
    font-size: 1.5rem;
    margin-bottom: 1rem;
}

.diq-feature-card-title {
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 0.5rem;
}

.diq-feature-card-desc {
    font-size: 0.83rem;
    color: #475569;
    line-height: 1.6;
}

.diq-pricing-section {
    padding: 4rem 3rem;
    max-width: 900px;
    margin: 0 auto;
    text-align: center;
}

.diq-section-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.2rem;
    font-weight: 800;
    color: #f1f5f9;
    letter-spacing: -0.02em;
    margin-bottom: 0.75rem;
}

.diq-section-sub {
    font-size: 0.95rem;
    color: #475569;
    margin-bottom: 3rem;
}

.diq-pricing-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.diq-pricing-card {
    background: #0d1117;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 2rem 1.5rem;
    text-align: left;
    position: relative;
}

.diq-pricing-card.featured {
    border-color: #1d4ed8;
    background: rgba(29,78,216,0.06);
}

.diq-popular-badge {
    position: absolute;
    top: -12px;
    left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(135deg, #1d4ed8, #4f46e5);
    color: white;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 3px 14px;
    border-radius: 100px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    white-space: nowrap;
}

.diq-plan-name {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #475569;
    margin-bottom: 0.75rem;
}

.diq-plan-price {
    font-family: 'Syne', sans-serif;
    font-size: 2.5rem;
    font-weight: 800;
    color: #f1f5f9;
    letter-spacing: -0.03em;
    line-height: 1;
    margin-bottom: 0.25rem;
}

.diq-plan-period {
    font-size: 0.82rem;
    color: #475569;
    margin-bottom: 1.5rem;
}

.diq-plan-features {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
}

.diq-plan-features li {
    font-size: 0.83rem;
    color: #64748b;
    display: flex;
    align-items: flex-start;
    gap: 8px;
}

.diq-plan-features li::before {
    content: '✓';
    color: #3b82f6;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 1px;
}

.diq-footer {
    border-top: 1px solid rgba(255,255,255,0.05);
    padding: 2rem 3rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #334155;
    font-size: 0.8rem;
}

.diq-testimonial-section {
    padding: 4rem 3rem;
    max-width: 1000px;
    margin: 0 auto;
}

.diq-testimonial-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.25rem;
}

.diq-testimonial-card {
    background: #0d1117;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 1.5rem;
}

.diq-testimonial-text {
    font-size: 0.88rem;
    color: #94a3b8;
    line-height: 1.65;
    margin-bottom: 1.25rem;
    font-style: italic;
}

.diq-testimonial-author {
    font-size: 0.8rem;
    font-weight: 600;
    color: #f1f5f9;
}

.diq-testimonial-role {
    font-size: 0.75rem;
    color: #475569;
    margin-top: 2px;
}

.diq-stars {
    color: #f59e0b;
    font-size: 0.75rem;
    letter-spacing: 2px;
    margin-bottom: 0.75rem;
}
</style>
"""


def render_auth_page():
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    view = st.session_state.get("auth_view", "login")

    # Two-column layout
    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.markdown(f"""
        <div class="diq-left">
            <div class="diq-logo">
                <div class="diq-logo-icon">⚙</div>
                <div class="diq-logo-text">Drawing<span>IQ</span></div>
            </div>
            <div class="diq-hero-badge">AI-Powered Machine Shop Platform</div>
            <h1 class="diq-hero-h1">
                Read any drawing.<br>
                <span class="accent">Quote any job.</span><br>
                <span class="accent2">In 60 seconds.</span>
            </h1>
            <p class="diq-hero-sub">
                DrawingIQ extracts every dimension, tolerance, and flag from your engineering drawings — then generates professional quotes automatically. Built for machine shops that compete on speed.
            </p>
            <div class="diq-stats">
                <div>
                    <div class="diq-stat-num">2+ hrs</div>
                    <div class="diq-stat-label">Saved per job</div>
                </div>
                <div>
                    <div class="diq-stat-num">99%</div>
                    <div class="diq-stat-label">Accuracy rate</div>
                </div>
                <div>
                    <div class="diq-stat-num">60s</div>
                    <div class="diq-stat-label">Full analysis</div>
                </div>
            </div>
            <div class="diq-features">
                <div class="diq-feature-row"><div class="diq-feature-icon">📐</div>AI drawing analysis with GD&T extraction</div>
                <div class="diq-feature-row"><div class="diq-feature-icon">💰</div>Instant job cost estimates with line items</div>
                <div class="diq-feature-row"><div class="diq-feature-icon">✅</div>13-point pre-machining readiness checklist</div>
                <div class="diq-feature-row"><div class="diq-feature-icon">🔬</div>First Article Inspection (FAI) reports</div>
                <div class="diq-feature-row"><div class="diq-feature-icon">🏭</div>Production queue & job scheduling</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with right_col:
        st.markdown('<div class="diq-right">', unsafe_allow_html=True)
        if view == "login":
            _render_login()
        elif view == "signup":
            _render_signup()
        elif view == "reset":
            _render_reset()
        st.markdown('</div>', unsafe_allow_html=True)


def _render_login():
    st.markdown("""
    <div class="diq-form-header">
        <div class="diq-form-title">Welcome back</div>
        <div class="diq-form-sub">New to DrawingIQ? <a href="#">Start your free trial</a></div>
    </div>
    """, unsafe_allow_html=True)

    email    = st.text_input("Email address", key="login_email", placeholder="you@company.com")
    password = st.text_input("Password", key="login_pw", placeholder="••••••••", type="password")

    col1, col2 = st.columns([3, 2])
    with col1:
        if st.button("Sign In →", type="primary", use_container_width=True):
            if not email or not password:
                st.error("Please fill in all fields.")
            else:
                with st.spinner(""):
                    ok, msg = login(email, password)
                if ok:
                    st.rerun()
                else:
                    st.error(msg)
    with col2:
        if st.button("Forgot password?", use_container_width=True):
            st.session_state.auth_view = "reset"
            st.rerun()

    st.markdown('<div class="diq-divider">or</div>', unsafe_allow_html=True)

    if st.button("Create a free account →", use_container_width=True):
        st.session_state.auth_view = "signup"
        st.rerun()

    st.markdown("""
    <div style="margin-top:2rem;padding:1rem;background:rgba(37,99,235,0.08);border:1px solid rgba(37,99,235,0.15);border-radius:10px;font-size:0.8rem;color:#475569;text-align:center;">
        🎁 <strong style="color:#60a5fa;">30-day free trial</strong> — full Pro access, no credit card required
    </div>
    """, unsafe_allow_html=True)


def _render_signup():
    st.markdown("""
    <div class="diq-form-header">
        <div class="diq-form-title">Start for free</div>
        <div class="diq-form-sub">30-day trial · No credit card · Cancel anytime</div>
    </div>
    """, unsafe_allow_html=True)

    full_name = st.text_input("Full Name", key="su_name", placeholder="Jane Smith")
    company   = st.text_input("Company (optional)", key="su_company", placeholder="Acme Manufacturing")
    email     = st.text_input("Work Email", key="su_email", placeholder="jane@acme.com")
    password  = st.text_input("Password", key="su_pw", placeholder="Min. 8 characters", type="password")
    confirm   = st.text_input("Confirm Password", key="su_confirm", type="password")
    tos_agreed = st.checkbox("I agree to the Terms of Service and Privacy Policy", key="su_tos")

    if st.button("Create Free Account →", type="primary", use_container_width=True):
        if not all([full_name, email, password, confirm]):
            st.error("Please fill in all required fields.")
        elif password != confirm:
            st.error("Passwords don't match.")
        elif not tos_agreed:
            st.error("Please agree to the Terms of Service.")
        else:
            with st.spinner("Creating your account..."):
                ok, msg = signup(email, password, full_name, company)
            if ok:
                st.success("✅ " + msg)
            else:
                st.error(msg)

    st.markdown('<div class="diq-divider">already have an account?</div>', unsafe_allow_html=True)

    if st.button("← Back to Sign In", use_container_width=True):
        st.session_state.auth_view = "login"
        st.rerun()


def _render_reset():
    st.markdown("""
    <div class="diq-form-header">
        <div class="diq-form-title">Reset password</div>
        <div class="diq-form-sub">We'll send a reset link to your email</div>
    </div>
    """, unsafe_allow_html=True)

    email = st.text_input("Email", key="reset_email", placeholder="you@company.com")

    if st.button("Send Reset Link →", type="primary", use_container_width=True):
        if not email:
            st.error("Please enter your email.")
        else:
            ok, msg = send_password_reset(email)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    if st.button("← Back to Sign In", use_container_width=True):
        st.session_state.auth_view = "login"
        st.rerun()


def render_landing_page():
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class="diq-landing">

    <!-- NAV -->
    <div class="diq-nav">
        <div class="diq-logo">
            <div class="diq-logo-icon">⚙</div>
            <div class="diq-logo-text">Drawing<span>IQ</span></div>
        </div>
        <div style="display:flex;align-items:center;gap:2rem;">
            <a href="#" style="color:#475569;font-size:0.88rem;text-decoration:none;">Features</a>
            <a href="#" style="color:#475569;font-size:0.88rem;text-decoration:none;">Pricing</a>
            <a href="#" style="color:#475569;font-size:0.88rem;text-decoration:none;">Docs</a>
        </div>
    </div>

    <!-- HERO -->
    <div class="diq-hero-section">
        <div class="diq-hero-badge">AI-Powered Machine Shop Platform</div>
        <h1 class="diq-hero-h1">
            Read any drawing.<br>
            <span class="accent">Quote any job.</span><br>
            <span class="accent2">In 60 seconds.</span>
        </h1>
        <p class="diq-hero-sub">
            DrawingIQ uses AI to analyze engineering drawings, extract every dimension and tolerance, flag issues before you machine, and generate professional quotes automatically. Built for shops that compete on speed and precision.
        </p>
    </div>

    <!-- FEATURES -->
    <div style="max-width:1000px;margin:0 auto 5rem;padding:0 3rem;">
        <div class="diq-feature-grid">
            <div class="diq-feature-card">
                <div class="diq-feature-card-icon">📐</div>
                <div class="diq-feature-card-title">Instant Drawing Analysis</div>
                <div class="diq-feature-card-desc">Upload any engineering drawing. Get every dimension, tolerance, GD&T callout, and machinist note extracted in under 60 seconds.</div>
            </div>
            <div class="diq-feature-card">
                <div class="diq-feature-card-icon">💰</div>
                <div class="diq-feature-card-title">Automatic Job Quoting</div>
                <div class="diq-feature-card-desc">Enter your shop rates once. Get instant line-item quotes with machine cost, labor, material, overhead, and profit margin.</div>
            </div>
            <div class="diq-feature-card">
                <div class="diq-feature-card-icon">✅</div>
                <div class="diq-feature-card-title">Pre-Machining Checklist</div>
                <div class="diq-feature-card-desc">13-point readiness check before every job. Catch missing material callouts, tolerances, and title blocks automatically.</div>
            </div>
            <div class="diq-feature-card">
                <div class="diq-feature-card-icon">🔬</div>
                <div class="diq-feature-card-title">FAI Reports</div>
                <div class="diq-feature-card-desc">Enter actual measurements after machining. Auto-generate First Article Inspection reports in seconds.</div>
            </div>
            <div class="diq-feature-card">
                <div class="diq-feature-card-icon">🏭</div>
                <div class="diq-feature-card-title">Production Queue</div>
                <div class="diq-feature-card-desc">Assign verified jobs to machines. Track status from Pending to Complete. See your full shop queue in one place.</div>
            </div>
            <div class="diq-feature-card">
                <div class="diq-feature-card-icon">📈</div>
                <div class="diq-feature-card-title">Job Cost Tracking</div>
                <div class="diq-feature-card-desc">Log actual vs estimated costs. Learn which jobs are profitable and improve future quote accuracy automatically.</div>
            </div>
        </div>
    </div>

    <!-- TESTIMONIALS -->
    <div class="diq-testimonial-section">
        <div style="text-align:center;margin-bottom:2.5rem;">
            <div class="diq-section-title">Shops love DrawingIQ</div>
            <div class="diq-section-sub">Saving time and winning more quotes every day</div>
        </div>
        <div class="diq-testimonial-grid">
            <div class="diq-testimonial-card">
                <div class="diq-stars">★★★★★</div>
                <div class="diq-testimonial-text">"We used to spend 2 hours per quote. Now it takes 5 minutes. DrawingIQ paid for itself in the first week."</div>
                <div class="diq-testimonial-author">Mike R.</div>
                <div class="diq-testimonial-role">Owner, precision machine shop · Ohio</div>
            </div>
            <div class="diq-testimonial-card">
                <div class="diq-stars">★★★★★</div>
                <div class="diq-testimonial-text">"The checklist feature alone has saved us from scrapping 3 parts this month. Catches things we used to miss at setup."</div>
                <div class="diq-testimonial-author">Sarah K.</div>
                <div class="diq-testimonial-role">QC Manager · aerospace supplier</div>
            </div>
            <div class="diq-testimonial-card">
                <div class="diq-stars">★★★★★</div>
                <div class="diq-testimonial-text">"Finally a tool built for machine shops, not just engineers. The FAI reports save us hours of documentation work."</div>
                <div class="diq-testimonial-author">Dave M.</div>
                <div class="diq-testimonial-role">CNC Programmer · job shop</div>
            </div>
        </div>
    </div>

    <!-- PRICING -->
    <div class="diq-pricing-section">
        <div class="diq-section-title">Simple, honest pricing</div>
        <div class="diq-section-sub">Start free. Upgrade when you're ready. Cancel anytime.</div>
        <div class="diq-pricing-grid">
            <div class="diq-pricing-card">
                <div class="diq-plan-name">Free</div>
                <div class="diq-plan-price">$0</div>
                <div class="diq-plan-period">30-day full trial included</div>
                <ul class="diq-plan-features">
                    <li>5 analyses / month</li>
                    <li>Basic flags & dimensions</li>
                    <li>Pre-machining checklist</li>
                    <li>Job traveler download</li>
                </ul>
            </div>
            <div class="diq-pricing-card featured">
                <div class="diq-popular-badge">Most Popular</div>
                <div class="diq-plan-name" style="color:#60a5fa;">Pro</div>
                <div class="diq-plan-price">$50</div>
                <div class="diq-plan-period">per month</div>
                <ul class="diq-plan-features">
                    <li>300 analyses / month</li>
                    <li>Full quote engine</li>
                    <li>Customer quote portal</li>
                    <li>FAI report generation</li>
                    <li>Job tracker & scheduling</li>
                    <li>Machine capability checks</li>
                    <li>Team workspaces (5 seats)</li>
                    <li>PDF & CSV export</li>
                </ul>
            </div>
            <div class="diq-pricing-card">
                <div class="diq-plan-name">Shop</div>
                <div class="diq-plan-price">$150</div>
                <div class="diq-plan-period">per month</div>
                <ul class="diq-plan-features">
                    <li>Unlimited analyses</li>
                    <li>Everything in Pro</li>
                    <li>Unlimited team seats</li>
                    <li>White label quotes</li>
                    <li>API access</li>
                    <li>Priority support</li>
                </ul>
            </div>
        </div>
    </div>

    <!-- FOOTER -->
    <div class="diq-footer">
        <div class="diq-logo" style="margin-bottom:0;">
            <div class="diq-logo-icon" style="width:32px;height:32px;font-size:1rem;">⚙</div>
            <div class="diq-logo-text" style="font-size:1rem;">Drawing<span>IQ</span></div>
        </div>
        <div style="color:#1e293b;font-size:0.78rem;">© 2026 DrawingIQ · support@drawingiq.com</div>
        <div style="display:flex;gap:1.5rem;">
            <a href="#" style="color:#1e293b;text-decoration:none;font-size:0.78rem;">Terms</a>
            <a href="#" style="color:#1e293b;text-decoration:none;font-size:0.78rem;">Privacy</a>
        </div>
    </div>

    </div>
    """, unsafe_allow_html=True)

    # Auth form embedded in landing
    st.markdown("<div style='max-width:460px;margin:0 auto;padding:0 1.5rem 4rem;'>", unsafe_allow_html=True)

    view = st.session_state.get("auth_view", "login")

    st.markdown(f"""
    <div style='background:#0d1117;border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:2rem;margin-bottom:1rem;'>
        <div class="diq-form-title" style='margin-bottom:0.25rem;'>{'Sign in' if view == 'login' else 'Create account' if view == 'signup' else 'Reset password'}</div>
        <div class="diq-form-sub" style='margin-bottom:1.5rem;'>{'30-day free trial — no credit card required' if view == 'signup' else 'Welcome back to DrawingIQ'}</div>
    </div>
    """, unsafe_allow_html=True)

    if view == "login":
        _render_login()
    elif view == "signup":
        _render_signup()
    elif view == "reset":
        _render_reset()

    st.markdown("</div>", unsafe_allow_html=True)