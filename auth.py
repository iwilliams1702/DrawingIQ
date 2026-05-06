"""
auth.py — Authentication using Supabase Auth
Handles: signup, login, logout, password reset, session persistence in Streamlit
"""

import streamlit as st
from supabase import create_client, Client
import os
from database import get_profile, update_profile

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")


def get_auth_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def init_session():
    defaults = {
        "user": None,
        "profile": None,
        "access_token": None,
        "refresh_token": None,
        "auth_view": "login",
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
        st.session_state.profile = get_profile(user["id"])


def login(email: str, password: str) -> tuple[bool, str]:
    try:
        client = get_auth_client()
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        user = res.user
        session = res.session
        if not user:
            return False, "Invalid email or password."
        st.session_state.user = {"id": user.id, "email": user.email}
        st.session_state.access_token = session.access_token
        st.session_state.refresh_token = session.refresh_token
        st.session_state.profile = get_profile(user.id)
        return True, "Welcome back!"
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
        res = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name}}
        })
        user = res.user
        if not user:
            return False, "Signup failed. Please try again."

        # Manually create profile (bypasses trigger)
        import time; time.sleep(1)
        from database import get_client
        try:
            get_client().table("profiles").upsert({
                "id": user.id,
                "email": email,
                "full_name": full_name,
                "company": company,
            }).execute()
        except Exception:
            pass  # Profile may already exist

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


# ─── UI Components ──────────────────────────────────────────────────────────────

AUTH_CSS = """
<style>
.auth-container {
    max-width: 420px;
    margin: 4rem auto;
    background: white;
    border: 1px solid #e2e6f0;
    border-radius: 14px;
    padding: 2.5rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
}
.auth-logo {
    text-align: center;
    margin-bottom: 2rem;
}
.auth-logo .icon { font-size: 2.5rem; }
.auth-logo h1 { font-size: 1.6rem; font-weight: 700; color: #1a1d2e; margin: 0.5rem 0 0.25rem; }
.auth-logo p  { color: #6b7280; font-size: 0.9rem; margin: 0; }
.auth-divider { 
    text-align: center; 
    color: #9ca3af; 
    font-size: 0.8rem; 
    margin: 1.2rem 0; 
    position: relative;
}
.auth-divider::before {
    content: '';
    position: absolute;
    top: 50%; left: 0; right: 0;
    height: 1px;
    background: #e5e7eb;
    z-index: 0;
}
.auth-divider span {
    background: white;
    padding: 0 0.75rem;
    position: relative;
    z-index: 1;
}
.plan-pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
}
.plan-free       { background: #f3f4f6; color: #6b7280; }
.plan-starter    { background: #e0f2fe; color: #0369a1; }
.plan-pro        { background: #fef3c7; color: #d97706; }
.plan-enterprise { background: #ede9fe; color: #7c3aed; }
</style>
"""


def render_auth_page():
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    view = st.session_state.get("auth_view", "login")

    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown("""
    <div class="auth-logo">
        <div class="icon">⚙</div>
        <h1>DrawingIQ</h1>
        <p>Enterprise Engineering Drawing Intelligence</p>
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
    email    = st.text_input("Email", key="login_email", placeholder="you@company.com")
    password = st.text_input("Password", type="password", key="login_pw", placeholder="••••••••")

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

    st.markdown('<div class="auth-divider"><span>New to DrawingIQ?</span></div>', unsafe_allow_html=True)
    if st.button("Create a free account →", use_container_width=True):
        st.session_state.auth_view = "signup"
        st.rerun()


def _render_signup():
    st.markdown("#### Create your free account")
    st.caption("Free plan includes 5 analyses/month. No credit card required.")

    full_name = st.text_input("Full Name", key="su_name", placeholder="Jane Smith")
    company   = st.text_input("Company (optional)", key="su_company", placeholder="Acme Manufacturing")
    email     = st.text_input("Work Email", key="su_email", placeholder="jane@acme.com")
    password  = st.text_input("Password", type="password", key="su_pw", placeholder="Min. 8 characters")
    confirm   = st.text_input("Confirm Password", type="password", key="su_confirm")

    if st.button("Create Account", type="primary", use_container_width=True):
        if not all([full_name, email, password, confirm]):
            st.error("Please fill in all required fields.")
        elif password != confirm:
            st.error("Passwords don't match.")
        else:
            with st.spinner("Creating account…"):
                ok, msg = signup(email, password, full_name, company)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.markdown('<div class="auth-divider"><span>Already have an account?</span></div>', unsafe_allow_html=True)
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