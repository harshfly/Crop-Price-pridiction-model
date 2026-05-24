import os
import time
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error

from src.features import create_all_features, get_feature_columns
from src.model import build_xgboost_v2, build_lightgbm, HAS_LGBM, evaluate_model, save_model

def train_global_model():
    """
    Train a Unified Global Model on ALL crops, mandis, and states simultaneously.
    This replaces the 40,000+ individual models with a single, highly capable model.
    """
    print("\n" + "🌍" * 30)
    print("🌍 TRAINING GLOBAL UNIFIED MODEL (All India)")
    print("🌍" * 30)

    # 1. Load entire master dataset
    master_path = "data/processed/master_dataset.csv"
    if not os.path.exists(master_path):
        print(f"❌ Master dataset not found at {master_path}")
        return

    print("📥 Loading full master dataset...")
    df = pd.read_csv(master_path, parse_dates=["date"])
    print(f"   Loaded {len(df):,} rows.")

    # Sort to prevent temporal leak
    df = df.sort_values(by=["date"]).reset_index(drop=True)

    # 2. Encode categorical features BEFORE feature engineering
    # We use LabelEncoder for tree-based models
    print("🔠 Encoding categorical features (State, Mandi, Crop)...")
    encoders = {}
    cat_cols = ["state", "mandi", "crop"]
    
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.title()
            le = LabelEncoder()
            # We add an 'Unknown' category to handle unseen data at inference
            unique_vals = list(df[col].unique()) + ['Unknown']
            le.fit(unique_vals)
            df[col + "_encoded"] = le.transform(df[col])
            encoders[col] = le
            
    # Save encoders
    os.makedirs("models/saved", exist_ok=True)
    joblib.dump(encoders, "models/saved/categorical_encoders.pkl")

    # 3. Feature Engineering
    print("🔧 Running feature engineering pipeline on ALL data...")
    # Forecast 7 days ahead
    df_features = create_all_features(df, forecast_days=7, normalize=True)
    
    # Target variable
    target_col = "target_price"
    
    # Feature columns (exclude raw categoricals and IDs)
    exclude = ["date", "state", "mandi", "crop", "district", "variety", "grade", 
               target_col, "target_change", "target_direction", "target_change_pct",
               "arrivals_tonnes"]
    feature_cols = [c for c in df_features.columns if c not in exclude]

    print(f"   Using {len(feature_cols)} features.")

    # 4. Train-Test Split (Time-based: last 10% of time is test)
    print("✂️ Splitting data (Time-based)...")
    split_idx = int(len(df_features) * 0.9)
    train_df = df_features.iloc[:split_idx]
    test_df = df_features.iloc[split_idx:]

    X_train = train_df[feature_cols].values
    y_train = train_df[target_col].values
    X_test = test_df[feature_cols].values
    y_test = test_df[target_col].values

    print(f"   Train: {len(X_train):,} rows | Test: {len(X_test):,} rows")

    results = {}

    # 5. Train LightGBM (Fastest and best for global tabular data)
    if HAS_LGBM:
        print("\n🍃 Training Global LightGBM...")
        start = time.time()
        lgbm = build_lightgbm(X_train.shape[1])
        lgbm.fit(X_train, y_train, eval_set=[(X_test, y_test)])
        elapsed = time.time() - start
        print(f"   Trained in {elapsed:.1f}s")
        
        preds = lgbm.predict(X_test)
        results["Global_LightGBM"] = evaluate_model(y_test, preds, "Global_LightGBM")
        
        # Save model
        joblib.dump(lgbm, "models/saved/global_lightgbm.pkl")
        
        # Feature Importance
        importance = pd.DataFrame({
            "Feature": feature_cols,
            "Importance": lgbm.feature_importances_
        }).sort_values(by="Importance", ascending=False).head(15)
        print("\n🌟 Top 10 Features (LightGBM):")
        print(importance.head(10).to_string(index=False))

    # 6. Train XGBoost
    print("\n🌲 Training Global XGBoost...")
    start = time.time()
    xgb = build_xgboost_v2(X_train.shape[1])
    xgb.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    elapsed = time.time() - start
    print(f"   Trained in {elapsed:.1f}s")
    
    preds_xgb = xgb.predict(X_test)
    results["Global_XGBoost"] = evaluate_model(y_test, preds_xgb, "Global_XGBoost")
    
    # Save model
    joblib.dump(xgb, "models/saved/global_xgboost.pkl")

    # 7. Print Summary
    print("\n" + "═" * 80)
    print(f"🏆 GLOBAL MODEL EVALUATION (v2.0 Industry)")
    print("═" * 80)
    for name, res in results.items():
        acc = res.get("accuracy_pct", 100 - res.get("mape", 100))
        print(f"{name}: sMAPE={res['smape']:.1f}% | Acc={acc:.1f}% | DirAcc={res['directional_accuracy']:.1f}%")
        
    # Save feature names for inference
    with open("models/saved/global_features.json", "w") as f:
        json.dump(feature_cols, f)
        
    print("\n✅ Global training complete! Models saved to models/saved/")
    return results

if __name__ == "__main__":
    train_global_model()
