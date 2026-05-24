# ═══════════════════════════════════════════════════════════════════
# KrishiMitra AI — Data Loader
# Fetches weather data from OpenWeatherMap & loads AGMARKNET CSVs
# ═══════════════════════════════════════════════════════════════════

import os
import time
import glob
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

# ── City Coordinates (for weather API) ─────────────────────────────
# These are the main mandi cities we track for crop prices
CITIES = {
    "Indore":    {"lat": 22.7196, "lon": 75.8577, "state": "Madhya Pradesh"},
    "Dewas":     {"lat": 22.9676, "lon": 76.0534, "state": "Madhya Pradesh"},
    "Ujjain":    {"lat": 23.1765, "lon": 75.7885, "state": "Madhya Pradesh"},
    "Bhopal":    {"lat": 23.2599, "lon": 77.4126, "state": "Madhya Pradesh"},
    "Mandsaur":  {"lat": 24.0667, "lon": 75.0833, "state": "Madhya Pradesh"},
    "Sehore":    {"lat": 23.2000, "lon": 77.0833, "state": "Madhya Pradesh"},
    "Nashik":    {"lat": 19.9975, "lon": 73.7898, "state": "Maharashtra"},
    "Jaipur":    {"lat": 26.9124, "lon": 75.7873, "state": "Rajasthan"},
}

# ── Crops we're tracking ───────────────────────────────────────────
CROPS = ["Onion", "Potato", "Tomato", "Wheat", "Garlic",
         "Ginger", "Chana", "Maize", "Arhar Dal", "Soybean"]


# ═══════════════════════════════════════════════════════════════════
# WEATHER DATA — Fetch from OpenWeatherMap
# ═══════════════════════════════════════════════════════════════════

def fetch_weather_for_city(city_name: str, lat: float, lon: float,
                           api_key: str, start_year: int = 2015,
                           end_year: int = 2024) -> pd.DataFrame:
    """
    Fetch historical daily weather for one city from OpenWeatherMap.

    How it works:
    - Calls the API one day at a time (that's how their historical API works)
    - Gets temperature (min/max), rainfall, humidity for each day
    - Retries 3 times if a request fails (network issues happen!)

    Why we need weather data:
    - Heavy rain → transport disruption → less supply at mandi → price goes UP
    - Drought → crop damage → shortage → price goes UP significantly
    - The AI model learns these patterns from historical data

    Args:
        city_name: Name like "Indore"
        lat, lon:  GPS coordinates
        api_key:   Your OpenWeatherMap API key
        start_year: First year of data (default 2015)
        end_year:   Last year of data (default 2024)

    Returns:
        DataFrame with columns: date, city, temp_max, temp_min, temp_avg,
                                rainfall_mm, humidity, wind_speed
    """
    records = []
    current = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    total_days = (end - current).days + 1

    print(f"\n🌦️  Fetching weather for {city_name} ({start_year}–{end_year})...")

    with tqdm(total=total_days, desc=city_name, unit="day") as pbar:
        while current <= end:
            url = "https://api.openweathermap.org/data/3.0/onecall/day_summary"
            params = {
                "lat": lat,
                "lon": lon,
                "date": current.strftime("%Y-%m-%d"),
                "appid": api_key,
                "units": "metric",  # Celsius, mm, etc.
            }

            # Retry up to 3 times if API fails
            for attempt in range(3):
                try:
                    resp = requests.get(url, params=params, timeout=10)
                    resp.raise_for_status()
                    data = resp.json()

                    records.append({
                        "date": current.strftime("%Y-%m-%d"),
                        "city": city_name,
                        "temp_max": data.get("temperature", {}).get("max", np.nan),
                        "temp_min": data.get("temperature", {}).get("min", np.nan),
                        "temp_avg": data.get("temperature", {}).get("afternoon", np.nan),
                        "rainfall_mm": data.get("precipitation", {}).get("total", 0.0),
                        "humidity": data.get("humidity", {}).get("afternoon", np.nan),
                        "wind_speed": data.get("wind", {}).get("max", {}).get("speed", np.nan),
                    })
                    break  # Success — move to next day

                except Exception as e:
                    if attempt < 2:
                        time.sleep(5)  # Wait 5 seconds before retry
                    else:
                        # After 3 failures, log NaN and move on
                        records.append({
                            "date": current.strftime("%Y-%m-%d"),
                            "city": city_name,
                            "temp_max": np.nan, "temp_min": np.nan,
                            "temp_avg": np.nan, "rainfall_mm": np.nan,
                            "humidity": np.nan, "wind_speed": np.nan,
                        })

            current += timedelta(days=1)
            pbar.update(1)

            # Rate limiting — OpenWeatherMap free tier: 60 calls/minute
            time.sleep(1.1)

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    return df


