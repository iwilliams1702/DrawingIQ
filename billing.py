"""
billing.py — Stripe integration for DrawingIQ
Handles: checkout sessions, customer portal, webhook processing, plan upgrades
"""

import os
import stripe
import streamlit as st
from database import get_profile, update_profile, get_client, PLAN_LIMITS

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PLANS = {
    "starter": {
        "name":           "Starter",
        "price":          "$50",
        "period":         "/ month",
        "stripe_price_id": os.getenv("STRIPE_PRICE_STARTER", "price_REPLACE_ME_STARTER"),
        "color":          "#0369a1",
        "features": [
            "50 analyses / month",
            "Full quote engine + customer portal",
            "Job traveler & setup sheet",
            "Pre-machining checklist",
            "PDF support",
            "CSV & JSON export",
            "Single user",
            "Email support",
        ],
    },
    "pro": {
        "name":           "Pro",
        "price":          "$150",
        "period":         "/ month",
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", "price_REPLACE_ME_PRO"),
        "color":          "#d97706",
        "highlighted":    True,
        "features": [
            "300 analyses / month",
            "Everything in Starter",
            "FAI report generation",
            "Job tracker (actual vs estimated)",
            "Machine capability profiles",
            "Material price library",
            "Repeat part detection",
            "Team workspaces (up to 5 seats)",
            "Revision comparison",
            "Priority support",
        ],
    },
    "enterprise": {
        "name":           "Enterprise",
        "price":          "Custom",
        "period":         "",
        "stripe_price_id": None,
        "color":          "#7c3aed",
        "features": [
            "Unlimited analyses",
            "Unlimited team seats",
            "White label option",
            "API access",
            "SSO / SAML",
            "Dedicated account manager",
            "SLA guarantee",
            "Custom integrations",
        ],
    },
}

FREE_PLAN = {
    "name":    "Free",
    "price":   "$0",
    "period":  "/ month",
    "features": [
        "5 analyses / month",
        "Single file upload",
        "Images only (no PDF)",
        "Basic flags & dimensions",
        "No quote engine",
        "No export",
    ],
}


def create_checkout_session(user_id: str, plan_key: str, email: str) -> str | None:
    plan = PLANS.get(plan_key)
    if not plan or not plan.get("stripe_price_id") or "REPLACE_ME" in plan["stripe_price_id"]:
        raise ValueError(
            f"Stripe not connected yet. Set STRIPE_PRICE_{plan_key.upper()} "
            f"in your Streamlit secrets after creating products in Stripe."
        )
    profile     = get_profile(user_id)
    customer_id = profile.get("stripe_customer_id") if profile else None
    params = {
        "mode":       "subscription",
        "line_items": [{"price": plan["stripe_price_id"], "quantity": 1}],
        "success_url": os.getenv("APP_URL", "https://drawingiq.streamlit.app") + "?billing=success",
        "cancel_url":  os.getenv("APP_URL", "https://drawingiq.streamlit.app") + "?billing=cancel",
        "metadata":    {"user_id": user_id, "plan": plan_key},
        "client_reference_id": user_id,
        "subscription_data":   {"metadata": {"user_id": user_id, "plan": plan_key}},
    }
    if customer_id:
        params["customer"] = customer_id
    else:
        params["customer_email"] = email
    session = stripe.checkout.Session.create(**params)
    return session.url


def create_portal_session(user_id: str) -> str | None:
    profile = get_profile(user_id)
    if not profile or not profile.get("stripe_customer_id"):
        raise ValueError("No Stripe customer found. Please upgrade first.")
    session = stripe.billing_portal.Session.create(
        customer=profile["stripe_customer_id"],
        return_url=os.getenv("APP_URL", "https://drawingiq.streamlit.app"),
    )
    return session.url


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        return {"error": "Invalid signature"}

    db    = get_client()
    etype = event["type"]
    data  = event["data"]["object"]

    if etype == "checkout.session.completed":
        user_id         = data.get("metadata", {}).get("user_id") or data.get("client_reference_id")
        plan            = data.get("metadata", {}).get("plan", "starter")
        customer_id     = data.get("customer")
        subscription_id = data.get("subscription")
        if user_id:
            update_profile(user_id, {
                "plan":                   plan,
                "stripe_customer_id":     customer_id,
                "stripe_subscription_id": subscription_id,
                "analyses_this_month":    0,
            })

    elif etype == "customer.subscription.updated":
        subscription_id = data["id"]
        status          = data["status"]
        profiles        = db.table("profiles").select("id").eq(
            "stripe_subscription_id", subscription_id
        ).execute().data
        if profiles:
            user_id = profiles[0]["id"]
            if status in ("active", "trialing"):
                price_id = data["items"]["data"][0]["price"]["id"]
                new_plan = _price_id_to_plan(price_id)
                update_profile(user_id, {"plan": new_plan})
            elif status in ("canceled", "unpaid", "past_due"):
                update_profile(user_id, {"plan": "free", "stripe_subscription_id": None})

    elif etype == "customer.subscription.deleted":
        subscription_id = data["id"]
        profiles        = db.table("profiles").select("id").eq(
            "stripe_subscription_id", subscription_id
        ).execute().data
        if profiles:
            update_profile(profiles[0]["id"], {
                "plan": "free", "stripe_subscription_id": None
            })

    return {"status": "ok", "event": etype}


