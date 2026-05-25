# ═══════════════════════════════════════════════════════════════════
# KrishiMitra AI — Prediction Runner
# Loads trained models and generates price predictions with SHAP
# ═══════════════════════════════════════════════════════════════════

import os
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timedelta

from src.features import create_all_features, get_feature_columns, get_feature_importance_names
from src.model import (
    load_trained_model,
    ensemble_predict,
    predict_with_confidence,
    create_sequences,
)

# Window size for sequences
WINDOW_SIZE = 30
FORECAST_STEPS = 7


def load_prediction_models(crop: str, mandi: str = "indore",
                           model_dir: str = "models/saved") -> dict:
    """
    Load all trained models for a specific crop/mandi.

    Returns:
        {"lstm": model, "gru": model, "xgboost": model}
    """
    crop_mandi = f"{crop.lower()}_{mandi.lower()}"
    models = {}

    for model_type in ["lstm", "gru", "xgboost"]:
        try:
            model = load_trained_model(crop_mandi, model_type, model_dir)
            models[model_type] = model
            print(f"  ✅ Loaded {model_type} for {crop} @ {mandi}")
        except Exception as e:
            print(f"  ⚠️  Could not load {model_type}: {e}")

    if not models:
        raise RuntimeError(
            f"❌ No trained models found for {crop} @ {mandi}!\n"
            f"   Run: python -m src.train --crop {crop} --mandi {mandi}"
        )

    return models


def get_latest_features(crop: str, mandi: str,
                        data_path: str = "data/processed/master_dataset.csv",
                        n_days: int = 60) -> np.ndarray:
    """
    Get the latest N days of features for making a prediction.

    In production, this would fetch live data from the database.
    For now, we use the last N days from our dataset.
    """
    df = pd.read_csv(data_path, parse_dates=["date"])

    # Filter for this crop + mandi
    mask = (
        (df["crop"].str.lower() == crop.lower()) &
        (df["mandi"].str.lower() == mandi.lower())
    )
    filtered = df[mask].sort_values("date").tail(n_days).copy()

    if len(filtered) < WINDOW_SIZE:
        raise ValueError(
            f"❌ Not enough data! Need {WINDOW_SIZE} days, have {len(filtered)}."
        )

    # Run feature engineering (without target creation)
    featured = create_all_features(filtered, normalize=True)

    # Get feature columns
    feature_cols = get_feature_columns(featured)
    features = featured[feature_cols].values.astype(np.float32)

    # Take the last WINDOW_SIZE days as input sequence
    sequence = features[-WINDOW_SIZE:]
    sequence = sequence.reshape(1, WINDOW_SIZE, -1)  # (1, 30, n_features)

    return sequence, featured, filtered


def generate_shap_explanation(crop: str, mandi: str,
                              features_df: pd.DataFrame,
                              predicted_price: float) -> list:
    """
    Generate a simplified SHAP-like explanation for the prediction.

    For a full SHAP analysis, use the XGBoost model (easier than deep learning).
    This function creates a human-readable explanation of why the price is
    predicted to go up or down.

    Returns a list of factors like:
    [
        {"factor": "Rainfall shortage", "impact_rs": +312, "direction": "up"},
        {"factor": "Low mandi arrivals", "impact_rs": +248, "direction": "up"},
    ]
    """
    factors = []
    feature_names = get_feature_importance_names()

    # Try to load XGBoost model for SHAP (much easier than deep learning SHAP)
    try:
        import shap

        xgb_model = load_trained_model(
            f"{crop.lower()}_{mandi.lower()}", "xgboost"
        )

        # Get feature values for the last day
        feature_cols = get_feature_columns(features_df)
        last_row = features_df[feature_cols].iloc[-1:].values

        # Flatten for XGBoost
        X_flat = last_row.reshape(1, -1)

        # Calculate SHAP values
        explainer = shap.TreeExplainer(xgb_model)
        shap_values = explainer.shap_values(X_flat)

        # Get top 5 most important features
        feature_impacts = list(zip(feature_cols, shap_values[0]))
        feature_impacts.sort(key=lambda x: abs(x[1]), reverse=True)

        for feat_name, impact in feature_impacts[:5]:
            human_name = feature_names.get(feat_name, feat_name.replace("_", " ").title())
            direction = "up" if impact > 0 else "down"
            factors.append({
                "factor": human_name,
                "impact_rs": round(float(impact), 0),
                "direction": direction,
            })

    except Exception as e:
        # Fallback: rule-based explanation if SHAP fails
        print(f"  ⚠️  SHAP unavailable ({e}), using rule-based explanation")
        factors = _rule_based_explanation(features_df)

    return factors


