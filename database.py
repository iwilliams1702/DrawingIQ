# Copyright (c) 2026 Isaiah Williams / DrawingIQ
# All rights reserved. Unauthorized copying, modification,
# or distribution of this software is strictly prohibited.
"""
database.py — All Supabase DB operations for DrawingIQ
Tables managed here:
  - profiles       (user metadata, plan, usage)
  - analyses       (every drawing analysis result)
  - team_members   (workspace membership)
  - workspaces     (team accounts)
  - materials      (shop material price library)
  - machines       (shop machine capability profiles)
  - quotes         (customer quote portal)
  - job_actuals    (actual vs estimated job tracking)
  - fai_reports    (first article inspection reports)
"""

import os
import secrets
from datetime import datetime
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

_client: Client | None = None

def get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment.")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# ─── Schema (run once in Supabase SQL editor) ──────────────────────────────────
SCHEMA_SQL = """
-- Profiles (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    company TEXT,
    plan TEXT NOT NULL DEFAULT 'free',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    analyses_this_month INT NOT NULL DEFAULT 0,
    analyses_total INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Workspaces (team accounts)
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    owner_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    plan TEXT NOT NULL DEFAULT 'pro',
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Team members
CREATE TABLE IF NOT EXISTS team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member',
    invited_by UUID REFERENCES profiles(id),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, user_id)
);

-- Analyses
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE SET NULL,
    filename TEXT NOT NULL,
    file_size_kb FLOAT,
    drawing_type TEXT,
    part_name TEXT,
    part_number TEXT,
    material TEXT,
    confidence_score INT,
    estimated_complexity TEXT,
    flag_critical_count INT DEFAULT 0,
    flag_warning_count INT DEFAULT 0,
    flag_info_count INT DEFAULT 0,
    result_json JSONB NOT NULL,
    analysis_mode TEXT,
    detail_level TEXT,
    model_used TEXT DEFAULT 'gpt-4o',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Material price library
CREATE TABLE IF NOT EXISTS materials (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    spec TEXT,
    form TEXT,
    price_per_kg NUMERIC(10,4) DEFAULT 0,
    density_kg_m3 NUMERIC(10,2) DEFAULT 2700,
    supplier TEXT,
    notes TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Machine capability profiles
CREATE TABLE IF NOT EXISTS machines (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    machine_type TEXT,
    tolerance_mm NUMERIC(10,5) DEFAULT 0.05,
    rate_per_hr NUMERIC(10,2) DEFAULT 85,
    notes TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Customer quotes
CREATE TABLE IF NOT EXISTS quotes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    analysis_id UUID REFERENCES analyses(id) ON DELETE SET NULL,
    quote_number TEXT,
    customer_name TEXT,
    customer_email TEXT,
    quote_data JSONB,
    token TEXT UNIQUE,
    status TEXT DEFAULT 'pending',
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Job actuals tracking
CREATE TABLE IF NOT EXISTS job_actuals (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    actual_machine_hrs NUMERIC(8,2) DEFAULT 0,
    actual_labor_hrs NUMERIC(8,2) DEFAULT 0,
    actual_material_cost NUMERIC(10,2) DEFAULT 0,
    actual_total NUMERIC(10,2) DEFAULT 0,
    notes TEXT,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(analysis_id)
);

-- FAI reports
CREATE TABLE IF NOT EXISTS fai_reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    analysis_id UUID REFERENCES analyses(id) ON DELETE CASCADE,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    measurements JSONB,
    inspector TEXT,
    job_number TEXT,
    passed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    overall TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS Policies
ALTER TABLE profiles     ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses     ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces   ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE materials    ENABLE ROW LEVEL SECURITY;
ALTER TABLE machines     ENABLE ROW LEVEL SECURITY;
ALTER TABLE quotes       ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_actuals  ENABLE ROW LEVEL SECURITY;
ALTER TABLE fai_reports  ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own profile"   ON profiles     FOR ALL USING (auth.uid() = id);
CREATE POLICY "Users see own analyses"  ON analyses     FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Team analyses"           ON analyses     FOR SELECT
    USING (workspace_id IN (
        SELECT workspace_id FROM team_members WHERE user_id = auth.uid()
    ));
CREATE POLICY "own_materials"    ON materials    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "own_machines"     ON machines     FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "own_quotes"       ON quotes       FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "public_quote_token" ON quotes     FOR SELECT USING (true);
CREATE POLICY "own_job_actuals"  ON job_actuals  FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "own_fai_reports"  ON fai_reports  FOR ALL USING (auth.uid() = user_id);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, email, full_name)
    VALUES (NEW.id, NEW.email, NEW.raw_user_meta_data->>'full_name');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();
"""


