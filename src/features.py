# ═══════════════════════════════════════════════════════════════════
# KrishiMitra AI — Feature Engineering
# Transforms raw price/weather data into ML-ready features
# ═══════════════════════════════════════════════════════════════════
#
# WHAT IS FEATURE ENGINEERING?
# Instead of giving the AI just the raw price, we give it extra "hints":
#   - What was the price 7 days ago? (lag features)
#   - What's the 30-day average? (rolling statistics)
#   - Is a festival coming up? (calendar features)
#   - Has it been raining heavily? (weather features)
# Each "hint" is called a FEATURE. More good features = better predictions.
# ═══════════════════════════════════════════════════════════════════

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib
import os

# ── Festival dates for India (Diwali, Holi, Eid, Pongal, etc.) ────
# These are approximate dates — prices spike near festivals due to demand
FESTIVAL_DATES = {
    # Diwali (prices spike 1-2 weeks before)
    "Diwali": [
        "2020-11-14", "2021-11-04", "2022-10-24", "2023-11-12",
        "2024-11-01", "2025-10-20", "2026-11-08", "2027-10-29",
        "2028-10-17", "2029-11-05", "2030-10-26",
    ],
    # Holi
    "Holi": [
        "2020-03-10", "2021-03-29", "2022-03-18", "2023-03-08",
        "2024-03-25", "2025-03-14", "2026-03-03", "2027-03-22",
        "2028-03-11", "2029-03-01", "2030-03-20",
    ],
    # Eid-ul-Fitr (approximate)
    "Eid": [
        "2020-05-24", "2021-05-13", "2022-05-03", "2023-04-22",
        "2024-04-11", "2025-03-31", "2026-03-20", "2027-03-10",
        "2028-02-27", "2029-02-15", "2030-02-04",
    ],
    # Pongal / Makar Sankranti (harvest festival)
    "Pongal": [
        "2020-01-15", "2021-01-14", "2022-01-14", "2023-01-15",
        "2024-01-15", "2025-01-14", "2026-01-14", "2027-01-14",
        "2028-01-14", "2029-01-14", "2030-01-14",
    ],
    # Navratri (9-day festival, high demand for certain crops)
    "Navratri": [
        "2020-10-17", "2021-10-07", "2022-09-26", "2023-10-15",
        "2024-10-03", "2025-10-22", "2026-10-11", "2027-10-01",
        "2028-09-20", "2029-10-09", "2030-09-28",
    ],
}

# ── Harvest seasons by crop (months when supply increases → price drops) ──
# This is a KEY feature: during harvest season, supply floods the mandis
HARVEST_MONTHS = {
    "Onion":      [1, 2, 3, 4, 5],          # Rabi: Jan–May
    "Potato":     [1, 2, 3, 12],              # Winter harvest
    "Tomato":     [1, 2, 3, 10, 11, 12],      # Multiple seasons
    "Wheat":      [3, 4, 5],                  # Rabi: Mar–May
    "Garlic":     [2, 3, 4],                  # Feb–Apr
    "Ginger":     [12, 1, 2],                 # Winter
    "Chana":      [3, 4],                     # Rabi: Mar–Apr
    "Maize":      [9, 10, 11],                # Kharif: Sep–Nov
    "Arhar Dal":  [12, 1, 2],                 # Winter
    "Soybean":    [10, 11],                   # Oct–Nov
}


def create_lag_features(df: pd.DataFrame, grouped) -> pd.DataFrame:
    """
    Create LAG features — "What was the price N days ago?"

    Why this matters:
    - Yesterday's price is the #1 predictor of today's price
    - Prices move in trends — if it went up 3 days in a row, it might continue
    - The model needs to "see" past prices to predict the future
    """
    for lag in [1, 3, 7, 14, 30]:
        df[f"price_lag_{lag}"] = grouped["modal_price"].shift(lag)

    # Also add arrival lags (supply trend)
    if "arrivals_qtl" in df.columns:
        for lag in [1, 7, 14]:
            df[f"arrivals_lag_{lag}"] = grouped["arrivals_qtl"].shift(lag)

    return df


