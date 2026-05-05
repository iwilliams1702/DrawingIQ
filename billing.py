"""
billing.py — Stripe integration for DrawingIQ
Handles: checkout sessions, customer portal, webhook processing, plan upgrades
"""

import os
import json
import stripe
import streamlit as st
from database import get_profile, update_profile, get_client, PLAN_LIMITS

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# ─── Pricing config (fill in your Stripe Price IDs after creating products) ────
PLANS = {
    "starter": {
        "name": "Starter",
        "price": "$49",
        "period": "/ month",
        "stripe_price_id": os.getenv("STRIPE_PRICE_STARTER", "price_REPLACE_ME_STARTER"),
        "color": "#0369a1",
        "bg": "#e0f2fe",
        "features": [
            "50 analyses / month",
            "Batch upload (5 drawings)",
            "PDF support",
            "CSV & JSON export",
            "30-day history",
            "Email support",
        ],
    },
    "pro": {
        "name": "Pro",
        "price": "$149",
        "period": "/ month",
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO", "price_REPLACE_ME_PRO"),
        "color": "#d97706",
        "bg": "#fef3c7",
        "features": [
            "300 analyses / month",
            "Batch upload (20 drawings)",
            "PDF support",
            "Team workspaces (up to 10 seats)",
            "Full history + search",
            "Priority support",
            "Deep Review mode",
        ],
        "highlighted": True,
    },
    "enterprise": {
        "name": "Enterprise",
        "price": "Custom",
        "period": "",
        "stripe_price_id": None,
        "color": "#7c3aed",
        "bg": "#ede9fe",
        "features": [
            "Unlimited analyses",
            "Unlimited batch size",
            "Unlimited team seats",
            "Dedicated account manager",
            "SSO / SAML",
            "Custom integrations",
            "SLA guarantee",
        ],
    },
}

FREE_PLAN = {
    "name": "Free",
    "price": "$0",
    "period": "/ month",
    "features": [
        "5 analyses / month",
        "Single file upload",
        "Images only (no PDF)",
        "Basic export",
        "7-day history",
    ],
}


def create_checkout_session(user_id: str, plan_key: str, email: str) -> str | None:
    """Creates a Stripe Checkout session and returns the URL."""
    plan = PLANS.get(plan_key)
    if not plan or not plan.get("stripe_price_id") or "REPLACE_ME" in plan["stripe_price_id"]:
        raise ValueError(f"Stripe Price ID for '{plan_key}' is not configured. "
                         "Set STRIPE_PRICE_STARTER / STRIPE_PRICE_PRO in your .env")

    profile = get_profile(user_id)
    customer_id = profile.get("stripe_customer_id") if profile else None

    params = {
        "mode": "subscription",
        "line_items": [{"price": plan["stripe_price_id"], "quantity": 1}],
        "success_url": os.getenv("APP_URL", "http://localhost:8501") + "?billing=success",
        "cancel_url":  os.getenv("APP_URL", "http://localhost:8501") + "?billing=cancel",
        "metadata": {"user_id": user_id, "plan": plan_key},
        "client_reference_id": user_id,
        "subscription_data": {"metadata": {"user_id": user_id, "plan": plan_key}},
    }

    if customer_id:
        params["customer"] = customer_id
    else:
        params["customer_email"] = email

    session = stripe.checkout.Session.create(**params)
    return session.url


def create_portal_session(user_id: str) -> str | None:
    """Opens Stripe Customer Portal for managing/canceling subscriptions."""
    profile = get_profile(user_id)
    if not profile or not profile.get("stripe_customer_id"):
        raise ValueError("No Stripe customer found for this user.")

    session = stripe.billing_portal.Session.create(
        customer=profile["stripe_customer_id"],
        return_url=os.getenv("APP_URL", "http://localhost:8501"),
    )
    return session.url