# ─── Profile operations ────────────────────────────────────────────────────────

def get_profile(user_id: str) -> dict | None:
    db = get_client()
    res = db.table("profiles").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None

def update_profile(user_id: str, updates: dict) -> dict:
    db = get_client()
    updates["updated_at"] = datetime.utcnow().isoformat()
    res = db.table("profiles").update(updates).eq("id", user_id).execute()
    return res.data

def increment_usage(user_id: str):
    """Bump both monthly and total analysis counters."""
    db = get_client()
    profile = get_profile(user_id)
    if profile:
        db.table("profiles").update({
            "analyses_this_month": profile["analyses_this_month"] + 1,
            "analyses_total":      profile["analyses_total"] + 1,
            "updated_at":          datetime.utcnow().isoformat(),
        }).eq("id", user_id).execute()


# ─── Plan limits ───────────────────────────────────────────────────────────────

PLAN_LIMITS = {
    "free":       {"analyses_per_month": 5,     "batch_size": 1,  "pdf": False, "team": False, "export": False, "quote": False},
    "trial":      {"analyses_per_month": 300,   "batch_size": 20, "pdf": True,  "team": True,  "export": True,  "quote": True},
    "starter":    {"analyses_per_month": 50,    "batch_size": 5,  "pdf": True,  "team": False, "export": True,  "quote": True},
    "pro":        {"analyses_per_month": 300,   "batch_size": 20, "pdf": True,  "team": True,  "export": True,  "quote": True},
    "enterprise": {"analyses_per_month": 99999, "batch_size": 50, "pdf": True,  "team": True,  "export": True,  "quote": True},
}

def get_plan_limits(plan: str) -> dict:
    # Check if user is in free trial (account < 30 days old on free plan)
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

def is_in_trial(profile: dict) -> bool:
    """Returns True if user is within their 30-day free trial."""
    if profile.get("plan","free") != "free":
        return False
    created = profile.get("created_at","")
    if not created:
        return True  # No creation date = assume trial
    try:
        from datetime import timezone
        created_dt = datetime.fromisoformat(created.replace("Z","+00:00"))
        days_used  = (datetime.now(timezone.utc) - created_dt).days
        return days_used <= 30
    except Exception:
        return True

def get_effective_limits(profile: dict) -> dict:
    """Returns limits based on plan, upgrading free users in trial to trial limits."""
    plan = profile.get("plan","free")
    if plan == "free" and is_in_trial(profile):
        return PLAN_LIMITS["trial"]
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

def can_analyze(profile: dict) -> tuple[bool, str]:
    limits = get_effective_limits(profile)
    used   = profile.get("analyses_this_month", 0)
    cap    = limits["analyses_per_month"]
    if used >= cap:
        return False, f"You've used {used}/{cap} analyses this month. Upgrade to continue."
    return True, ""


# ─── Analysis operations ───────────────────────────────────────────────────────

def save_analysis(user_id: str, filename: str, result: dict,
                  file_size_kb: float = 0, analysis_mode: str = "",
                  detail_level: str = "", workspace_id: str | None = None) -> dict:
    db    = get_client()
    flags = result.get("flags", [])
    record = {
        "user_id":              user_id,
        "workspace_id":         workspace_id,
        "filename":             filename,
        "file_size_kb":         file_size_kb,
        "drawing_type":         result.get("drawing_type"),
        "part_name":            result.get("part_name"),
        "part_number":          result.get("part_number"),
        "material":             result.get("material"),
        "confidence_score":     result.get("confidence_score"),
        "estimated_complexity": result.get("estimated_complexity"),
        "flag_critical_count":  len([f for f in flags if f.get("severity") == "critical"]),
        "flag_warning_count":   len([f for f in flags if f.get("severity") == "warning"]),
        "flag_info_count":      len([f for f in flags if f.get("severity") == "info"]),
        "result_json":          result,
        "analysis_mode":        analysis_mode,
        "detail_level":         detail_level,
    }
    res = db.table("analyses").insert(record).execute()
    increment_usage(user_id)
    return res.data[0] if res.data else {}