def create_rolling_features(df: pd.DataFrame, grouped) -> pd.DataFrame:
    """
    Create ROLLING STATISTICS — "What's the trend been?"

    Why this matters:
    - A 7-day average smooths out daily noise → shows the real trend
    - Standard deviation shows volatility → unstable prices need more caution
    - Comparing current price to moving average shows if price is "too high" or "too low"
    """
    # Price rolling windows
    for window in [7, 14, 30]:
        df[f"price_roll_{window}d_mean"] = grouped["modal_price"].transform(
            lambda x: x.rolling(window, min_periods=1).mean()
        )
        df[f"price_roll_{window}d_std"] = grouped["modal_price"].transform(
            lambda x: x.rolling(window, min_periods=1).std()
        )

    # Arrivals rolling (supply trend)
    if "arrivals_qtl" in df.columns:
        df["arrivals_roll_7d_mean"] = grouped["arrivals_qtl"].transform(
            lambda x: x.rolling(7, min_periods=1).mean()
        )
        df["arrivals_roll_30d_mean"] = grouped["arrivals_qtl"].transform(
            lambda x: x.rolling(30, min_periods=1).mean()
        )

    return df


def create_momentum_features(df: pd.DataFrame, grouped) -> pd.DataFrame:
    """
    Create MOMENTUM features — "Is the price going up or down?"

    Why this matters:
    - Price change percentage tells the model about velocity of movement
    - A 7-day price change of +15% means prices are surging → might continue
    - Momentum helps predict trend continuation or reversal
    """
    # Price change (percentage)
    df["price_change_1d"] = grouped["modal_price"].pct_change(1) * 100
    df["price_change_7d"] = grouped["modal_price"].pct_change(7) * 100
    df["price_change_14d"] = grouped["modal_price"].pct_change(14) * 100
    df["price_change_30d"] = grouped["modal_price"].pct_change(30) * 100

    # Price relative to moving averages
    # If current price > 30d average → price is elevated
    df["price_vs_30d_avg"] = (
        df["modal_price"] / df["price_roll_30d_mean"].replace(0, np.nan)
    )

    return df


def create_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create CALENDAR features — dates, festivals, seasons.

    Why this matters:
    - Prices follow seasonal patterns (e.g., onion always spikes in Oct-Nov)
    - Festival demand causes pre-festival price surges
    - Weekday patterns exist (some mandis are closed on Sundays)
    """
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["day_of_week"] = df["date"].dt.dayofweek      # 0=Mon, 6=Sun
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["day_of_month"] = df["date"].dt.day
    df["is_month_start"] = df["date"].dt.is_month_start.astype(int)
    df["is_month_end"] = df["date"].dt.is_month_end.astype(int)
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    # ── Days until nearest festival ──
    all_festival_dates = []
    for fest_name, dates in FESTIVAL_DATES.items():
        for d in dates:
            all_festival_dates.append(pd.to_datetime(d))

    def days_to_nearest_festival(date):
        """Find the minimum absolute days to any festival date."""
        if not all_festival_dates:
            return 365
        diffs = [abs((date - fd).days) for fd in all_festival_dates]
        return min(diffs)

    df["days_to_festival"] = df["date"].apply(days_to_nearest_festival)
    df["is_festival_week"] = (df["days_to_festival"] <= 7).astype(int)
    df["is_festival_month"] = (df["days_to_festival"] <= 30).astype(int)

    # ── Harvest season (crop-specific) ──
    def is_harvest(row):
        crop = row.get("crop", "")
        month = row.get("month", 0)
        harvest_months = HARVEST_MONTHS.get(crop, [])
        return 1 if month in harvest_months else 0

    df["is_harvest_season"] = df.apply(is_harvest, axis=1)

    return df


def create_weather_features(df: pd.DataFrame, grouped) -> pd.DataFrame:
    """
    Create WEATHER features — rainfall, temperature extremes, drought detection.

    Why this matters:
    - Heavy rainfall → floods → transport disruption → price spike
    - Drought → crop failure → severe shortage → massive price increase
    - Temperature extremes affect crop shelf life (tomatoes spoil faster in heat)
    """
    if "rainfall_mm" not in df.columns:
        return df

    # Total rainfall over last 7 and 14 days
    df["rainfall_7d_sum"] = grouped["rainfall_mm"].transform(
        lambda x: x.rolling(7, min_periods=1).sum()
    )
    df["rainfall_14d_sum"] = grouped["rainfall_mm"].transform(
        lambda x: x.rolling(14, min_periods=1).sum()
    )

    # Is it raining heavily? (above 50mm in a week = significant)
    df["is_heavy_rain_week"] = (df["rainfall_7d_sum"] > 50).astype(int)

    # Drought detection: very low rain + high temperature
    if "temp_max" in df.columns:
        df["is_drought_week"] = (
            (df["rainfall_7d_sum"] < 2) & (df["temp_max"] > 35)
        ).astype(int)

        # Temperature deviation from rolling 30-day average
        df["temp_30d_avg"] = grouped["temp_max"].transform(
            lambda x: x.rolling(30, min_periods=1).mean()
        )
        df["temp_deviation"] = df["temp_max"] - df["temp_30d_avg"]

    # Humidity extremes
    if "humidity" in df.columns:
        df["is_high_humidity"] = (df["humidity"] > 85).astype(int)

    return df


def create_market_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create MARKET features — MSP premium, supply pressure, fuel cost impact.

    Why this matters:
    - MSP premium: if modal_price >> MSP, farmers are earning well
    - Supply pressure: if arrivals << average, supply is tight → price goes up
    - Fuel prices affect transport costs, which affect final mandi prices
    """
    # MSP Premium — how much above/below government MSP
    if "msp_price" in df.columns:
        df["msp_premium"] = df["modal_price"] / df["msp_price"].replace(0, np.nan)
        df["above_msp"] = (df["modal_price"] > df["msp_price"]).astype(int)

    # Supply pressure — current arrivals vs 30-day average
    if "arrivals_roll_30d_mean" in df.columns:
        df["supply_pressure"] = (
            df["arrivals_qtl"] / df["arrivals_roll_30d_mean"].replace(0, np.nan)
        )

    # Price spread — difference between max and min price at mandi
    if "max_price" in df.columns and "min_price" in df.columns:
        df["price_spread"] = df["max_price"] - df["min_price"]
        df["price_spread_pct"] = df["price_spread"] / df["modal_price"].replace(0, np.nan) * 100

    # Diesel / fuel cost index (if available)
    if "diesel_price" in df.columns:
        df["fuel_cost_index"] = df["diesel_price"] / df["diesel_price"].mean()
        df["diesel_price_normalized"] = df["diesel_price"] / 100.0  # Scale to 0-1 range

    return df


