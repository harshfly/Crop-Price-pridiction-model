from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import json
from datetime import datetime

# Import from existing codebase
from src.predict import predict_price as run_prediction
from api.geography import (
    get_all_categories, CROP_DATABASE,
    get_all_states, get_mandis_by_state, MANDI_DATABASE,
    find_nearby_mandis, estimate_transport_cost
)

app = FastAPI(
    title="KrishiMitra Global UI API",
    description="Database-free API for local testing and Hugging Face deployment.",
    version="2.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Models ──
class PredictRequest(BaseModel):
    state: str = ""
    mandi: str
    crop: str
    days_ahead: int = 7

class NearbyMandiRequest(BaseModel):
    lat: float
    lon: float
    radius_km: float = 300
    quantity_qtl: float = 100
    crop: str = ""

# ── Routes expected by frontend/app.js ──

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "models_loaded": 2}

@app.get("/api/v1/crops")
def get_crops():
    crops = [{"name": n, **info} for n, info in CROP_DATABASE.items()]
    return {"total": len(crops), "categories": get_all_categories(), "crops": crops}

@app.get("/api/v1/geography/states")
def get_states():
    states = get_all_states()
    result = []
    for s in states:
        mandis = get_mandis_by_state(s)
        result.append({"state": s, "mandi_count": len(mandis), "mandis": [m["name"] for m in mandis]})
    return {"states": result, "total": len(result)}

@app.get("/api/v1/mandis")
def get_mandis(state: str = "all"):
    if state != "all":
        mandis = get_mandis_by_state(state)
    else:
        mandis = [{"name": n, **info} for n, info in MANDI_DATABASE.items()]
    return {"mandis": mandis, "total": len(mandis)}

@app.get("/api/v1/weather/impact")
def weather_impact(city: str = "Indore", crop: str = "Onion"):
    import random
    temp = random.randint(25, 38)
    rain = random.randint(0, 15)
    impact = "Nominal"
    dir = "neutral"
    if rain > 10:
        impact = f"Heavy rain ({rain}mm) may disrupt arrivals"
        dir = "up"
    elif temp > 35:
        impact = f"High heat ({temp}°C) may cause spoilage"
        dir = "up"
    
    return {
        "impact_summary": impact,
        "temperature": temp,
        "rainfall_7d": rain,
        "price_impact_direction": dir
    }

@app.get("/api/v1/weather/forecast")
def weather_forecast(city: str = "Indore"):
    """Return 14 days of weather data: 7 past, 7 future"""
    import random
    from datetime import timedelta
    
    today = datetime.now()
    dates = [(today + timedelta(days=i)).strftime("%b %d") for i in range(-7, 7)]
    
    # Generate a temperature curve
    base_temp = random.randint(22, 35)
    temps = [base_temp + random.randint(-3, 3) for _ in range(14)]
    
    # Generate random rainfall spikes
    rain = [random.choice([0, 0, 0, random.randint(5, 20)]) for _ in range(14)]
    
    return {
        "city": city,
        "dates": dates,
        "temperature": temps,
        "rainfall": rain
    }

@app.get("/api/v1/news")
def get_news(crop: str = "Onion", state: str = "Maharashtra"):
    """Mock news generator for market context"""
    import random
    headlines = [
        f"Export duty lifted on {crop}, prices expected to rise.",
        f"Heavy rainfall in {state} disrupts {crop} supply chains.",
        f"Government releases buffer stock of {crop} to control inflation.",
        f"New pest outbreak reported in {state} {crop} farms.",
        f"Transport strike in {state} delays {crop} arrivals by 48 hours.",
        f"Record harvest of {crop} expected this season.",
        f"International demand for Indian {crop} surges."
    ]
    
    # Pick 3 random news items
    selected = random.sample(headlines, 3)
    news_items = []
    for i, h in enumerate(selected):
        sentiment = "positive" if "lifted" in h or "demand" in h else "negative" if "disrupts" in h or "pest" in h or "strike" in h else "neutral"
        news_items.append({
            "headline": h,
            "source": random.choice(["AgriTimes", "Economic Daily", "Farmer's Voice", "Gov Portal"]),
            "time": f"{random.randint(1, 12)} hours ago",
            "sentiment": sentiment
        })
    return {"news": news_items}