def get_analyses(user_id: str, limit: int = 50,
                 workspace_id: str | None = None) -> list[dict]:
    db    = get_client()
    query = db.table("analyses").select(
        "id, filename, drawing_type, part_name, part_number, material, "
        "confidence_score, estimated_complexity, flag_critical_count, "
        "flag_warning_count, created_at, result_json"
    ).order("created_at", desc=True).limit(limit)
    if workspace_id:
        query = query.eq("workspace_id", workspace_id)
    else:
        query = query.eq("user_id", user_id)
    return query.execute().data or []

def get_analysis_by_id(analysis_id: str) -> dict | None:
    db  = get_client()
    res = db.table("analyses").select("*").eq("id", analysis_id).single().execute()
    return res.data

def delete_analysis(analysis_id: str, user_id: str) -> bool:
    db  = get_client()
    res = db.table("analyses").delete()\
            .eq("id", analysis_id).eq("user_id", user_id).execute()
    return bool(res.data)


# ─── Workspace / team operations ───────────────────────────────────────────────

def create_workspace(owner_id: str, name: str) -> dict:
    db = get_client()
    ws = db.table("workspaces").insert({
        "name": name, "owner_id": owner_id,
    }).execute().data[0]
    db.table("team_members").insert({
        "workspace_id": ws["id"], "user_id": owner_id, "role": "owner",
    }).execute()
    return ws

def get_workspace(workspace_id: str) -> dict | None:
    db  = get_client()
    res = db.table("workspaces").select("*").eq("id", workspace_id).single().execute()
    return res.data

def get_user_workspaces(user_id: str) -> list[dict]:
    db  = get_client()
    res = db.table("team_members").select(
        "role, workspaces(id, name, plan, created_at)"
    ).eq("user_id", user_id).execute()
    return res.data or []

def get_workspace_members(workspace_id: str) -> list[dict]:
    db  = get_client()
    res = db.table("team_members").select(
        "role, joined_at, profiles(id, email, full_name)"
    ).eq("workspace_id", workspace_id).execute()
    return res.data or []

def invite_member(workspace_id: str, inviter_id: str,
                  email: str, role: str = "member") -> dict:
    db          = get_client()
    profile_res = db.table("profiles").select("id")\
                    .eq("email", email).single().execute()
    if not profile_res.data:
        raise ValueError(f"No user found with email {email}. They must sign up first.")
    user_id = profile_res.data["id"]
    res = db.table("team_members").insert({
        "workspace_id": workspace_id,
        "user_id":      user_id,
        "role":         role,
        "invited_by":   inviter_id,
    }).execute()
    return res.data[0] if res.data else {}

def remove_member(workspace_id: str, user_id: str):
    db = get_client()
    db.table("team_members").delete()\
      .eq("workspace_id", workspace_id).eq("user_id", user_id).execute()


# ─── Analytics helpers ─────────────────────────────────────────────────────────

def get_usage_stats(user_id: str) -> dict:
    db      = get_client()
    profile = get_profile(user_id)
    if not profile:
        return {}
    analyses      = get_analyses(user_id, limit=300)
    drawing_types = {}
    for a in analyses:
        dt = a.get("drawing_type") or "Unknown"
        drawing_types[dt] = drawing_types.get(dt, 0) + 1
    return {
        "plan":                   profile.get("plan", "free"),
        "analyses_this_month":    profile.get("analyses_this_month", 0),
        "analyses_total":         profile.get("analyses_total", 0),
        "limit_this_month":       get_plan_limits(profile.get("plan","free"))["analyses_per_month"],
        "drawing_type_breakdown": drawing_types,
        "recent_count":           len(analyses),
    }