def create_forecast_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create WEATHER FORECAST features — what weather is COMING.

    Unlike historical weather features (what happened), these predict
    what WILL happen. This is critical for price prediction:
    - Rain forecast → transport will be disrupted → prices UP
    - Heatwave coming → perishables will spoil → buy NOW
    - Clear weather week → normal supply → prices stable

    These features come from OpenWeatherMap 5-day forecast API
    and are populated by src/external_data.py
    """
    # Tomorrow's forecast
    if "forecast_rain_tomorrow" in df.columns:
        df["rain_tomorrow_flag"] = (df["forecast_rain_tomorrow"] > 5).astype(int)
        df["heavy_rain_tomorrow"] = (df["forecast_rain_tomorrow"] > 20).astype(int)

    # 3-day forecast
    if "forecast_rain_3day" in df.columns:
        df["rain_3day_flag"] = (df["forecast_rain_3day"] > 15).astype(int)
        df["transport_risk_3day"] = np.where(
            df["forecast_rain_3day"] > 30, 3,  # High risk
            np.where(df["forecast_rain_3day"] > 10, 2,  # Medium risk
            np.where(df["forecast_rain_3day"] > 3, 1, 0))  # Low / None
        )

    # 5-day forecast
    if "forecast_rain_5day" in df.columns:
        df["rain_5day_flag"] = (df["forecast_rain_5day"] > 25).astype(int)

    # Temperature extremes in forecast
    if "forecast_temp_max_5day" in df.columns:
        df["heatwave_forecast"] = (df["forecast_temp_max_5day"] > 42).astype(int)

    # Weather severity (0-10 score from external_data.py)
    if "forecast_severity_tomorrow" in df.columns:
        df["severe_weather_tomorrow"] = (df["forecast_severity_tomorrow"] >= 5).astype(int)

    if "forecast_severity_5day" in df.columns:
        df["severe_weather_week"] = (df["forecast_severity_5day"] >= 5).astype(int)

    return df


def create_fuel_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create FUEL/TRANSPORT COST features.

    Diesel is the lifeblood of agricultural transport:
    - Farm → local mandi: bullock cart or tractor (diesel)
    - Local → wholesale: trucks (diesel)
    - Wholesale → retail: tempos (diesel)

    A ₹1 increase in diesel ≈ ₹2-5 per quintal at mandi.
    Crude oil at $95+ signals diesel price hike in 2-3 weeks.
    """
    # Fuel cost index relative to mean
    if "fuel_cost_index" in df.columns:
        df["fuel_above_avg"] = (df["fuel_cost_index"] > 1.0).astype(int)
        df["fuel_premium"] = df["fuel_cost_index"] - 1.0  # How far above average

    # Diesel price trend
    if "diesel_change" in df.columns:
        df["diesel_going_up"] = (df["diesel_change"] > 0).astype(int)
        df["diesel_going_down"] = (df["diesel_change"] < 0).astype(int)

    # Crude oil tier (leading indicator for future diesel prices)
    if "crude_tier" in df.columns:
        df["crude_expensive"] = (df["crude_tier"] >= 2).astype(int)  # Moderate or higher

    # USD/INR exchange rate impact (weaker rupee → costlier imports → higher prices)
    if "usd_inr_rate" in df.columns:
        df["rupee_weak"] = (df["usd_inr_rate"] > 84).astype(int)

    return df