def _price_id_to_plan(price_id: str) -> str:
    for plan_key, plan_data in PLANS.items():
        if plan_data.get("stripe_price_id") == price_id:
            return plan_key
    return "free"


def reset_monthly_usage():
    db = get_client()
    db.table("profiles").update({"analyses_this_month": 0}).neq("id", "none").execute()


# ─── Free tier abuse prevention ───────────────────────────────────────────────

def check_abuse_risk(email: str, profile: dict) -> dict:
    """
    Returns a risk assessment for potential free tier abuse.
    Checks: disposable email domains, account age, usage patterns.
    """
    risk    = {"level": "low", "reasons": []}
    
    # Known disposable email domains
    disposable = [
        "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
        "yopmail.com", "sharklasers.com", "guerrillamailblock.com", "grr.la",
        "guerrillamail.info", "spam4.me", "trashmail.com", "mailnull.com",
        "spamgourmet.com", "trashmail.me", "dispostable.com", "maildrop.cc",
        "fakeinbox.com", "tempinbox.com", "getairmail.com", "filzmail.com",
        "throwam.com", "discard.email", "spamhereplease.com", "mailnew.com",
        "spamex.com", "mytrashmail.com", "mt2015.com", "spamfree24.org",
        "0-mail.com", "0815.ru", "10minutemail.com", "20minutemail.com",
    ]
    domain = email.split("@")[-1].lower() if "@" in email else ""
    if domain in disposable:
        risk["level"]   = "high"
        risk["reasons"].append("Disposable email address detected.")

    # No company set (weak signal but worth noting)
    if not profile.get("company"):
        risk["reasons"].append("No company set on account.")

    # Account very new + already at limit
    from datetime import datetime, timezone
    created = profile.get("created_at", "")
    if created:
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_hours  = (datetime.now(timezone.utc) - created_dt).total_seconds() / 3600
            if age_hours < 2 and profile.get("analyses_this_month", 0) >= 4:
                risk["level"] = "high"
                risk["reasons"].append("Account hit usage limit within 2 hours of creation.")
            elif age_hours < 24:
                if risk["level"] != "high":
                    risk["level"] = "medium"
                risk["reasons"].append("Account less than 24 hours old.")
        except Exception:
            pass

    return risk


def enforce_free_limits(profile: dict, email: str) -> tuple[bool, str]:
    """
    Extra enforcement on top of normal plan limits.
    Returns (allowed, reason).
    """
    plan = profile.get("plan", "free")
    if plan != "free":
        return True, ""

    risk = check_abuse_risk(email, profile)
    if risk["level"] == "high":
        return False, (
            "Your account has been flagged for review. "
            "Please upgrade to a paid plan or contact support@drawingiq.com."
        )
    return True, ""


# ─── UI ───────────────────────────────────────────────────────────────────────

BILLING_CSS = """
<style>
.pricing-wrap {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1.25rem;
    margin: 1.5rem 0;
}
.pricing-card {
    background: white;
    border: 1.5px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0;
}
.pricing-card.highlighted {
    border-color: #f97316;
    box-shadow: 0 0 0 3px rgba(249,115,22,0.15);
}
.most-popular-badge {
    text-align: center;
    margin-bottom: 0.75rem;
}
.most-popular-badge span {
    background: #f97316;
    color: white;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 3px 12px;
    border-radius: 20px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.pc-plan-name {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
}
.pc-price {
    font-size: 2.2rem;
    font-weight: 800;
    color: #0f172a;
    line-height: 1;
    font-family: 'IBM Plex Mono', monospace;
}
.pc-period {
    font-size: 0.82rem;
    color: #6b7280;
    margin-left: 4px;
}
.pc-features {
    list-style: none;
    padding: 0;
    margin: 1rem 0 0;
}
.pc-features li {
    font-size: 0.83rem;
    color: #374151;
    padding: 4px 0;
    display: flex;
    align-items: flex-start;
    gap: 0.4rem;
    border-bottom: 1px solid #f8faff;
}
.pc-features li::before {
    content: "✓";
    color: #16a34a;
    font-weight: 700;
    flex-shrink: 0;
}
.usage-bar-bg {
    background: #f3f4f6;
    border-radius: 20px;
    height: 8px;
    margin: 0.5rem 0;
}
.usage-bar {
    background: #2563eb;
    border-radius: 20px;
    height: 8px;
    transition: width 0.4s;
}
.usage-bar.danger { background: #dc2626; }
</style>
"""