# ─── Material price library ────────────────────────────────────────────────────

def save_material(user_id: str, name: str, spec: str, form: str,
                  price_per_kg: float, density_kg_m3: float,
                  supplier: str = "", notes: str = "") -> dict:
    db  = get_client()
    res = db.table("materials").upsert({
        "user_id":       user_id,
        "name":          name,
        "spec":          spec,
        "form":          form,
        "price_per_kg":  price_per_kg,
        "density_kg_m3": density_kg_m3,
        "supplier":      supplier,
        "notes":         notes,
        "updated_at":    datetime.utcnow().isoformat(),
    }).execute()
    return res.data[0] if res.data else {}

def get_materials(user_id: str) -> list[dict]:
    db  = get_client()
    res = db.table("materials").select("*")\
            .eq("user_id", user_id).order("name").execute()
    return res.data or []

def delete_material(material_id: str, user_id: str):
    db = get_client()
    db.table("materials").delete()\
      .eq("id", material_id).eq("user_id", user_id).execute()


# ─── Machine capability profiles ───────────────────────────────────────────────

def save_machine(user_id: str, name: str, machine_type: str,
                 tolerance_mm: float, rate_per_hr: float,
                 notes: str = "") -> dict:
    db  = get_client()
    res = db.table("machines").upsert({
        "user_id":      user_id,
        "name":         name,
        "machine_type": machine_type,
        "tolerance_mm": tolerance_mm,
        "rate_per_hr":  rate_per_hr,
        "notes":        notes,
        "updated_at":   datetime.utcnow().isoformat(),
    }).execute()
    return res.data[0] if res.data else {}

def get_machines(user_id: str) -> list[dict]:
    db  = get_client()
    res = db.table("machines").select("*")\
            .eq("user_id", user_id).order("name").execute()
    return res.data or []

def delete_machine(machine_id: str, user_id: str):
    db = get_client()
    db.table("machines").delete()\
      .eq("id", machine_id).eq("user_id", user_id).execute()


# ─── Customer quote portal ─────────────────────────────────────────────────────

def save_quote(user_id: str, analysis_id: str, quote_data: dict,
               customer_name: str, customer_email: str,
               quote_number: str) -> dict:
    db    = get_client()
    token = secrets.token_urlsafe(24)
    res   = db.table("quotes").insert({
        "user_id":        user_id,
        "analysis_id":    analysis_id,
        "quote_number":   quote_number,
        "customer_name":  customer_name,
        "customer_email": customer_email,
        "quote_data":     quote_data,
        "token":          token,
        "status":         "pending",
        "created_at":     datetime.utcnow().isoformat(),
    }).execute()
    return res.data[0] if res.data else {}

def get_quotes(user_id: str) -> list[dict]:
    db  = get_client()
    res = db.table("quotes").select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True).execute()
    return res.data or []

def get_quote_by_token(token: str) -> dict | None:
    db  = get_client()
    res = db.table("quotes").select("*").eq("token", token).single().execute()
    return res.data

