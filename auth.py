# Copyright (c) 2026 Isaiah Williams / DrawingIQ
# All rights reserved. Unauthorized copying, modification,
# or distribution of this software is strictly prohibited.
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
        # Also keep full_name synced on the user dict so header always works
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

        # Fetch profile immediately so full_name is available right away
        profile = get_profile(user.id) or {}
        full_name = (
            profile.get("full_name")
            or user.user_metadata.get("full_name", "")
            or email.split("@")[0]   # last-resort fallback: use email prefix
        )

        st.session_state.user = {
            "id":        user.id,
            "email":     user.email,
            "full_name": full_name,
        }
        st.session_state.access_token  = session.access_token
        st.session_state.refresh_token = session.refresh_token
        st.session_state.profile       = profile

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


# ── Auth page CSS ──────────────────────────────────────────────────────────────
AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');

[data-testid="stAppViewContainer"] {
    background: #020d1f;
    background-image:
        linear-gradient(rgba(0,80,200,0.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,80,200,0.07) 1px, transparent 1px);
    background-size: 40px 40px;
}
[data-testid="stHeader"] { background: transparent; }

.auth-container {
    width: 100%; max-width: 440px; margin: 2rem auto;
    background: rgba(5, 20, 50, 0.85);
    border: 1px solid rgba(30, 100, 255, 0.3);
    border-radius: 16px; padding: 2.5rem;
    box-shadow: 0 0 60px rgba(0,80,255,0.15), 0 20px 60px rgba(0,0,0,0.5);
    backdrop-filter: blur(20px);
}

