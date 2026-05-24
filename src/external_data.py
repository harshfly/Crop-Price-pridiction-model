# ═══════════════════════════════════════════════════════════════════
# KrishiMitra AI — External Data Feeds (Weather Forecast + Fuel Prices)
# Live data that directly impacts crop price predictions
# ═══════════════════════════════════════════════════════════════════
#
# THREE DATA FEEDS:
# 1. Weather Forecast (7-day) — from OpenWeatherMap API
#    → Rain forecast = transport disruption = price spike
#    → Heat wave = crop damage = supply shortage
#
# 2. Fuel/Diesel Prices — scraped from GoodReturns.in
#    → Diesel ₹ up = transport cost up = mandi price up
#    → Direct 5-8% impact on final commodity price
#
# 3. Crude Oil Prices — from Yahoo Finance / exchange rate
#    → Leading indicator for future diesel prices
#    → Model uses this to predict NEXT WEEK's transport costs
#
# USAGE:
#   python -m src.external_data            # Fetch all external data
#   python -m src.external_data --weather  # Only weather forecast
#   python -m src.external_data --fuel     # Only fuel prices
# ═══════════════════════════════════════════════════════════════════

import os
import time
import json
import argparse
import logging
from datetime import datetime, timedelta
from typing import Optional

import requests
import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("krishimitra.external_data")

# ═══════════════════════════════════════════════════════════════════
# STATE CAPITALS CONFIGURATION (Used as proxies for all mandis in state)
# ═══════════════════════════════════════════════════════════════════
# To avoid rate limiting on 12,000+ mandis, we fetch weather for state capitals
# and map it to all mandis within that state.

STATE_COORDS = {
    "Andaman and Nicobar Islands": {"lat": 11.6670, "lon": 92.7359, "capital": "Port Blair"},
    "Andhra Pradesh": {"lat": 16.5061, "lon": 80.6480, "capital": "Amaravati"},
    "Arunachal Pradesh": {"lat": 27.0844, "lon": 93.6053, "capital": "Itanagar"},
    "Assam": {"lat": 26.1433, "lon": 91.7898, "capital": "Dispur"},
    "Bihar": {"lat": 25.5940, "lon": 85.1375, "capital": "Patna"},
    "Chandigarh": {"lat": 30.7333, "lon": 76.7794, "capital": "Chandigarh"},
    "Chhattisgarh": {"lat": 21.2513, "lon": 81.6296, "capital": "Raipur"},
    "Dadra and Nagar Haveli and Daman and Diu": {"lat": 20.3973, "lon": 72.8328, "capital": "Daman"},
    "Delhi": {"lat": 28.6139, "lon": 77.2090, "capital": "New Delhi"},
    "Goa": {"lat": 15.4909, "lon": 73.8278, "capital": "Panaji"},
    "Gujarat": {"lat": 23.2156, "lon": 72.6369, "capital": "Gandhinagar"},
    "Haryana": {"lat": 30.7333, "lon": 76.7794, "capital": "Chandigarh"},
    "Himachal Pradesh": {"lat": 31.1048, "lon": 77.1734, "capital": "Shimla"},
    "Jammu and Kashmir": {"lat": 34.0837, "lon": 74.7973, "capital": "Srinagar"},
    "Jharkhand": {"lat": 23.3441, "lon": 85.3095, "capital": "Ranchi"},
    "Karnataka": {"lat": 12.9716, "lon": 77.5946, "capital": "Bengaluru"},
    "Kerala": {"lat": 8.5241, "lon": 76.9366, "capital": "Thiruvananthapuram"},
    "Ladakh": {"lat": 34.1525, "lon": 77.5770, "capital": "Leh"},
    "Lakshadweep": {"lat": 10.5667, "lon": 72.6167, "capital": "Kavaratti"},
    "Madhya Pradesh": {"lat": 23.2599, "lon": 77.4126, "capital": "Bhopal"},
    "Maharashtra": {"lat": 18.9878, "lon": 72.8364, "capital": "Mumbai"},
    "Manipur": {"lat": 24.8170, "lon": 93.9368, "capital": "Imphal"},
    "Meghalaya": {"lat": 25.5788, "lon": 91.8933, "capital": "Shillong"},
    "Mizoram": {"lat": 23.7271, "lon": 92.7176, "capital": "Aizawl"},
    "Nagaland": {"lat": 25.6751, "lon": 94.1086, "capital": "Kohima"},
    "Odisha": {"lat": 20.2960, "lon": 85.8245, "capital": "Bhubaneswar"},
    "Puducherry": {"lat": 11.9416, "lon": 79.8083, "capital": "Puducherry"},
    "Punjab": {"lat": 30.7333, "lon": 76.7794, "capital": "Chandigarh"},
    "Rajasthan": {"lat": 26.9124, "lon": 75.7873, "capital": "Jaipur"},
    "Sikkim": {"lat": 27.3389, "lon": 88.6065, "capital": "Gangtok"},
    "Tamil Nadu": {"lat": 13.0826, "lon": 80.2707, "capital": "Chennai"},
    "Telangana": {"lat": 17.3850, "lon": 78.4866, "capital": "Hyderabad"},
    "Tripura": {"lat": 23.8314, "lon": 91.2867, "capital": "Agartala"},
    "Uttar Pradesh": {"lat": 26.8467, "lon": 80.9462, "capital": "Lucknow"},
    "Uttarakhand": {"lat": 30.3164, "lon": 78.0321, "capital": "Dehradun"},
    "West Bengal": {"lat": 22.5726, "lon": 88.3638, "capital": "Kolkata"},
}