def update_quote_status(quote_id: str, status: str, message: str = ""):
    db = get_client()
    db.table("quotes").update({
        "status":     status,
        "message":    message,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", quote_id).execute()


# ─── Job actuals tracking (actual vs estimated) ────────────────────────────────

def save_job_actual(analysis_id: str, user_id: str,
                    actual_machine_hrs: float, actual_labor_hrs: float,
                    actual_material_cost: float, actual_total: float,
                    notes: str = "") -> dict:
    db  = get_client()
    res = db.table("job_actuals").upsert({
        "analysis_id":          analysis_id,
        "user_id":              user_id,
        "actual_machine_hrs":   actual_machine_hrs,
        "actual_labor_hrs":     actual_labor_hrs,
        "actual_material_cost": actual_material_cost,
        "actual_total":         actual_total,
        "notes":                notes,
        "updated_at":           datetime.utcnow().isoformat(),
    }).execute()
    return res.data[0] if res.data else {}

def get_job_actuals(user_id: str, limit: int = 100) -> list[dict]:
    db  = get_client()
    res = db.table("job_actuals").select(
        "*, analyses(filename, part_name, estimated_complexity, result_json)"
    ).eq("user_id", user_id)\
     .order("updated_at", desc=True).limit(limit).execute()
    return res.data or []


# ─── Repeat part detection ─────────────────────────────────────────────────────

def find_similar_parts(user_id: str, part_name: str = None,
                       part_number: str = None) -> list[dict]:
    db      = get_client()
    results = db.table("analyses").select(
        "id, filename, part_name, part_number, material, "
        "estimated_complexity, confidence_score, created_at"
    ).eq("user_id", user_id)\
     .order("created_at", desc=True).execute().data or []

    matches = []
    for r in results:
        score = 0
        if part_number and r.get("part_number"):
            if part_number.lower().strip() == r["part_number"].lower().strip():
                score += 10
        if part_name and r.get("part_name"):
            pn = part_name.lower().strip()
            rn = r["part_name"].lower().strip()
            if pn == rn:
                score += 8
            elif pn in rn or rn in pn:
                score += 4
        if score > 0:
            r["match_score"] = score
            matches.append(r)
    return sorted(matches, key=lambda x: -x["match_score"])[:5]


# ─── FAI reports ───────────────────────────────────────────────────────────────

def save_fai(analysis_id: str, user_id: str, measurements: list[dict],
             inspector: str, job_number: str) -> dict:
    db      = get_client()
    passed  = sum(1 for m in measurements if m.get("status") == "pass")
    failed  = sum(1 for m in measurements if m.get("status") == "fail")
    overall = "pass" if failed == 0 else "fail"
    res     = db.table("fai_reports").insert({
        "analysis_id":  analysis_id,
        "user_id":      user_id,
        "measurements": measurements,
        "inspector":    inspector,
        "job_number":   job_number,
        "passed_count": passed,
        "failed_count": failed,
        "overall":      overall,
        "created_at":   datetime.utcnow().isoformat(),
    }).execute()
    return res.data[0] if res.data else {}

def get_fai_reports(user_id: str, analysis_id: str = None) -> list[dict]:
    db    = get_client()
    query = db.table("fai_reports").select("*").eq("user_id", user_id)
    if analysis_id:
        query = query.eq("analysis_id", analysis_id)
    return query.order("created_at", desc=True).execute().data or []


# ─── Production Queue (persisted) ─────────────────────────────────────────────

def save_job_to_queue(user_id: str, job: dict) -> dict:
    db  = get_client()
    res = db.table("job_queue").upsert({
        "id":           job.get("id"),
        "user_id":      user_id,
        "filename":     job.get("filename",""),
        "part_name":    job.get("part_name",""),
        "part_number":  job.get("part_number",""),
        "material":     job.get("material",""),
        "machine":      job.get("machine",""),
        "operator":     job.get("operator",""),
        "job_number":   job.get("job_number",""),
        "due_date":     job.get("due_date",""),
        "priority":     job.get("priority","Normal"),
        "status":       job.get("status","Pending"),
        "notes":        job.get("notes",""),
        "complexity":   job.get("complexity","Unknown"),
        "verified_by":  job.get("verified_by",""),
        "verified_at":  job.get("verified_at",""),
        "analysis_id":  job.get("analysis_id",""),
        "updated_at":   datetime.utcnow().isoformat(),
    }).execute()
    return res.data[0] if res.data else {}

def get_job_queue(user_id: str) -> list[dict]:
    db  = get_client()
    res = db.table("job_queue").select("*")            .eq("user_id", user_id)            .neq("status", "Archived")            .order("updated_at", desc=True).execute()
    return res.data or []

def update_job_status(job_id: str, user_id: str, status: str) -> bool:
    db  = get_client()
    res = db.table("job_queue").update({
        "status":     status,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", job_id).eq("user_id", user_id).execute()
    return bool(res.data)

def delete_job_from_queue(job_id: str, user_id: str) -> bool:
    db  = get_client()
    res = db.table("job_queue").delete()            .eq("id", job_id).eq("user_id", user_id).execute()
    return bool(res.data)