import os
import json
import secrets
import hashlib
from datetime import datetime

API_KEY_FILE = "data/api_keys.json"
PLANS = {
    "enterprise": {"requests_per_day": 100000,"crops": 40, "mandis": 50},
}

def generate_api_key(company_name, plan="enterprise"):
    raw_key = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw_key.encode()).hexdigest()
    
    os.makedirs(os.path.dirname(API_KEY_FILE), exist_ok=True)
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r") as f:
            keys = json.load(f)
    else:
        keys = {}
        
    keys[hashed] = {
        "company": company_name,
        "plan": plan,
        "created_at": datetime.utcnow().isoformat(),
        "is_active": True,
        "usage_today": 0,
        "last_reset": datetime.utcnow().strftime("%Y-%m-%d"),
    }
    
    with open(API_KEY_FILE, "w") as f:
        json.dump(keys, f, indent=2)
        
    return {
        "api_key": f"km_{raw_key}",
        "plan": plan,
        "rate_limit": f"{PLANS[plan]['requests_per_day']} requests/day"
    }

if __name__ == "__main__":
    key_info = generate_api_key("KrishiMitra", "enterprise")
    print("\n" + "="*50)
    print("API KEY GENERATED")
    print("="*50)
    print(f"Company:    KrishiMitra")
    print(f"Plan:       {key_info['plan']}")
    print(f"API Key:    {key_info['api_key']}")
    print(f"Rate Limit: {key_info['rate_limit']}")
    print("="*50 + "\n")