def render_pricing_page(user_id: str, email: str, current_plan: str):
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    plan_order = ["free", "starter", "pro", "enterprise"]

    st.markdown("## Upgrade DrawingIQ")
    st.caption("Upgrade or downgrade anytime. Cancel anytime. No contracts.")

    plan_list = [
        {"key": "free",       **FREE_PLAN,                              "color": "#6b7280"},
        {"key": "starter",    **{k:v for k,v in PLANS["starter"].items()}},
        {"key": "pro",        **{k:v for k,v in PLANS["pro"].items()}},
        {"key": "enterprise", **{k:v for k,v in PLANS["enterprise"].items()}},
    ]

    cols = st.columns(4)
    for col, plan in zip(cols, plan_list):
        with col:
            is_current  = plan["key"] == current_plan
            highlighted = plan.get("highlighted", False)
            color       = plan.get("color", "#6b7280")
            border      = "3px solid #f97316" if highlighted else "1px solid #dbeafe"

            popular = (
                "<div style='text-align:center;margin-bottom:8px;'>"
                "<span style='background:#f97316;color:white;font-size:0.68rem;"
                "font-weight:700;padding:3px 14px;border-radius:20px;'>MOST POPULAR</span></div>"
            ) if highlighted else ""

            feats = "".join(
                f"<div style='font-size:0.82rem;color:#374151;padding:3px 0;'>"
                f"<span style='color:#16a34a;font-weight:700;'>✓</span> {f}</div>"
                for f in plan["features"]
            )

            st.markdown(f"""<div style='background:white;border:{border};border-radius:12px;
padding:1.25rem;'>{popular}
<div style='font-size:0.78rem;font-weight:700;text-transform:uppercase;
letter-spacing:0.08em;color:{color};margin-bottom:4px;'>{plan['name']}</div>
<div style='font-size:2rem;font-weight:800;color:#0f172a;font-family:monospace;
line-height:1;margin-bottom:10px;'>{plan['price']}
<span style='font-size:0.85rem;color:#6b7280;font-weight:400;
font-family:sans-serif;margin-left:4px;'>{plan.get('period','')}</span></div>
{feats}</div>""", unsafe_allow_html=True)

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

            if is_current:
                st.success("✓ Current plan")
            elif plan["key"] == "free":
                if current_plan != "free":
                    if st.button("Downgrade", key="btn_free", use_container_width=True):
                        st.info("To cancel, use Manage Subscription below.")
            elif plan["key"] == "enterprise":
                if st.button("Contact Sales", key="btn_enterprise", use_container_width=True):
                    st.info("Email sales@drawingiq.com")
            else:
                label = "Upgrade" if plan_order.index(plan["key"]) > plan_order.index(current_plan) else "Change Plan"
                if st.button(label, key=f"btn_{plan['key']}", type="primary", use_container_width=True):
                    if not stripe_key or "REPLACE_ME" in os.getenv(f"STRIPE_PRICE_{plan['key'].upper()}", "REPLACE_ME"):
                        st.error("Payment processing coming soon. Contact support@drawingiq.com to upgrade.")
                    else:
                        try:
                            url = create_checkout_session(user_id, plan["key"], email)
                            st.markdown(f'<meta http-equiv="refresh" content="0; url={url}">', unsafe_allow_html=True)
                            st.info(f"Redirecting… [Click here if not redirected]({url})")
                        except ValueError as e:
                            st.error(str(e))

    if current_plan != "free":
        st.markdown("---")
        if st.button("⚙ Manage Subscription / Cancel"):
            if not stripe_key:
                st.error("Contact support@drawingiq.com to manage your subscription.")
            else:
                try:
                    url = create_portal_session(user_id)
                    st.markdown(f'<meta http-equiv="refresh" content="0; url={url}">', unsafe_allow_html=True)
                    st.info(f"Redirecting… [Click here]({url})")
                except ValueError as e:
                    st.error(str(e))


def render_usage_bar(used: int, limit: int, plan: str):
    pct       = min(int(used / max(limit, 1) * 100), 100)
    bar_color = "#dc2626" if pct >= 90 else "#d97706" if pct >= 70 else "#3b82f6"
    limit_str = "∞" if limit >= 99999 else str(limit)
    st.markdown(
        f"<div style='font-size:0.8rem;color:#7aa2d4;margin-bottom:4px;'>"
        f"Usage: <strong style='color:#e2e8f0;'>{used}</strong>"
        f" / <span style='color:#7aa2d4;'>{limit_str}</span> this month</div>"
        f"<div style='background:#1e3a5f;border-radius:20px;height:6px;margin-bottom:4px;'>"
        f"<div style='background:{bar_color};border-radius:20px;height:6px;width:{pct}%;'></div>"
        f"</div>",
        unsafe_allow_html=True
    )