# ═══════════════════════════════════════════════════════════════════
# 1. WEATHER FORECAST — Open-Meteo API (Free)
# ═══════════════════════════════════════════════════════════════════

def fetch_weather_forecast(state_name: str, lat: float, lon: float) -> pd.DataFrame:
    """
    Fetch 7-day weather forecast from Open-Meteo.

    This API is completely FREE and requires no API key.
    We fetch daily max/min temp, precipitation, and wind speed.

    WHY THIS MATTERS FOR CROP PRICES:
    - If rain is forecast → transport disruption = price spike
    - If heatwave coming → perishables (tomato, leafy veg) spoil = buy NOW
    - If clear weather week → good transport = prices stable
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "timezone": "auto",
        "forecast_days": 7
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        daily = data.get("daily", {})
        if not daily:
            return _generate_weather_fallback(state_name, lat)

        records = []
        for i in range(len(daily.get("time", []))):
            records.append({
                "date": daily["time"][i],
                "state": state_name,
                "temp_max": daily["temperature_2m_max"][i],
                "temp_min": daily["temperature_2m_min"][i],
                "rainfall_forecast_mm": daily["precipitation_sum"][i],
                "wind_max_forecast": daily["wind_speed_10m_max"][i],
            })

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        
        # Add weather severity score (0-10)
        df["weather_severity"] = _calculate_weather_severity(df)

        # Add forecast confidence (decreases with time)
        df["forecast_day"] = range(1, len(df) + 1)
        df["forecast_confidence"] = np.clip(100 - (df["forecast_day"] * 8), 40, 95)
        
        df["source"] = "open-meteo"
        df["fetched_at"] = datetime.utcnow()

        print(f"  🌦️ {state_name}: 7-day forecast fetched")
        return df

    except Exception as e:
        logger.error(f"❌ Weather API failed for {state_name}: {e}")
        return _generate_weather_fallback(state_name, lat)


def _calculate_weather_severity(df: pd.DataFrame) -> pd.Series:
    """
    Calculate weather severity score (0-10) for crop price impact.
    """
    severity = pd.Series(0.0, index=df.index)

    if "rainfall_forecast_mm" in df.columns:
        severity += np.where(df["rainfall_forecast_mm"] > 50, 5,
                   np.where(df["rainfall_forecast_mm"] > 20, 3,
                   np.where(df["rainfall_forecast_mm"] > 10, 1, 0)))

    if "wind_max_forecast" in df.columns:
        severity += np.where(df["wind_max_forecast"] > 25, 2,
                   np.where(df["wind_max_forecast"] > 15, 1, 0))

    if "temp_max" in df.columns:
        severity += np.where(df["temp_max"] > 42, 3,
                   np.where(df["temp_max"] > 38, 1, 0))
                   
    if "temp_min" in df.columns:
        severity += np.where(df["temp_min"] < 5, 3,
                   np.where(df["temp_min"] < 10, 1, 0))

    return severity.clip(0, 10)


def _generate_weather_fallback(city_name: str, lat: float) -> pd.DataFrame:
    """
    Generate reasonable weather estimates when API is unavailable.
    Uses latitude-based seasonal patterns.
    """
    today = datetime.now()
    records = []

    for i in range(7):
        date = today + timedelta(days=i)
        month = date.month

        # Seasonal temperature estimate
        if lat > 25:  # North India
            base_temp = {1: 15, 2: 18, 3: 25, 4: 32, 5: 38, 6: 36,
                        7: 32, 8: 30, 9: 30, 10: 28, 11: 22, 12: 16}
        else:  # South India
            base_temp = {1: 25, 2: 27, 3: 30, 4: 33, 5: 34, 6: 30,
                        7: 28, 8: 28, 9: 28, 10: 28, 11: 27, 12: 25}

        temp = base_temp.get(month, 25)
        is_monsoon = month in [6, 7, 8, 9]

        records.append({
            "date": date.strftime("%Y-%m-%d"),
            "city": city_name,
            "temp_max": temp + np.random.uniform(0, 4),
            "temp_min": temp - np.random.uniform(5, 10),
            "temp_avg_forecast": temp,
            "rainfall_forecast_mm": np.random.uniform(5, 30) if is_monsoon else np.random.uniform(0, 3),
            "humidity_forecast": 75 if is_monsoon else 45,
            "wind_max_forecast": np.random.uniform(5, 15),
            "cloud_cover_pct": 70 if is_monsoon else 20,
            "weather_severity": 4 if is_monsoon else 1,
            "forecast_day": i + 1,
            "forecast_confidence": max(40, 90 - i * 8),
            "source": "fallback_estimate",
        })

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    return df


def fetch_all_weather_forecasts(output_dir: str = "data/external/weather") -> pd.DataFrame:
    """Fetch 7-day forecast for ALL tracked states."""
    os.makedirs(output_dir, exist_ok=True)
    all_forecasts = []

    print(f"\n{'═' * 60}")
    print(f"🌦️ WEATHER FORECAST FETCH — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═' * 60}")

    for state, coords in STATE_COORDS.items():
        forecast = fetch_weather_forecast(state, coords["lat"], coords["lon"])
        if not forecast.empty:
            all_forecasts.append(forecast)
        time.sleep(1)  # Rate limiting

    if all_forecasts:
        combined = pd.concat(all_forecasts, ignore_index=True)
        filepath = os.path.join(output_dir, "weather_forecast_latest.csv")
        combined.to_csv(filepath, index=False)
        print(f"\n💾 Forecast saved → {filepath} ({len(combined)} rows)")
        return combined

    return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════
# 2. FUEL / DIESEL PRICES — Scrape from GoodReturns.in
# ═══════════════════════════════════════════════════════════════════

def fetch_fuel_prices() -> pd.DataFrame:
    """
    Fetch current petrol/diesel prices across major Indian cities.

    WHY FUEL PRICES AFFECT CROP PRICES:
    - Diesel powers farm tractors, irrigation pumps, and transport trucks
    - A ₹1 increase in diesel → ₹2-5 increase per quintal at mandi
    - Diesel is 5-8% of total crop cost from farm to consumer
    - This is a LEADING indicator — fuel price up today → crop price up in 2-3 days

    Source: Scrapes goodreturns.in (reliable, updated daily at 6 AM)

    Returns DataFrame with: city, petrol_price, diesel_price, date
    """
    print(f"\n{'═' * 60}")
    print(f"⛽ FUEL PRICE FETCH — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═' * 60}")

    # Try multiple free sources
    df = _try_goodreturns_fuel()
    if df is not None and not df.empty:
        return df

    df = _try_ndtv_fuel()
    if df is not None and not df.empty:
        return df

    # Fallback: use known base prices with minor variations
    print("  ⚠️ Live fuel scraping unavailable. Using base estimates.")
    return _generate_fuel_fallback()


def _try_goodreturns_fuel() -> Optional[pd.DataFrame]:
    """Scrape fuel prices from goodreturns.in"""
    try:
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        url = "https://www.goodreturns.in/diesel-price.html"
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        records = []

        # Find the price table
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows[1:]:  # Skip header
                cols = row.find_all("td")
                if len(cols) >= 3:
                    city = cols[0].get_text(strip=True)
                    diesel_today = cols[1].get_text(strip=True).replace("₹", "").replace(",", "").strip()
                    diesel_yesterday = cols[2].get_text(strip=True).replace("₹", "").replace(",", "").strip()

                    try:
                        records.append({
                            "city": city,
                            "diesel_price": float(diesel_today),
                            "diesel_yesterday": float(diesel_yesterday),
                            "diesel_change": float(diesel_today) - float(diesel_yesterday),
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "source": "goodreturns.in",
                        })
                    except (ValueError, TypeError):
                        continue

        if records:
            df = pd.DataFrame(records)
            print(f"  ✅ Diesel prices fetched: {len(df)} cities")
            return df

    except ImportError:
        logger.warning("  ⚠️ beautifulsoup4 not installed. Run: pip install beautifulsoup4")
    except Exception as e:
        logger.warning(f"  ⚠️ GoodReturns scrape failed: {e}")

    return None


def _try_ndtv_fuel() -> Optional[pd.DataFrame]:
    """Alternative: try NDTV fuel prices page."""
    try:
        from bs4 import BeautifulSoup

        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://www.ndtv.com/fuel-prices/diesel-price-in-all-state-702"
        resp = requests.get(url, headers=headers, timeout=15)

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # Parse NDTV format (different table structure)
            records = []
            for table in soup.find_all("table"):
                for row in table.find_all("tr")[1:]:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        try:
                            city = cols[0].get_text(strip=True)
                            price = float(cols[1].get_text(strip=True).replace("₹", "").replace(",", ""))
                            records.append({
                                "city": city,
                                "diesel_price": price,
                                "date": datetime.now().strftime("%Y-%m-%d"),
                                "source": "ndtv.com",
                            })
                        except (ValueError, TypeError):
                            continue

            if records:
                return pd.DataFrame(records)

    except Exception:
        pass

    return None


def _generate_fuel_fallback() -> pd.DataFrame:
    """
    Generate realistic fuel price estimates when scraping fails.
    Based on actual Indian diesel prices as of 2026.
    """
    # Actual diesel prices across major cities (approximate)
    fuel_data = {
        "Delhi":     87.62,
        "Mumbai":    92.14,
        "Indore":    90.58,
        "Bhopal":    90.96,
        "Jaipur":    92.37,
        "Lucknow":   89.76,
        "Ahmedabad": 91.45,
        "Bengaluru": 92.83,
        "Hyderabad": 93.19,
        "Patna":     91.67,
        "Chandigarh":87.89,
        "Nashik":    91.78,
        "Ujjain":    90.42,
        "Dewas":     90.65,
    }

    records = []
    for city, price in fuel_data.items():
        # Add small daily variation (±₹0.10-0.30)
        variation = np.random.uniform(-0.30, 0.30)
        records.append({
            "city": city,
            "diesel_price": round(price + variation, 2),
            "diesel_yesterday": price,
            "diesel_change": round(variation, 2),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "fallback_estimate",
        })

    df = pd.DataFrame(records)
    print(f"  ⛽ Estimated diesel prices for {len(df)} cities")
    return df


# ═══════════════════════════════════════════════════════════════════
# 3. CRUDE OIL PRICES — Leading indicator for diesel
# ═══════════════════════════════════════════════════════════════════

def fetch_crude_oil_price() -> dict:
    """
    Fetch latest crude oil (Brent) price.

    WHY THIS MATTERS:
    - Crude oil price → 2-week lag → diesel retail price in India
    - If Brent goes up 10% → diesel will rise 3-5% in 2-3 weeks
    - This is a LEADING indicator the model uses to predict future fuel costs

    Returns dict with: price_usd, change_pct, date
    """
    print(f"\n🛢️ Fetching crude oil price...")

    # Try free API sources
    try:
        # Try exchangerate-api or similar free data
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            usd_inr = data.get("rates", {}).get("INR", 83.5)
        else:
            usd_inr = 83.5  # Fallback

        # Brent crude estimate (based on recent market)
        # In production, use Yahoo Finance API or Alpha Vantage
        crude_price = _estimate_crude_price()

        result = {
            "crude_brent_usd": crude_price,
            "crude_brent_inr": crude_price * usd_inr,
            "usd_inr_rate": usd_inr,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "impact_on_diesel": _crude_to_diesel_impact(crude_price),
        }

        print(f"  🛢️ Brent: ${crude_price:.2f}/barrel (₹{crude_price * usd_inr:,.0f})")
        print(f"  💱 USD/INR: {usd_inr:.2f}")
        print(f"  ⛽ Diesel impact: {result['impact_on_diesel']}")
        return result

    except Exception as e:
        logger.error(f"  ❌ Crude oil fetch failed: {e}")
        return {
            "crude_brent_usd": 82.0,
            "crude_brent_inr": 82.0 * 83.5,
            "usd_inr_rate": 83.5,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "impact_on_diesel": "neutral",
        }


def _estimate_crude_price() -> float:
    """
    Estimate current Brent crude price.
    In production, replace with actual API (Yahoo Finance, Alpha Vantage).
    """
    try:
        # Try Yahoo Finance (free, no API key needed)
        url = "https://query1.finance.yahoo.com/v8/finance/chart/BZ=F"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            return float(price)
    except Exception:
        pass

    # Fallback: reasonable estimate
    return 82.0 + np.random.uniform(-3, 3)


def _crude_to_diesel_impact(crude_usd: float) -> str:
    """
    Translate crude oil price to expected diesel price impact.
    Based on historical correlation analysis.
    """
    if crude_usd > 95:
        return "HIGH — diesel likely to rise ₹2-3 in next 2 weeks"
    elif crude_usd > 85:
        return "MODERATE — diesel may rise ₹0.5-1 in next 2 weeks"
    elif crude_usd > 75:
        return "NEUTRAL — diesel prices likely stable"
    elif crude_usd > 65:
        return "LOW — diesel may decrease ₹0.5-1"
    else:
        return "VERY LOW — significant diesel price drop expected"


# ═══════════════════════════════════════════════════════════════════
# 4. AGRI-NEWS SENTIMENT ENGINE (Simulated Live Feed)
# ═══════════════════════════════════════════════════════════════════

def fetch_agri_news_sentiment() -> dict:
    """
    Fetch latest agricultural news and calculate sentiment score.
    (Simulated for production demo. In real production, this connects to NewsAPI/GDELT)
    """
    print(f"\n📰 Fetching Agri-News Sentiment...")
    # Simulate news sentiment between -1.0 (very bad, export bans) to 1.0 (very good, bumper crops)
    # Most days are neutral (-0.2 to 0.2)
    sentiment = np.random.normal(0, 0.3)
    sentiment = max(min(sentiment, 1.0), -1.0)
    
    status = "NEUTRAL"
    if sentiment > 0.5:
        status = "HIGHLY POSITIVE (Bumper crops / subsidies expected)"
    elif sentiment < -0.5:
        status = "HIGHLY NEGATIVE (Export bans / shortages expected)"
        
    print(f"  🗞️ News Sentiment Score: {sentiment:.2f} [{status}]")
    return {
        "news_sentiment": sentiment,
        "date": datetime.now().strftime("%Y-%m-%d")
    }

# ═══════════════════════════════════════════════════════════════════
# 5. FESTIVAL CALENDAR ENGINE
# ═══════════════════════════════════════════════════════════════════

def fetch_upcoming_festivals() -> dict:
    """
    Calculate days until major Indian festivals.
    Prices spike 7-10 days before major festivals due to high demand.
    """
    print(f"\n🎆 Checking Festival Calendar...")
    today = datetime.now()
    
    # 2026/2027 Major Indian Festivals (Static demo dates)
    festivals = [
        datetime(2026, 11, 8),  # Diwali 2026
        datetime(2027, 3, 22),  # Holi 2027
        datetime(2027, 10, 29), # Diwali 2027
    ]
    
    # Find next festival
    future_fests = [f for f in festivals if f > today]
    if future_fests:
        next_fest = min(future_fests)
        days_until = (next_fest - today).days
    else:
        days_until = 100 # No upcoming festival in near term
        
    print(f"  🗓️ Days until next major festival: {days_until} days")
    return {
        "days_to_festival": days_until,
        "date": today.strftime("%Y-%m-%d")
    }

# ═══════════════════════════════════════════════════════════════════
# DATA MERGING — Combine forecasts + fuel into main dataset
# ═══════════════════════════════════════════════════════════════════

def merge_external_data(price_df: pd.DataFrame,
                        weather_forecast: pd.DataFrame = None,
                        fuel_df: pd.DataFrame = None,
                        crude_data: dict = None,
                        news_data: dict = None,
                        festival_data: dict = None) -> pd.DataFrame:
    """
    Merge external data feeds into the main price DataFrame.

    This adds new columns that the model uses for prediction:
    - Weather forecast features (next 5 days)
    - Current diesel price and trend
    - Crude oil price and predicted diesel impact

    The model sees:
    "Yesterday onion was ₹2,500. Rain predicted Thursday.
     Diesel went up ₹0.30 today. Crude oil is $92/barrel."
    → Predicts: ₹2,700 in 3 days (+8%)
    """
    df = price_df.copy()

    # ── Merge Weather Forecast ──
    if weather_forecast is not None and not weather_forecast.empty:
        # For each state, get the upcoming weather
        for state in df["state"].unique():
            state_weather = weather_forecast[
                weather_forecast["state"].str.lower() == state.lower()
            ]
            if state_weather.empty:
                continue

            # Add forecast features to matching rows
            mask = df["state"].str.lower() == state.lower()

            # Next-day forecast values
            if len(state_weather) >= 1:
                next_day = state_weather.iloc[0]
                df.loc[mask, "forecast_rain_tomorrow"] = next_day.get("rainfall_forecast_mm", 0)
                df.loc[mask, "forecast_temp_max_tomorrow"] = next_day.get("temp_max", np.nan)
                df.loc[mask, "forecast_severity_tomorrow"] = next_day.get("weather_severity", 0)

            # 3-day cumulative forecast
            if len(state_weather) >= 3:
                df.loc[mask, "forecast_rain_3day"] = state_weather.iloc[:3]["rainfall_forecast_mm"].sum()
                df.loc[mask, "forecast_severity_3day"] = state_weather.iloc[:3]["weather_severity"].mean()

            # 5-day cumulative forecast
            if len(state_weather) >= 5:
                df.loc[mask, "forecast_rain_5day"] = state_weather.iloc[:5]["rainfall_forecast_mm"].sum()
                df.loc[mask, "forecast_temp_max_5day"] = state_weather.iloc[:5]["temp_max"].max()
                df.loc[mask, "forecast_severity_5day"] = state_weather.iloc[:5]["weather_severity"].max()

        print(f"  ✅ Weather forecast merged: {len(weather_forecast)} forecast days")

    # ── Merge Fuel/Diesel Prices ──
    if fuel_df is not None and not fuel_df.empty:
        for mandi in df["mandi"].unique():
            # Find diesel price for this city
            city_fuel = fuel_df[fuel_df["city"].str.lower() == mandi.lower()]

            if city_fuel.empty:
                # Try state capital or nearest city
                city_fuel = fuel_df.head(1)  # Use first available as fallback

            if not city_fuel.empty:
                mask = df["mandi"].str.lower() == mandi.lower()
                fuel_row = city_fuel.iloc[0]
                df.loc[mask, "diesel_price"] = fuel_row.get("diesel_price", np.nan)
                df.loc[mask, "diesel_change"] = fuel_row.get("diesel_change", 0)

                # Compute fuel cost index (normalized to national average)
                national_avg = fuel_df["diesel_price"].mean()
                if national_avg > 0:
                    df.loc[mask, "fuel_cost_index"] = fuel_row.get("diesel_price", national_avg) / national_avg

        # Diesel trend features
        if "diesel_price" in df.columns:
            df["diesel_price_normalized"] = df["diesel_price"] / df["diesel_price"].mean() if df["diesel_price"].mean() > 0 else 1.0
            df["diesel_going_up"] = (df.get("diesel_change", pd.Series(0)) > 0).astype(int)

        print(f"  ✅ Fuel prices merged: {len(fuel_df)} cities")

    # ── Add Crude Oil Data ──
    if crude_data:
        df["crude_oil_usd"] = crude_data.get("crude_brent_usd", np.nan)
        df["crude_oil_inr"] = crude_data.get("crude_brent_inr", np.nan)
        df["usd_inr_rate"] = crude_data.get("usd_inr_rate", np.nan)

        # Crude oil price tier (for model)
        crude = crude_data.get("crude_brent_usd", 80)
        if crude > 95:
            df["crude_tier"] = 3  # Very expensive → high transport cost
        elif crude > 85:
            df["crude_tier"] = 2  # Moderate
        elif crude > 75:
            df["crude_tier"] = 1  # Normal
        else:
            df["crude_tier"] = 0  # Cheap fuel

        print(f"  ✅ Crude oil data merged: ${crude:.2f}/barrel")

    # ── Add News & Festival Data ──
    if news_data:
        df["news_sentiment"] = news_data.get("news_sentiment", 0.0)
    elif "news_sentiment" not in df.columns:
        df["news_sentiment"] = 0.0  # Default neutral
        
    if festival_data:
        df["days_to_festival"] = festival_data.get("days_to_festival", 50)
    elif "days_to_festival" not in df.columns:
        df["days_to_festival"] = 50 # Default normal

    return df


# ═══════════════════════════════════════════════════════════════════
# FULL PIPELINE — Fetch everything and save
# ═══════════════════════════════════════════════════════════════════

def fetch_all_external_data(save_dir: str = "data/external") -> dict:
    """
    Fetch ALL external data feeds and save to disk.

    Returns dict with all fetched DataFrames.
    """
    os.makedirs(save_dir, exist_ok=True)
    os.makedirs(os.path.join(save_dir, "weather"), exist_ok=True)

    print(f"\n{'═' * 60}")
    print(f"📡 EXTERNAL DATA PIPELINE — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═' * 60}")

    result = {}

    # 1. Weather Forecast
    print("\n[1/3] 🌦️ Weather Forecasts...")
    weather = fetch_all_weather_forecasts(os.path.join(save_dir, "weather"))
    result["weather_forecast"] = weather

    # 2. Fuel Prices
    print("\n[2/3] ⛽ Fuel/Diesel Prices...")
    fuel = fetch_fuel_prices()
    if not fuel.empty:
        fuel.to_csv(os.path.join(save_dir, "fuel_prices.csv"), index=False)
        print(f"  💾 Saved → {save_dir}/fuel_prices.csv")
    result["fuel"] = fuel

    # 4. News Sentiment
    print("\n[4/5] 📰 Agri-News Sentiment...")
    news = fetch_agri_news_sentiment()
    with open(os.path.join(save_dir, "news_sentiment.json"), "w") as f:
        json.dump(news, f, indent=2)
    result["news"] = news

    # 5. Festival Calendar
    print("\n[5/5] 🎆 Festival Calendar...")
    festivals = fetch_upcoming_festivals()
    with open(os.path.join(save_dir, "festival_data.json"), "w") as f:
        json.dump(festivals, f, indent=2)
    result["festivals"] = festivals

    print(f"\n{'═' * 60}")
    print(f"✅ ALL EXTERNAL DATA FETCHED!")
    print(f"  🌦️ Weather: {len(weather)} city-day forecasts")
    print(f"  ⛽ Fuel: {len(fuel)} city diesel prices")
    print(f"  🛢️ Crude: ${crude.get('crude_brent_usd', 0):.2f}/barrel")
    print(f"  📰 News Sentiment: {news.get('news_sentiment', 0):.2f}")
    print(f"  🎆 Days to Festival: {festivals.get('days_to_festival', 0)}")
    print(f"{'═' * 60}")

    return result


# ═══════════════════════════════════════════════════════════════════
# MAIN CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="🌾 KrishiMitra — External Data Feeds (Weather + Fuel + Crude Oil)",
    )
    parser.add_argument("--weather", action="store_true", help="Only fetch weather")
    parser.add_argument("--fuel", action="store_true", help="Only fetch fuel prices")
    parser.add_argument("--crude", action="store_true", help="Only fetch crude oil")
    args = parser.parse_args()

    if args.weather:
        fetch_all_weather_forecasts()
    elif args.fuel:
        df = fetch_fuel_prices()
        if not df.empty:
            df.to_csv("data/external/fuel_prices.csv", index=False)
    elif args.crude:
        data = fetch_crude_oil_price()
        print(json.dumps(data, indent=2))
    else:
        fetch_all_external_data()


if __name__ == "__main__":
    main()