def create_target_variables(df: pd.DataFrame, grouped,
                            forecast_days: int = 7) -> pd.DataFrame:
    """
    Create TARGET variables — what the model predicts.

    - price_7d_future: the actual price 7 days from now (regression target)
    - price_direction: 1 if price goes up, 0 if down (classification target)
    """
    # Main target: price N days in the future
    df["target_price"] = grouped["modal_price"].shift(-forecast_days)

    # Price change target (for classification: up or down?)
    df["target_change"] = df["target_price"] - df["modal_price"]
    df["target_direction"] = (df["target_change"] > 0).astype(int)

    # Percentage change target
    df["target_change_pct"] = (
        df["target_change"] / df["modal_price"].replace(0, np.nan) * 100
    )

    return df


def create_all_features(df: pd.DataFrame,
                        forecast_days: int = 7,
                        normalize: bool = True,
                        scaler_path: str = "models/saved/feature_scaler.pkl") -> pd.DataFrame:
    """
    MASTER FUNCTION — Run the entire feature engineering pipeline.

    Takes raw merged data (prices + weather) and produces ML-ready features.

    Args:
        df: Raw DataFrame with columns: date, crop, mandi, modal_price, etc.
        forecast_days: How many days ahead to predict (default 7)
        normalize: Whether to normalize features to 0–1 range
        scaler_path: Where to save the scaler for later use in prediction

    Returns:
        DataFrame with all features, ready for model training.
    """
    print("\n🔧 Starting Feature Engineering Pipeline...")
    print(f"   Input: {len(df)} rows, {len(df.columns)} columns")

    # Sort by crop + mandi + date (IMPORTANT for time-series features)
    df = df.sort_values(["crop", "mandi", "date"]).reset_index(drop=True)

    # Group by crop + mandi — features are computed within each group
    # (Onion prices in Indore are independent from Potato prices in Dewas)
    grouped = df.groupby(["crop", "mandi"])

    # ── Create all feature groups ──
    print("   📊 Creating lag features...")
    df = create_lag_features(df, grouped)

    print("   📈 Creating rolling statistics...")
    df = create_rolling_features(df, grouped)

    print("   🚀 Creating momentum features...")
    df = create_momentum_features(df, grouped)

    print("   📅 Creating calendar features...")
    df = create_calendar_features(df)

    print("   🌦️  Creating weather features...")
    df = create_weather_features(df, grouped)

    print("   💰 Creating market features...")
    df = create_market_features(df)

    print("   🔮 Creating forecast features...")
    df = create_forecast_features(df)

    print("   ⛽ Creating fuel/transport features...")
    df = create_fuel_features(df)

    print(f"   🎯 Creating target variables ({forecast_days}-day forecast)...")
    # Re-group after adding features
    grouped = df.groupby(["crop", "mandi"])
    df = create_target_variables(df, grouped, forecast_days)

    # ── Drop rows with NaN targets (can't train on these) ──
    initial_len = len(df)
    df = df.dropna(subset=["target_price"])

    # Also fill remaining NaN features with forward fill then 0
    feature_cols = [c for c in df.columns if c not in
                    ["date", "crop", "mandi", "state", "district", "variety", "grade",
                     "State", "District", "Market", "Commodity", "Variety", "Grade", "Arrival_Date", "Commodity_Code",
                     "target_price", "target_change", "target_direction", "target_change_pct"]]
    df[feature_cols] = df[feature_cols].ffill().fillna(0)

    print(f"   🗑️  Dropped {initial_len - len(df)} rows with missing targets")

    # ── Normalize numerical features to 0-1 range ──
    if normalize:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        # Don't normalize target or ID columns
        exclude = ["target_price", "target_change", "target_direction",
                    "target_change_pct", "day_of_week", "month", "quarter",
                    "is_weekend", "is_harvest_season", "is_festival_week",
                    "is_festival_month", "is_heavy_rain_week", "is_drought_week",
                    "is_high_humidity", "is_month_start", "is_month_end",
                    "above_msp", "target_direction"]
        cols_to_scale = [c for c in numeric_cols if c not in exclude]

        scaler = MinMaxScaler()
        df[cols_to_scale] = scaler.fit_transform(df[cols_to_scale])

        # Save scaler for use in prediction
        os.makedirs(os.path.dirname(scaler_path), exist_ok=True)
        joblib.dump(scaler, scaler_path)
        print(f"   💾 Scaler saved → {scaler_path}")

    print(f"\n✅ Feature Engineering Complete!")
    print(f"   Output: {len(df)} rows, {len(df.columns)} columns")
    print(f"   Features created: {len(df.columns) - 6}")  # minus base columns

    return df