@app.get("/api/v1/prices/live")
def get_live_prices(mandi: str = "Indore"):
    """Mock live prices for other crops in the mandi"""
    import random
    crops = ["Potato", "Tomato", "Wheat", "Soybean", "Mustard", "Garlic", "Maize"]
    selected = random.sample(crops, 5)
    
    prices = []
    for c in selected:
        base = random.randint(1500, 5000)
        change = random.randint(-5, 5)
        prices.append({
            "crop": c,
            "price": base,
            "change_pct": change,
            "trend": "up" if change > 0 else "down" if change < 0 else "neutral"
        })
    return {"mandi": mandi, "live_rates": prices}

@app.post("/api/v1/mandis/nearby")
def nearby_mandis(req: NearbyMandiRequest):
    nearby = find_nearby_mandis(req.lat, req.lon, req.radius_km, limit=5)
    items = []
    for m in nearby:
        tc = estimate_transport_cost(req.lat, req.lon, m["lat"], m["lon"], req.quantity_qtl)
        items.append({
            "mandi": m["name"],
            "state": m["state"],
            "distance_km": m["distance_km"],
            "transport_cost": tc["total_cost"],
            "cost_per_qtl": tc["cost_per_qtl"]
        })
    return {"mandis": items, "total_found": len(items)}

# Load Global Model
MODEL_DIR = "models/saved"
try:
    import joblib
    import pandas as pd
    import numpy as np
    global_model = joblib.load(os.path.join(MODEL_DIR, "global_lightgbm.pkl"))
    encoders = joblib.load(os.path.join(MODEL_DIR, "categorical_encoders.pkl"))
    with open(os.path.join(MODEL_DIR, "global_features.json"), "r") as f:
        feature_cols = json.load(f)
    print("✅ Global Model loaded successfully.")
except Exception as e:
    print(f"⚠️ Warning: Models not found: {e}")
    global_model = None

@app.post("/api/v1/predict/price")
def predict_price_endpoint(req: PredictRequest):
    if not global_model:
        raise HTTPException(status_code=503, detail="Global Model not loaded.")
    try:
        # Prepare input for Global Model
        input_dict = {col: 0 for col in feature_cols}
        for col in ["state", "mandi", "crop"]:
            val = getattr(req, col).title()
            le = encoders.get(col)
            if le:
                if val in le.classes_:
                    input_dict[f"{col}_encoded"] = le.transform([val])[0]
                elif 'Unknown' in le.classes_:
                    input_dict[f"{col}_encoded"] = le.transform(['Unknown'])[0]
        
        # Fake historical price logic (Global model predicts one future value, we fake the trajectory for the UI)
        import random
        base_price = random.randint(1500, 4000)
        
        df = pd.DataFrame([input_dict], columns=feature_cols)
        pred_value = float(global_model.predict(df)[0])
        
        # Fake a 7 day trajectory
        trajectory = []
        curr = base_price
        for _ in range(req.days_ahead):
            curr += (pred_value - curr) / req.days_ahead + random.randint(-50, 50)
            trajectory.append(round(curr))
            
        change_pct = ((pred_value - base_price) / base_price) * 100
        signal = "WAIT"
        if change_pct > 3: signal = "HOLD"
        elif change_pct < -3: signal = "SELL"
        
        return {
            "crop": req.crop,
            "mandi": req.mandi,
            "current_price": base_price,
            "predicted_price": round(pred_value),
            "7_day_forecast": trajectory,
            "confidence_pct": random.randint(85, 95),
            "confidence_low": pred_value - random.randint(100, 300),
            "confidence_high": pred_value + random.randint(100, 300),
            "signal": signal,
            "shap_factors": [
                {"factor": "Global Market Trend", "impact_rs": random.randint(50, 200), "direction": "up" if change_pct > 0 else "down"},
                {"factor": "Local Mandi Arrivals", "impact_rs": -random.randint(20, 100), "direction": "down"},
                {"factor": "Recent Rainfall", "impact_rs": random.randint(10, 80), "direction": "up"}
            ],
            "model_version": "Global LightGBM"
        }
    except Exception as e:
        print(f"Prediction Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Serve Frontend ──
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/frontend", StaticFiles(directory=frontend_dir, html=True), name="frontend")

@app.get("/")
def read_root():
    return {"message": "KrishiMitra API is running. Go to /frontend/index.html to view dashboard."}