def _rule_based_explanation(features_df: pd.DataFrame) -> list:
    """
    Fallback explanation when SHAP is unavailable.
    Uses simple rules based on feature values.
    """
    factors = []
    latest = features_df.iloc[-1]

    # Check rainfall
    if "rainfall_7d_sum" in latest.index:
        if latest.get("rainfall_7d_sum", 0) < 2:
            factors.append({
                "factor": "Low rainfall (potential drought)",
                "impact_rs": 200,
                "direction": "up",
            })
        elif latest.get("rainfall_7d_sum", 0) > 50:
            factors.append({
                "factor": "Heavy rainfall (transport disruption)",
                "impact_rs": 150,
                "direction": "up",
            })

    # Check supply pressure
    if "supply_pressure" in latest.index:
        sp = latest.get("supply_pressure", 1.0)
        if sp < 0.7:
            factors.append({
                "factor": "Low mandi arrivals (supply shortage)",
                "impact_rs": 250,
                "direction": "up",
            })
        elif sp > 1.3:
            factors.append({
                "factor": "High mandi arrivals (supply surplus)",
                "impact_rs": -200,
                "direction": "down",
            })

    # Check festival proximity
    if "days_to_festival" in latest.index:
        dtf = latest.get("days_to_festival", 365)
        if dtf <= 7:
            factors.append({
                "factor": "Festival demand (within 7 days)",
                "impact_rs": 220,
                "direction": "up",
            })

    # Check price momentum
    if "price_change_7d" in latest.index:
        pc = latest.get("price_change_7d", 0)
        if pc > 5:
            factors.append({
                "factor": "Strong upward price momentum",
                "impact_rs": 180,
                "direction": "up",
            })
        elif pc < -5:
            factors.append({
                "factor": "Downward price trend",
                "impact_rs": -180,
                "direction": "down",
            })

    # Default if no factors found
    if not factors:
        factors.append({
            "factor": "Market conditions stable",
            "impact_rs": 0,
            "direction": "neutral",
        })

    return factors


def generate_signal(current_price: float, predicted_price: float,
                    confidence_pct: float) -> str:
    """
    Generate a HOLD / SELL / WAIT trading signal.

    Logic:
    - Price going up significantly (>5%) + high confidence → HOLD
    - Price going down (>3%) + high confidence → SELL NOW
    - Low confidence or small change → WAIT
    """
    change_pct = (predicted_price - current_price) / current_price * 100

    if confidence_pct < 60:
        return "WAIT"  # Model is not sure enough
    elif change_pct > 5:
        return "HOLD"  # Price rising — hold for better price
    elif change_pct < -3:
        return "SELL"  # Price dropping — sell now
    elif change_pct > 2:
        return "HOLD"  # Slight increase — hold
    else:
        return "WAIT"  # Too close to call


