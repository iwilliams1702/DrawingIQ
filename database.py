"""
database.py — All Supabase DB operations for DrawingIQ
Tables managed here:
  - profiles       (user metadata, plan, usage)
  - analyses       (every drawing analysis result)
  - team_members   (workspace membership)
  - workspaces     (team accounts)
"""

import os
import json
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
    plan TEXT NOT NULL DEFAULT 'free',        -- free | starter | pro | enterprise
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
    role TEXT NOT NULL DEFAULT 'member',      -- owner | admin | member | viewer
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

-- RLS Policies
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own profile" ON profiles FOR ALL USING (auth.uid() = id);
CREATE POLICY "Users see own analyses" ON analyses FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Team analyses" ON analyses FOR SELECT
    USING (workspace_id IN (
        SELECT workspace_id FROM team_members WHERE user_id = auth.uid()
    ));

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


# ─── Profile operations ─────────────────────────────────────────────────────────

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
            "analyses_total": profile["analyses_total"] + 1,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()


# ─── Plan limits ────────────────────────────────────────────────────────────────

PLAN_LIMITS = {
    "free":       {"analyses_per_month": 5,    "batch_size": 1,  "pdf": False, "team": False, "export": False},
    "starter":    {"analyses_per_month": 50,   "batch_size": 5,  "pdf": True,  "team": False, "export": True},
    "pro":        {"analyses_per_month": 300,  "batch_size": 20, "pdf": True,  "team": True,  "export": True},
    "enterprise": {"analyses_per_month": 99999,"batch_size": 50, "pdf": True,  "team": True,  "export": True},
}

def get_plan_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

def can_analyze(profile: dict) -> tuple[bool, str]:
    """Returns (allowed, reason_if_not)."""
    plan = profile.get("plan", "free")
    limits = get_plan_limits(plan)
    used = profile.get("analyses_this_month", 0)
    cap = limits["analyses_per_month"]
    if used >= cap:
        return False, f"You've used {used}/{cap} analyses this month. Upgrade to continue."
    return True, ""


# ─── Analysis operations ────────────────────────────────────────────────────────

def save_analysis(user_id: str, filename: str, result: dict,
                  file_size_kb: float = 0, analysis_mode: str = "",
                  detail_level: str = "", workspace_id: str | None = None) -> dict:
    db = get_client()
    flags = result.get("flags", [])
    record = {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "filename": filename,
        "file_size_kb": file_size_kb,
        "drawing_type": result.get("drawing_type"),
        "part_name": result.get("part_name"),
        "material": result.get("material"),
        "confidence_score": result.get("confidence_score"),
        "estimated_complexity": result.get("estimated_complexity"),
        "flag_critical_count": len([f for f in flags if f.get("severity") == "critical"]),
        "flag_warning_count":  len([f for f in flags if f.get("severity") == "warning"]),
        "flag_info_count":     len([f for f in flags if f.get("severity") == "info"]),
        "result_json": result,
        "analysis_mode": analysis_mode,
        "detail_level": detail_level,
    }
    res = db.table("analyses").insert(record).execute()
    increment_usage(user_id)
    return res.data[0] if res.data else {}

def get_analyses(user_id: str, limit: int = 50, workspace_id: str | None = None) -> list[dict]:
    db = get_client()
    query = db.table("analyses").select(
        "id, filename, drawing_type, part_name, material, confidence_score, "
        "estimated_complexity, flag_critical_count, flag_warning_count, created_at, result_json"
    ).order("created_at", desc=True).limit(limit)

    if workspace_id:
        query = query.eq("workspace_id", workspace_id)
    else:
        query = query.eq("user_id", user_id)

    return query.execute().data or []

def get_analysis_by_id(analysis_id: str) -> dict | None:
    db = get_client()
    res = db.table("analyses").select("*").eq("id", analysis_id).single().execute()
    return res.data

def delete_analysis(analysis_id: str, user_id: str) -> bool:
    db = get_client()
    res = db.table("analyses").delete().eq("id", analysis_id).eq("user_id", user_id).execute()
    return bool(res.data)


# ─── Workspace / team operations ────────────────────────────────────────────────

def create_workspace(owner_id: str, name: str) -> dict:
    db = get_client()
    ws = db.table("workspaces").insert({
        "name": name, "owner_id": owner_id
    }).execute().data[0]
    # Add owner as member
    db.table("team_members").insert({
        "workspace_id": ws["id"], "user_id": owner_id, "role": "owner"
    }).execute()
    return ws

def get_workspace(workspace_id: str) -> dict | None:
    db = get_client()
    res = db.table("workspaces").select("*").eq("id", workspace_id).single().execute()
    return res.data

def get_user_workspaces(user_id: str) -> list[dict]:
    db = get_client()
    res = db.table("team_members").select(
        "role, workspaces(id, name, plan, created_at)"
    ).eq("user_id", user_id).execute()
    return res.data or []

def get_workspace_members(workspace_id: str) -> list[dict]:
    db = get_client()
    res = db.table("team_members").select(
        "role, joined_at, profiles(id, email, full_name)"
    ).eq("workspace_id", workspace_id).execute()
    return res.data or []

def invite_member(workspace_id: str, inviter_id: str, email: str, role: str = "member") -> dict:
    """Looks up user by email and adds them to the workspace."""
    db = get_client()
    profile_res = db.table("profiles").select("id").eq("email", email).single().execute()
    if not profile_res.data:
        raise ValueError(f"No user found with email {email}. They must sign up first.")
    user_id = profile_res.data["id"]
    res = db.table("team_members").insert({
        "workspace_id": workspace_id,
        "user_id": user_id,
        "role": role,
        "invited_by": inviter_id
    }).execute()
    return res.data[0] if res.data else {}

def remove_member(workspace_id: str, user_id: str):
    db = get_client()
    db.table("team_members").delete().eq("workspace_id", workspace_id).eq("user_id", user_id).execute()


# ─── Analytics helpers ──────────────────────────────────────────────────────────

def get_usage_stats(user_id: str) -> dict:
    db = get_client()
    profile = get_profile(user_id)
    if not profile:
        return {}

    analyses = get_analyses(user_id, limit=300)
    drawing_types = {}
    for a in analyses:
        dt = a.get("drawing_type") or "Unknown"
        drawing_types[dt] = drawing_types.get(dt, 0) + 1

    return {
        "plan": profile.get("plan", "free"),
        "analyses_this_month": profile.get("analyses_this_month", 0),
        "analyses_total": profile.get("analyses_total", 0),
        "limit_this_month": get_plan_limits(profile.get("plan", "free"))["analyses_per_month"],
        "drawing_type_breakdown": drawing_types,
        "recent_count": len(analyses),
    }