def handle_webhook(payload: bytes, sig_header: str) -> dict:
    """
    Process Stripe webhooks. Call this from a FastAPI/Flask endpoint or
    Streamlit route handler.

    Webhook events handled:
      - checkout.session.completed  → activate subscription
      - customer.subscription.updated → plan change
      - customer.subscription.deleted → downgrade to free
      - invoice.payment_failed       → notify user
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        return {"error": "Invalid signature"}

    db = get_client()
    etype = event["type"]
    data  = event["data"]["object"]

    if etype == "checkout.session.completed":
        user_id = data.get("metadata", {}).get("user_id") or data.get("client_reference_id")
        plan    = data.get("metadata", {}).get("plan", "starter")
        customer_id    = data.get("customer")
        subscription_id = data.get("subscription")
        if user_id:
            update_profile(user_id, {
                "plan": plan,
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "analyses_this_month": 0,  # reset on new plan
            })

    elif etype == "customer.subscription.updated":
        subscription_id = data["id"]
        status = data["status"]
        # Look up user by subscription ID
        profiles = db.table("profiles").select("id, plan").eq(
            "stripe_subscription_id", subscription_id
        ).execute().data
        if profiles:
            user_id = profiles[0]["id"]
            if status in ("active", "trialing"):
                # Get plan from price metadata if possible
                price_id = data["items"]["data"][0]["price"]["id"]
                new_plan = _price_id_to_plan(price_id)
                update_profile(user_id, {"plan": new_plan})
            elif status in ("canceled", "unpaid", "past_due"):
                update_profile(user_id, {"plan": "free", "stripe_subscription_id": None})

    elif etype == "customer.subscription.deleted":
        subscription_id = data["id"]
        profiles = db.table("profiles").select("id").eq(
            "stripe_subscription_id", subscription_id
        ).execute().data
        if profiles:
            update_profile(profiles[0]["id"], {
                "plan": "free",
                "stripe_subscription_id": None
            })

    return {"status": "ok", "event": etype}


def _price_id_to_plan(price_id: str) -> str:
    for plan_key, plan_data in PLANS.items():
        if plan_data.get("stripe_price_id") == price_id:
            return plan_key
    return "free"


def reset_monthly_usage():
    """
    Call this via a cron job on the 1st of each month.
    Resets analyses_this_month for all users.
    """
    db = get_client()
    db.table("profiles").update({"analyses_this_month": 0}).neq("id", "none").execute()


# ─── UI Components ──────────────────────────────────────────────────────────────

BILLING_CSS = """
<style>
.pricing-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1rem 0; }
.pricing-card {
    background: white;
    border: 1.5px solid #e2e6f0;
    border-radius: 12px;
    padding: 1.5rem;
}
.pricing-card.highlighted { border-color: #ff6b35; box-shadow: 0 0 0 3px rgba(255,107,53,0.1); }
.pricing-card .plan-name  { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.5rem; }
.pricing-card .price      { font-size: 2rem; font-weight: 700; color: #1a1d2e; line-height: 1; }
.pricing-card .period     { font-size: 0.85rem; color: #6b7280; }
.pricing-card .feature-list { margin: 1rem 0; padding: 0; list-style: none; }
.pricing-card .feature-list li { font-size: 0.85rem; color: #374151; padding: 3px 0; }
.pricing-card .feature-list li::before { content: "✓  "; color: #16a34a; font-weight: 700; }
.usage-bar-bg { background: #f3f4f6; border-radius: 20px; height: 8px; margin: 0.5rem 0; }
.usage-bar    { background: #ff6b35; border-radius: 20px; height: 8px; transition: width 0.4s; }
.usage-bar.danger { background: #dc2626; }
</style>
"""


def render_pricing_page(user_id: str, email: str, current_plan: str):
    """Full pricing/upgrade page."""
    st.markdown(BILLING_CSS, unsafe_allow_html=True)
    st.markdown("## Upgrade DrawingIQ")
    st.caption("Upgrade or downgrade anytime. Cancel at any time.")

    cols = st.columns(4)
    plan_order = ["free", "starter", "pro", "enterprise"]
    plan_data_list = [{"key": "free", **FREE_PLAN}] + [
        {"key": k, **PLANS[k]} for k in ["starter", "pro", "enterprise"]
    ]

    for i, (col, plan) in enumerate(zip(cols, plan_data_list)):
        with col:
            is_current = plan["key"] == current_plan
            highlighted = plan.get("highlighted", False)
            border = "border: 2px solid #ff6b35;" if highlighted else ""

            st.markdown(f"""
            <div class="pricing-card {'highlighted' if highlighted else ''}" style="{border}">
                {'<div style="text-align:center;margin-bottom:0.5rem;"><span style="background:#ff6b35;color:white;font-size:0.7rem;font-weight:700;padding:3px 10px;border-radius:20px;">MOST POPULAR</span></div>' if highlighted else ''}
                <div class="plan-name" style="color:{plan.get('color','#374151')}">{plan['name']}</div>
                <div><span class="price">{plan['price']}</span> <span class="period">{plan.get('period','')}</span></div>
                <ul class="feature-list">
                    {"".join(f"<li>{f}</li>" for f in plan['features'])}
                </ul>
            </div>
            """, unsafe_allow_html=True)

            if is_current:
                st.success("Current plan")
            elif plan["key"] == "enterprise":
                if st.button("Contact Sales", key=f"btn_{plan['key']}", use_container_width=True):
                    st.info("Email us at sales@drawingiq.com")
            elif plan["key"] == "free":
                if current_plan != "free":
                    if st.button("Downgrade", key=f"btn_{plan['key']}", use_container_width=True):
                        st.warning("To cancel, use Manage Subscription below.")
            else:
                label = "Upgrade" if i > plan_order.index(current_plan) else "Change Plan"
                if st.button(label, key=f"btn_{plan['key']}", type="primary", use_container_width=True):
                    try:
                        url = create_checkout_session(user_id, plan["key"], email)
                        st.markdown(f'<meta http-equiv="refresh" content="0; url={url}">', unsafe_allow_html=True)
                        st.info(f"Redirecting to Stripe… [Click here if not redirected]({url})")
                    except ValueError as e:
                        st.error(str(e))

    if current_plan != "free":
        st.markdown("---")
        if st.button("⚙ Manage Subscription / Cancel", use_container_width=False):
            try:
                url = create_portal_session(user_id)
                st.markdown(f'<meta http-equiv="refresh" content="0; url={url}">', unsafe_allow_html=True)
                st.info(f"Redirecting to Stripe Portal… [Click here]({url})")
            except ValueError as e:
                st.error(str(e))


def render_usage_bar(used: int, limit: int, plan: str):
    """Compact usage bar for sidebar."""
    pct = min(int(used / max(limit, 1) * 100), 100)
    color_class = "danger" if pct >= 90 else ""
    limit_str = "∞" if limit >= 99999 else str(limit)
    st.markdown(BILLING_CSS, unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size:0.8rem;color:#6b7280;margin-bottom:4px;">
        Usage: <strong style="color:#1a1d2e;">{used}</strong> / {limit_str} this month
    </div>
    <div class="usage-bar-bg">
        <div class="usage-bar {color_class}" style="width:{pct}%"></div>
    </div>
    """, unsafe_allow_html=True)