def fetch_all_weather(output_dir: str = "data/external/weather",
                      start_year: int = 2015,
                      end_year: int = 2024):
    """
    Fetch weather for ALL tracked cities and save as CSVs.

    Creates one CSV per city in the output directory:
      data/external/weather/weather_indore.csv
      data/external/weather/weather_dewas.csv
      ...
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise ValueError(
            "❌ OPENWEATHER_API_KEY not found! "
            "Set it in your .env file or environment variables.\n"
            "Get a free key at: https://openweathermap.org/api"
        )

    os.makedirs(output_dir, exist_ok=True)

    for city_name, coords in CITIES.items():
        output_file = os.path.join(output_dir, f"weather_{city_name.lower()}.csv")

        # Skip if already downloaded
        if os.path.exists(output_file):
            print(f"⏭️  {city_name} already exists, skipping...")
            continue

        df = fetch_weather_for_city(
            city_name=city_name,
            lat=coords["lat"],
            lon=coords["lon"],
            api_key=api_key,
            start_year=start_year,
            end_year=end_year,
        )
        df.to_csv(output_file, index=False)
        print(f"✅ Saved {len(df)} days → {output_file}")

    print("\n🎉 All weather data downloaded!")


# ═══════════════════════════════════════════════════════════════════
# AGMARKNET DATA — Load downloaded CSVs
# ═══════════════════════════════════════════════════════════════════

def load_agmarknet_csv(filepath: str) -> pd.DataFrame:
    """
    Load and clean a single AGMARKNET CSV file.

    AGMARKNET CSVs typically have columns like:
    State, District, Market, Commodity, Variety, Grade,
    Min_Price, Max_Price, Modal_Price, Date

    We standardize column names and data types.
    """
    try:
        df = pd.read_csv(filepath, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, encoding="latin-1")

    # Standardize column names (AGMARKNET files can vary)
    rename_map = {
        "Commodity": "crop",
        "Market": "mandi",
        "State Name": "state",
        "State": "state",
        "District Name": "district",
        "District": "district",
        "Min Price (Rs./Quintal)": "min_price",
        "Min_Price": "min_price",
        "Max Price (Rs./Quintal)": "max_price",
        "Max_Price": "max_price",
        "Modal Price (Rs./Quintal)": "modal_price",
        "Modal_Price": "modal_price",
        "Price Date": "date",
        "Arrival_Date": "date",
        "Arrivals (Tonnes)": "arrivals_tonnes",
        "Arrivals": "arrivals_tonnes",
    }

    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Parse dates
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

    # Clean string columns
    for col in ["crop", "mandi", "state", "district"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.title()

    # Convert prices to numeric
    for col in ["min_price", "max_price", "modal_price", "arrivals_tonnes"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Convert arrivals from tonnes to quintals (1 tonne = 10 quintals)
    if "arrivals_tonnes" in df.columns:
        df["arrivals_qtl"] = df["arrivals_tonnes"] * 10
    elif "arrivals_qtl" not in df.columns:
        df["arrivals_qtl"] = np.nan

    # Sort by date
    if "date" in df.columns:
        df = df.sort_values("date").reset_index(drop=True)

    return df


def load_all_agmarknet(raw_dir: str = "data/raw") -> pd.DataFrame:
    """
    Load ALL AGMARKNET CSV files from data/raw/ and combine into one DataFrame.

    Naming convention expected:
      agmarknet_onion_indore_2010_2024.csv
      agmarknet_potato_dewas_2015_2024.csv

    Returns a single combined DataFrame sorted by date.
    """
    csv_files = glob.glob(os.path.join(raw_dir, "*.csv"))

    if not csv_files:
        print(f"⚠️  No CSV files found in {raw_dir}/")
        print("   Download data from agmarknet.gov.in → Price & Arrivals → Price Report")
        return pd.DataFrame()

    all_dfs = []
    for filepath in tqdm(csv_files, desc="Loading AGMARKNET CSVs"):
        df = load_agmarknet_csv(filepath)
        all_dfs.append(df)
        print(f"  📄 {os.path.basename(filepath)}: {len(df)} rows")

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(subset=["date", "crop", "mandi"], keep="last")
    combined = combined.sort_values("date").reset_index(drop=True)

    print(f"\n✅ Total: {len(combined)} rows, {combined['crop'].nunique()} crops, "
          f"{combined['mandi'].nunique()} mandis")
    return combined


# ═══════════════════════════════════════════════════════════════════
# MERGE DATA — Combine prices + weather into one dataset
# ═══════════════════════════════════════════════════════════════════

def merge_price_and_weather(prices_df: pd.DataFrame,
                            weather_dir: str = "data/external/weather") -> pd.DataFrame:
    """
    Merge AGMARKNET price data with weather data by matching city + date.

    The result is one row per (date, crop, mandi) with both price and weather columns.
    This is what the model trains on.
    """
    # Load all weather CSVs
    weather_files = glob.glob(os.path.join(weather_dir, "weather_*.csv"))
    if not weather_files:
        print("⚠️  No weather data found. Run fetch_all_weather() first.")
        return prices_df

    weather_dfs = []
    for f in weather_files:
        df = pd.read_csv(f, parse_dates=["date"])
        weather_dfs.append(df)
    weather = pd.concat(weather_dfs, ignore_index=True)

    # Map mandi names to weather city names
    # (AGMARKNET uses "Indore" as mandi name, matching our weather city names)
    weather = weather.rename(columns={"city": "mandi"})

    # Merge on date + mandi
    merged = prices_df.merge(weather, on=["date", "mandi"], how="left")

    null_weather = merged["temp_max"].isna().sum()
    if null_weather > 0:
        print(f"⚠️  {null_weather} rows missing weather data ({null_weather/len(merged)*100:.1f}%)")
        # Forward-fill weather for missing days (weekends, holidays)
        weather_cols = ["temp_max", "temp_min", "temp_avg", "rainfall_mm", "humidity", "wind_speed"]
        merged[weather_cols] = merged.groupby("mandi")[weather_cols].ffill()

    return merged


def load_external_data() -> dict:
    """
    Load external datasets: MSP prices, fuel prices, festival calendar.
    Returns a dict of DataFrames for each data source.
    """
    external = {}

    # ── MSP (Minimum Support Prices) ──
    msp_path = "data/external/msp_prices.csv"
    if os.path.exists(msp_path):
        external["msp"] = pd.read_csv(msp_path)
        print(f"  📊 MSP data: {len(external['msp'])} rows")

    # ── Fuel/Diesel Prices ──
    fuel_path = "data/external/fuel_prices.csv"
    if os.path.exists(fuel_path):
        external["fuel"] = pd.read_csv(fuel_path, parse_dates=["date"])
        print(f"  ⛽ Fuel data: {len(external['fuel'])} rows")

    # ── Festival Calendar ──
    festival_path = "data/external/festivals.csv"
    if os.path.exists(festival_path):
        external["festivals"] = pd.read_csv(festival_path, parse_dates=["date"])
        print(f"  🎉 Festival data: {len(external['festivals'])} rows")

    return external


# ═══════════════════════════════════════════════════════════════════
# MAIN — Run this to download all data
# ═══════════════════════════════════════════════════════════════════

def main():
    """
    Run the full data loading pipeline:
    1. Fetch weather data from OpenWeatherMap API
    2. Load AGMARKNET CSV files
    3. Merge prices + weather
    4. Save the master dataset
    """
    print("=" * 60)
    print("🌾 KrishiMitra — Data Loading Pipeline")
    print("=" * 60)

    # Step 1: Fetch weather (skip if already downloaded)
    print("\n📥 Step 1: Fetching weather data...")
    try:
        fetch_all_weather()
    except ValueError as e:
        print(f"  {e}")
        print("  Continuing without weather data...")

    # Step 2: Load AGMARKNET data
    print("\n📥 Step 2: Loading AGMARKNET price data...")
    prices = load_all_agmarknet()

    if prices.empty:
        print("\n❌ No price data found. Please download CSVs from agmarknet.gov.in")
        print("   and place them in data/raw/ folder.")
        return

    # Step 3: Merge with weather
    print("\n🔀 Step 3: Merging price + weather data...")
    master = merge_price_and_weather(prices)

    # Step 4: Save master dataset
    os.makedirs("data/processed", exist_ok=True)
    output_path = "data/processed/master_dataset.csv"
    master.to_csv(output_path, index=False)
    print(f"\n✅ Master dataset saved → {output_path}")
    print(f"   Rows: {len(master):,}  |  Columns: {len(master.columns)}")
    print(f"   Date range: {master['date'].min()} → {master['date'].max()}")
    print(f"   Crops: {master['crop'].nunique()}  |  Mandis: {master['mandi'].nunique()}")


if __name__ == "__main__":
    main()