.auth-logo { text-align: center; margin-bottom: 2rem; }
.auth-logo-icon {
    width: 72px; height: 72px; margin: 0 auto 1rem;
    background: linear-gradient(135deg, #0a1628, #0d2a5e);
    border: 2px solid rgba(30,100,255,0.5); border-radius: 16px;
    display: flex; align-items: center; justify-content: center;
    font-size: 2rem; box-shadow: 0 0 20px rgba(30,100,255,0.3);
}
.auth-logo h1 {
    font-family: 'Inter', sans-serif;
    font-size: 1.8rem; font-weight: 700;
    color: #ffffff; margin: 0 0 0.25rem; letter-spacing: -0.02em;
}
.auth-logo h1 span { color: #3b82f6; }
.auth-logo .tagline {
    font-size: 0.75rem; color: #4a6fa5;
    letter-spacing: 0.15em; text-transform: uppercase; font-weight: 500;
}
.auth-logo .tagline span { color: #3b82f6; margin: 0 0.3rem; }

.auth-divider {
    text-align: center; color: #2d4a7a;
    font-size: 0.8rem; margin: 1.2rem 0; position: relative;
}
.auth-divider::before {
    content: ''; position: absolute;
    top: 50%; left: 0; right: 0; height: 1px;
    background: rgba(30,100,255,0.2); z-index: 0;
}
.auth-divider span {
    background: rgba(5,20,50,0.85);
    padding: 0 0.75rem; position: relative; z-index: 1; color: #4a6fa5;
}

[data-testid="stTextInput"] input {
    background: rgba(10,30,70,0.6) !important;
    border: 1px solid rgba(30,100,255,0.25) !important;
    border-radius: 8px !important; color: #e2e8f0 !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: rgba(59,130,246,0.7) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}
[data-testid="stTextInput"] label {
    color: #7aa2d4 !important; font-size: 0.82rem !important;
    font-weight: 500 !important;
}
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; letter-spacing: 0.02em !important;
    box-shadow: 0 4px 15px rgba(37,99,235,0.4) !important;
}
[data-testid="stButton"] button[kind="secondary"] {
    background: rgba(10,30,70,0.4) !important;
    border: 1px solid rgba(30,100,255,0.2) !important;
    color: #7aa2d4 !important; border-radius: 8px !important;
}
h4 { color: #e2e8f0 !important; font-family: 'Inter', sans-serif !important; }
[data-testid="stMarkdownContainer"] p { color: #7aa2d4 !important; }
[data-testid="stCaptionContainer"] { color: #4a6fa5 !important; }
</style>
"""


def render_auth_page():
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    view = st.session_state.get("auth_view", "login")
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown("""
    <div class="auth-logo">
        <div class="auth-logo-icon">⚙</div>
        <h1>Drawing<span>IQ</span></h1>
        <div class="tagline">Blueprints <span>·</span> Precision <span>·</span> Production</div>
    </div>
    """, unsafe_allow_html=True)
    if view == "login":
        _render_login()
    elif view == "signup":
        _render_signup()
    elif view == "reset":
        _render_reset()
    st.markdown('</div>', unsafe_allow_html=True)


def _render_login():
    st.markdown("#### Sign in to your account")
    email    = st.text_input("Email",    key="login_email", placeholder="you@company.com")
    password = st.text_input("Password", key="login_pw",    placeholder="••••••••",
                             type="password")
    col1, col2 = st.columns([3, 2])
    with col1:
        if st.button("Sign In", type="primary", use_container_width=True):
            if not email or not password:
                st.error("Please fill in all fields.")
            else:
                with st.spinner("Signing in…"):
                    ok, msg = login(email, password)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
    with col2:
        if st.button("Forgot password?", use_container_width=True):
            st.session_state.auth_view = "reset"
            st.rerun()
    st.markdown('<div class="auth-divider"><span>New to DrawingIQ?</span></div>',
                unsafe_allow_html=True)
    if st.button("Create a free account →", use_container_width=True):
        st.session_state.auth_view = "signup"
        st.rerun()


def _render_signup():
    st.markdown("#### Create your free account")
    st.caption("Free plan includes 5 analyses/month. No credit card required.")
    full_name = st.text_input("Full Name",           key="su_name",    placeholder="Jane Smith")
    company   = st.text_input("Company (optional)",  key="su_company", placeholder="Acme Manufacturing")
    email     = st.text_input("Work Email",          key="su_email",   placeholder="jane@acme.com")
    password  = st.text_input("Password",            key="su_pw",      placeholder="Min. 8 characters",
                              type="password")
    confirm   = st.text_input("Confirm Password",    key="su_confirm", type="password")

    tos_agreed = st.checkbox("I agree to the Terms of Service and Privacy Policy", key="su_tos")
    st.caption("By signing up you agree to our terms. 30-day free trial, then $50/month. Cancel anytime.")

    if st.button("Create Account", type="primary", use_container_width=True):
        if not all([full_name, email, password, confirm]):
            st.error("Please fill in all required fields.")
        elif password != confirm:
            st.error("Passwords don't match.")
        elif not tos_agreed:
            st.error("Please agree to the Terms of Service to continue.")
        else:
            with st.spinner("Creating account…"):
                ok, msg = signup(email, password, full_name, company)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.markdown('<div class="auth-divider"><span>Already have an account?</span></div>',
                unsafe_allow_html=True)
    if st.button("← Back to Sign In", use_container_width=True):
        st.session_state.auth_view = "login"
        st.rerun()


def _render_reset():
    st.markdown("#### Reset your password")
    st.caption("We'll send a reset link to your email.")
    email = st.text_input("Email", key="reset_email", placeholder="you@company.com")
    if st.button("Send Reset Link", type="primary", use_container_width=True):
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


# ── Terms of Service ──────────────────────────────────────────────────────────
TERMS_URL    = "https://app.termly.io/policy-viewer/policy.html?policyUUID=YOUR_TERMS_UUID"
PRIVACY_URL  = "https://app.termly.io/policy-viewer/policy.html?policyUUID=YOUR_PRIVACY_UUID"

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

PRIVACY POLICY SUMMARY:
- We collect: email, company name, uploaded drawings, analysis results
- We use it for: providing the service, improving accuracy
- We never: sell your data, share with advertisers, store credit card numbers
- You can: delete your account and all data at any time
"""

LANDING_CSS = """
<style>
.landing-wrap {
    min-height: 100vh;
    background: #020d1f;
    background-image: linear-gradient(rgba(0,80,200,0.06) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(0,80,200,0.06) 1px, transparent 1px);
    background-size: 40px 40px;
    padding: 0;
}
.hero {
    text-align: center;
    padding: 4rem 2rem 2rem;
    max-width: 800px;
    margin: 0 auto;
}
.hero-badge {
    display: inline-block;
    background: rgba(37,99,235,0.2);
    color: #60a5fa;
    border: 1px solid rgba(37,99,235,0.3);
    font-size: 0.75rem;
    font-weight: 600;
    padding: 4px 14px;
    border-radius: 20px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 1.5rem;
}
.hero h1 {
    font-size: 3rem;
    font-weight: 800;
    color: white;
    line-height: 1.1;
    margin-bottom: 1rem;
    letter-spacing: -0.03em;
}
.hero h1 span { color: #3b82f6; }
.hero p {
    font-size: 1.15rem;
    color: #7aa2d4;
    line-height: 1.7;
    margin-bottom: 2rem;
    max-width: 600px;
    margin-left: auto;
    margin-right: auto;
}
.feature-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    max-width: 900px;
    margin: 2rem auto;
    padding: 0 1rem;
}
.feature-card {
    background: rgba(5,20,50,0.6);
    border: 1px solid rgba(30,100,255,0.2);
    border-radius: 12px;
    padding: 1.25rem;
    text-align: left;
}
.feature-icon { font-size: 1.5rem; margin-bottom: 0.5rem; }
.feature-title { color: #e2e8f0; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.3rem; }
.feature-desc  { color: #4a6fa5; font-size: 0.8rem; line-height: 1.5; }
.social-proof {
    background: rgba(5,20,50,0.4);
    border-top: 1px solid rgba(30,100,255,0.15);
    padding: 1.5rem;
    text-align: center;
    color: #4a6fa5;
    font-size: 0.82rem;
}
</style>
"""

def render_landing_page():
    """Render marketing landing page for logged-out users."""
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    st.markdown(LANDING_CSS, unsafe_allow_html=True)

    # Hero section
    st.markdown('''
    <div class="hero">
        <div class="hero-badge">⚙ Machine Shop Intelligence</div>
        <h1>Read any drawing.<br><span>Quote any job.</span><br>In 60 seconds.</h1>
        <p>DrawingIQ uses AI to analyze engineering drawings, extract every dimension and tolerance,
           flag issues before you machine, and generate professional quotes automatically.
           Built specifically for machine shops.</p>
    </div>
    ''', unsafe_allow_html=True)

    # Feature grid
    st.markdown('''
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-icon">📐</div>
            <div class="feature-title">Instant Drawing Analysis</div>
            <div class="feature-desc">Upload any engineering drawing. Get every dimension, tolerance, flag, and machinist note extracted in seconds.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">💰</div>
            <div class="feature-title">Automatic Job Quoting</div>
            <div class="feature-desc">Enter your shop rates once. Get instant line-item quotes with machine cost, labor, material, overhead, and profit.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">✅</div>
            <div class="feature-title">Pre-Machining Checklist</div>
            <div class="feature-desc">13-point readiness check before every job. Catch missing material callouts, tolerances, and title blocks automatically.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🔬</div>
            <div class="feature-title">FAI Reports</div>
            <div class="feature-desc">Enter actual measurements after machining. Auto-generate First Article Inspection reports. Required for aerospace and defense.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">🏭</div>
            <div class="feature-title">Production Scheduling</div>
            <div class="feature-desc">Assign verified jobs to machines. Track status from Pending to Complete. See your full shop queue in one place.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">📈</div>
            <div class="feature-title">Job Cost Tracking</div>
            <div class="feature-desc">Log actual vs estimated costs after every job. Learn which jobs are profitable and improve future quotes automatically.</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # Pricing teaser
    st.markdown('''
    <div style="text-align:center;padding:1.5rem;color:#4a6fa5;font-size:0.88rem;">
        <strong style="color:#60a5fa;">Free trial — no credit card required.</strong>
        Then $50/month Starter or $150/month Pro.
        Cancel anytime.
    </div>
    ''', unsafe_allow_html=True)

    # Auth form
    st.markdown('<div style="max-width:440px;margin:0 auto;">', unsafe_allow_html=True)
    view = st.session_state.get("auth_view","login")
    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('''
    <div class="auth-logo">
        <div class="auth-logo-icon">⚙</div>
        <h1>Drawing<span>IQ</span></h1>
        <div class="tagline">Blueprints <span>·</span> Precision <span>·</span> Production</div>
    </div>
    ''', unsafe_allow_html=True)
    if view == "login":
        _render_login()
    elif view == "signup":
        _render_signup()
    elif view == "reset":
        _render_reset()
    st.markdown('</div></div>', unsafe_allow_html=True)

    # Footer
    st.markdown('''
    <div class="social-proof">
        <div style="margin-bottom:0.5rem;">
            Built for machine shops · Saves 2+ hours per job · Zero hallucinations guaranteed
        </div>
        <div>
            <a href="mailto:support@drawingiq.com" style="color:#4a6fa5;margin:0 0.5rem;">support@drawingiq.com</a>
            ·
            <a href="#" onclick="window.open('about:blank')" style="color:#4a6fa5;margin:0 0.5rem;">Terms of Service</a>
            ·
            <a href="#" style="color:#4a6fa5;margin:0 0.5rem;">Privacy Policy</a>
        </div>
    </div>
    ''', unsafe_allow_html=True)