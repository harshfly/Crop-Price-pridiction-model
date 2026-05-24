# ═══════════════════════════════════════════════════════════════════
# KrishiMitra AI — API Key Authentication for Commercial Use
# ═══════════════════════════════════════════════════════════════════

import os
import hashlib
import secrets
import json
from datetime import datetime
from functools import wraps
from fastapi import HTTPException, Security, Request
from fastapi.security import APIKeyHeader

API_KEY_FILE = "data/api_keys.json"
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Plans with rate limits
PLANS = {
    "free":       {"requests_per_day": 100,   "crops": 5,  "mandis": 3},
    "starter":    {"requests_per_day": 1000,  "crops": 20, "mandis": 15},
    "business":   {"requests_per_day": 10000, "crops": 40, "mandis": 50},
    "enterprise": {"requests_per_day": 100000,"crops": 40, "mandis": 50},
}


def _load_keys() -> dict:
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_keys(keys: dict):
    os.makedirs(os.path.dirname(API_KEY_FILE), exist_ok=True)
    with open(API_KEY_FILE, "w") as f:
        json.dump(keys, f, indent=2)


def generate_api_key(company_name: str, plan: str = "free") -> dict:
    """Generate a new API key for a customer."""
    raw_key = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw_key.encode()).hexdigest()

    keys = _load_keys()
    keys[hashed] = {
        "company": company_name,
        "plan": plan,
        "created_at": datetime.utcnow().isoformat(),
        "is_active": True,
        "usage_today": 0,
        "last_reset": datetime.utcnow().strftime("%Y-%m-%d"),
    }
    _save_keys(keys)

    return {
        "api_key": f"km_{raw_key}",
        "plan": plan,
        "rate_limit": f"{PLANS[plan]['requests_per_day']} requests/day",
        "message": f"API key generated for {company_name}. Keep it secret!",
    }


async def validate_api_key(request: Request, api_key: str = Security(API_KEY_HEADER)):
    """Validate API key from X-API-Key header. Returns None for public endpoints."""
    if api_key is None:
        # Allow unauthenticated access to public endpoints (free tier)
        return {"plan": "free", "company": "anonymous"}

    if not api_key.startswith("km_"):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    raw = api_key[3:]
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    keys = _load_keys()

    if hashed not in keys:
        raise HTTPException(status_code=401, detail="Invalid API key")

    info = keys[hashed]
    if not info.get("is_active", True):
        raise HTTPException(status_code=403, detail="API key deactivated")

    # Reset daily counter
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if info.get("last_reset") != today:
        info["usage_today"] = 0
        info["last_reset"] = today

    plan = info.get("plan", "free")
    limit = PLANS.get(plan, PLANS["free"])["requests_per_day"]
    if info["usage_today"] >= limit:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded ({limit}/day)")

    info["usage_today"] += 1
    keys[hashed] = info
    _save_keys(keys)

    return {"plan": plan, "company": info["company"]}
