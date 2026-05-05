# ⚙ DrawingIQ — Enterprise Engineering Drawing Analyzer

> AI-powered engineering drawing analysis with auth, billing, PDF support, and team workspaces.

---

## What's in this project

```
drawingiq/
├── app.py           # Main Streamlit app (all pages)
├── auth.py          # Login / signup / session management (Supabase Auth)
├── database.py      # All DB operations (Supabase Postgres)
├── billing.py       # Stripe checkout, webhooks, pricing page
├── analyzer.py      # Core AI engine (OpenAI GPT-4o)
├── pdf_utils.py     # PDF → image conversion
├── requirements.txt
├── .env.example     # Copy to .env and fill in keys
└── .streamlit/
    └── secrets.toml # For Streamlit Cloud deployment
```

---

## Setup — Step by Step

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

For PDF support on Mac:
```bash
brew install poppler
```

For PDF support on Ubuntu/Debian:
```bash
sudo apt install poppler-utils
```

---

### 2. Set up Supabase (free)

1. Go to [supabase.com](https://supabase.com) → Create new project
2. Go to **Settings → API** and copy:
   - `Project URL` → `SUPABASE_URL`
   - `anon/public key` → `SUPABASE_ANON_KEY`
3. Go to **SQL Editor** and run the entire `SCHEMA_SQL` block from `database.py`
   (copy everything between the triple-quotes)
4. Go to **Authentication → Settings** and enable Email signups

---

### 3. Set up Stripe

1. Create account at [stripe.com](https://stripe.com)
2. Go to **Products** → Create two products:
   - **DrawingIQ Starter** — $49/month recurring → copy the Price ID
   - **DrawingIQ Pro** — $149/month recurring → copy the Price ID
3. Go to **Developers → API Keys** → copy the Secret Key
4. Go to **Developers → Webhooks** → Add endpoint:
   - URL: `https://your-app.streamlit.app/webhook` (or your URL)
   - Events to listen for:
     - `checkout.session.completed`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_failed`
   - Copy the **Signing Secret**

> ⚠ **Note on Stripe webhooks with Streamlit:**
> Streamlit doesn't natively support webhook POST endpoints.
> For production, deploy a small FastAPI app alongside DrawingIQ to handle webhooks,
> OR use Stripe's **Customer Portal** for plan management and poll subscription status
> via the Stripe API instead of webhooks.
> A minimal webhook handler is included in `billing.py` — just wire it up to any Python
> web framework.

---

### 4. Configure environment

Copy `.env.example` to `.env` and fill in all values:

```bash
cp .env.example .env
```

---

### 5. Run locally

```bash
streamlit run app.py
```

---

## Deploy to Streamlit Cloud (free)

1. Push this folder to a **GitHub repo** (make sure `.env` is in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set `app.py` as the main file
4. Go to **Settings → Secrets** and paste everything from `.streamlit/secrets.toml`
5. Click **Deploy**

---

## Plan Tiers

| Feature | Free | Starter ($49/mo) | Pro ($149/mo) | Enterprise |
|---------|------|------------------|---------------|------------|
| Analyses/month | 5 | 50 | 300 | Unlimited |
| Batch size | 1 | 5 | 20 | 50 |
| PDF support | ✗ | ✓ | ✓ | ✓ |
| Export (JSON/CSV) | ✗ | ✓ | ✓ | ✓ |
| Team workspaces | ✗ | ✗ | ✓ (10 seats) | Unlimited |
| History | 7 days | 30 days | Full | Full |
| Deep Review mode | ✗ | ✗ | ✓ | ✓ |

---

## Monthly Usage Reset

Add a cron job or Supabase scheduled function to reset `analyses_this_month` on the 1st of each month:

```sql
-- Run as Supabase scheduled function (monthly)
UPDATE profiles SET analyses_this_month = 0;
```

Or in Python: call `billing.reset_monthly_usage()` from a scheduler.

---

## Next Steps to Scale

- [ ] Add a FastAPI webhook handler for Stripe
- [ ] Set up Resend/SendGrid for transactional emails (invite, receipt, limit warning)
- [ ] Add CAD file support (DXF, DWG via ezdxf)
- [ ] Build an admin dashboard to view all users and revenue
- [ ] Add SSO via Supabase (Google, Microsoft OAuth)
- [ ] Add drawing comparison (diff two versions of same part)
- [ ] Integrate with Procore / Autodesk for direct import