def predict_price(crop: str, mandi: str = "indore",
                  days_ahead: int = 7) -> dict:
    """
    MAIN PREDICTION FUNCTION — Single entry point for getting predictions.

    This is what the FastAPI endpoint calls.

    Args:
        crop: Crop name (e.g., "onion")
        mandi: Mandi name (e.g., "indore")
        days_ahead: Number of days to forecast (default 7)

    Returns:
        Complete prediction dict with SHAP factors, confidence, and signal.
        Format matches the API response schema.
    """
    print(f"\n🔮 Predicting {crop} @ {mandi} ({days_ahead} days ahead)...")

    # 1. Load models
    models = load_prediction_models(crop, mandi)

    # 2. Get latest features
    X, features_df, filtered_df = get_latest_features(crop, mandi)

    # 3. Make prediction with confidence
    result = predict_with_confidence(models, X, n_runs=10)

    mean_pred = result["mean"].flatten()
    ci_low = result["confidence_low"].flatten()
    ci_high = result["confidence_high"].flatten()

    # Get current (last known) price from the raw dataframe
    current_price = float(filtered_df["modal_price"].iloc[-1])
    predicted_price = float(mean_pred[-1])

    # Try to find a fresher real-time today's price from the database/API to align the forecast
    real_current_price = None
    try:
        from api.database import SessionLocal, Price
        db = SessionLocal()
        latest = db.query(Price).filter(
            Price.crop.ilike(f"%{crop}%"),
            Price.mandi.ilike(f"%{mandi}%")
        ).order_by(Price.date.desc()).first()
        if latest and latest.modal_price > 0:
            real_current_price = latest.modal_price
        db.close()
    except Exception:
        pass

    if real_current_price is None:
        # Try fetching real-time from data.gov.in API
        try:
            import urllib.request
            import urllib.parse
            import json
            
            COMMODITY_MAPPING = {
                "onion": "Onion",
                "potato": "Potato",
                "tomato": "Tomato",
                "garlic": "Garlic",
                "ginger": "Ginger",
                "wheat": "Wheat",
                "rice": "Rice",
                "maize": "Maize",
                "soybean": "Soyabean",
                "mustard": "Mustard",
                "cotton": "Cotton",
                "chana": "Bengal Gram(Gram)(Whole)",
                "moong": "Green Gram (Moong)(Whole)",
            }
            
            params = {
                "api-key": "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b",
                "format": "json",
                "limit": 5,
                "filters[commodity]": COMMODITY_MAPPING.get(crop.lower(), crop.title()),
                "filters[market]": mandi.title()
            }
            query_str = urllib.parse.urlencode(params)
            url = f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?{query_str}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                records = res_data.get("records", [])
                if records:
                    real_current_price = float(records[0].get("modal_price", 0))
        except Exception:
            pass

    if real_current_price is not None and real_current_price > 0:
        # Align prediction starting from today's real price
        change_pct = (predicted_price - current_price) / current_price
        scale_factor = real_current_price / current_price
        current_price = real_current_price
        predicted_price = current_price * (1 + change_pct)
        mean_pred = mean_pred * scale_factor
        ci_low = ci_low * scale_factor
        ci_high = ci_high * scale_factor

    # 4. Generate SHAP explanation
    shap_factors = generate_shap_explanation(crop, mandi, features_df, predicted_price)

    # 5. Generate signal
    signal = generate_signal(current_price, predicted_price, result["confidence_pct"])

    # 6. Build response
    prediction = {
        "crop": crop.title(),
        "mandi": mandi.title(),
        "prediction_date": (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d"),
        "current_price": round(current_price, 0),
        "predicted_price": round(predicted_price, 0),
        "confidence_low": round(float(ci_low[-1]), 0),
        "confidence_high": round(float(ci_high[-1]), 0),
        "confidence_pct": round(result["confidence_pct"], 1),
        "signal": signal,
        "shap_factors": shap_factors,
        "7_day_forecast": [round(float(p), 0) for p in mean_pred[:days_ahead]],
        "model_version": "1.0.0",
        "generated_at": datetime.now().isoformat(),
    }

    print(f"  💰 Current: ₹{current_price:,.0f}")
    print(f"  📈 Predicted: ₹{predicted_price:,.0f} (in {days_ahead} days)")
    print(f"  🎯 Confidence: {result['confidence_pct']:.0f}%")
    print(f"  📊 Signal: {signal}")

    return prediction


# ═══════════════════════════════════════════════════════════════════
# MAIN — Quick test
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="🔮 KrishiMitra Price Prediction")
    parser.add_argument("--crop", type=str, default="onion", help="Crop to predict")
    parser.add_argument("--mandi", type=str, default="indore", help="Mandi location")
    parser.add_argument("--days", type=int, default=7, help="Days ahead to predict")

    args = parser.parse_args()

    result = predict_price(args.crop, args.mandi, args.days)
    print("\n📋 Full Prediction JSON:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