def get_feature_columns(df: pd.DataFrame) -> list:
    """
    Get the list of feature columns (excludes date, crop, mandi, targets).

    Returns the columns that should be fed into the model.
    """
    exclude = ["date", "crop", "mandi", "state", "district", "variety", "grade",
               "State", "District", "Market", "Commodity", "Variety", "Grade", "Arrival_Date", "Commodity_Code",
               "target_price", "target_change", "target_direction",
               "target_change_pct", "arrivals_tonnes"]
    return [c for c in df.columns if c not in exclude]


def get_feature_importance_names() -> dict:
    """
    Human-readable names for features (used in SHAP explanations).

    The app shows: "Rainfall shortage contributed +₹312 to price increase"
    This mapping converts technical feature names to farmer-friendly labels.
    """
    return {
        "price_lag_1": "Yesterday's price",
        "price_lag_7": "Last week's price",
        "price_lag_30": "Last month's price",
        "price_roll_7d_mean": "7-day average trend",
        "price_roll_30d_mean": "30-day average trend",
        "price_change_7d": "Weekly price momentum",
        "arrivals_qtl": "Mandi arrival quantity",
        "arrivals_roll_7d_mean": "Weekly supply trend",
        "supply_pressure": "Supply vs demand pressure",
        "rainfall_7d_sum": "Recent rainfall",
        "rainfall_14d_sum": "Bi-weekly rainfall",
        "is_heavy_rain_week": "Heavy rain disruption",
        "is_drought_week": "Drought conditions",
        "temp_deviation": "Temperature anomaly",
        "days_to_festival": "Festival proximity",
        "is_festival_week": "Festival week demand",
        "is_harvest_season": "Harvest season (high supply)",
        "msp_premium": "MSP price premium",
        "price_spread_pct": "Price volatility",
        # Forecast features (NEW in v2.0)
        "forecast_rain_tomorrow": "Tomorrow's rain forecast",
        "heavy_rain_tomorrow": "Heavy rain expected tomorrow",
        "forecast_rain_3day": "3-day rain forecast",
        "transport_risk_3day": "Transport disruption risk (3-day)",
        "heatwave_forecast": "Heatwave coming this week",
        "severe_weather_tomorrow": "Severe weather alert",
        # Fuel/transport features (NEW in v2.0)
        "fuel_cost_index": "Transport/fuel costs",
        "diesel_price": "Current diesel price",
        "diesel_going_up": "Diesel price rising",
        "fuel_above_avg": "Fuel cost above average",
        "crude_tier": "Crude oil price tier",
        "crude_expensive": "Crude oil expensive (future diesel hike)",
        "rupee_weak": "Weak rupee (import cost up)",
        # Calendar
        "month": "Month of year",
        "day_of_week": "Day of week",
    }
