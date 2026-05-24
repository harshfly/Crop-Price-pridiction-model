# ═══════════════════════════════════════════════════════════════════
# KrishiMitra AI — Live AGMARKNET Price Scraper
# Fetches real-time mandi prices from data.gov.in official API
# ═══════════════════════════════════════════════════════════════════
#
# DATA SOURCE: data.gov.in — Ministry of Agriculture
# API: "Current Daily Price of Various Commodities from Various Markets"
# Resource ID: 9ef84268-d588-465a-a308-a864a43d0070
#
# This is the OFFICIAL Government of India API — free, reliable, and legal.
# Returns: State, District, Market, Commodity, Variety, Grade,
#          Arrival_Date, Min_Price, Max_Price, Modal_Price
#
# USAGE:
#   python -m src.scraper                    # Fetch today's prices
#   python -m src.scraper --days 30          # Fetch last 30 days
#   python -m src.scraper --commodity Onion  # Fetch specific crop
# ═══════════════════════════════════════════════════════════════════

import os
import time
import argparse
import logging
from datetime import datetime, timedelta
from typing import Optional

import requests
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

logger = logging.getLogger("krishimitra.scraper")

# ════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════════

# data.gov.in API details
DATA_GOV_API_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
DATA_GOV_API_KEY = os.getenv(
    "DATA_GOV_API_KEY",
    "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"  # Public demo key
)

# Commodities we track (matches KrishiMitra crops)
TRACKED_COMMODITIES = [
    "Onion", "Potato", "Tomato", "Wheat", "Garlic",
    "Ginger (Green)", "Bengal Gram(Gram)(Whole)",
    "Maize", "Arhar (Tur/Red Gram)(Whole)", "Soyabean",
    "Rice", "Green Chilli", "Capsicum", "Cauliflower",
    "Cabbage", "Brinjal", "Banana", "Apple", "Mango",
    "Lemon", "Coriander(Leaves)", "Cumin Seed(Jeera)",
    "Turmeric", "Red Chillies", "Groundnut",
    "Cotton", "Sugarcane", "Mustard",
]

# States we focus on (can expand later)
TRACKED_STATES = [
    "Madhya Pradesh", "Maharashtra", "Rajasthan",
    "Uttar Pradesh", "Gujarat", "Karnataka",
    "Andhra Pradesh", "Tamil Nadu", "Punjab",
    "Haryana", "Bihar", "West Bengal",
    "Chhattisgarh", "Uttarakhand", "Telangana",
]

# Max records per API call (data.gov.in caps at ~10,000)
MAX_RECORDS_PER_CALL = 1000


# ════════════════════════════════════════════════════════════════════
# CORE SCRAPER — Fetch from data.gov.in API
# ════════════════════════════════════════════════════════════════════

def fetch_mandi_prices(
    commodity: Optional[str] = None,
    state: Optional[str] = None,
    market: Optional[str] = None,
    limit: int = MAX_RECORDS_PER_CALL,
    offset: int = 0,
) -> list[dict]:
    """
    Fetch daily mandi prices from the official data.gov.in API.

    This is a FREE government API — no registration needed.
    Returns real-time prices from 12,000+ mandis across India.

    Args:
        commodity: Filter by crop name (e.g., "Onion")
        state: Filter by state (e.g., "Madhya Pradesh")
        market: Filter by market name (e.g., "Indore")
        limit: Max records to fetch (default 1000)
        offset: Pagination offset

    Returns:
        List of dicts with price data
    """
    params = {
        "api-key": DATA_GOV_API_KEY,
        "format": "json",
        "limit": limit,
        "offset": offset,
    }

    # Add optional filters
    if commodity:
        params["filters[commodity]"] = commodity
    if state:
        params["filters[state.keyword]"] = state
    if market:
        params["filters[market]"] = market

    try:
        response = requests.get(DATA_GOV_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        records = data.get("records", [])
        total = data.get("total", 0)

        logger.info(f"📥 Fetched {len(records)} records (total available: {total})")
        return records

    except requests.exceptions.Timeout:
        logger.error("⏰ API request timed out. Retrying...")
        time.sleep(5)
        return fetch_mandi_prices(commodity, state, market, limit, offset)

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ API request failed: {e}")
        return []


def fetch_all_prices(
    commodity: Optional[str] = None,
    state: Optional[str] = None,
    max_records: int = 10000,
) -> pd.DataFrame:
    """
    Fetch ALL available prices with automatic pagination.

    The API returns max ~1000 records per call, so we paginate
    through all results automatically.

    Returns:
        DataFrame with all fetched price records
    """
    all_records = []
    offset = 0
    batch_size = MAX_RECORDS_PER_CALL

    print(f"\n🌾 Fetching mandi prices...")
    if commodity:
        print(f"   Commodity: {commodity}")
    if state:
        print(f"   State: {state}")

    while offset < max_records:
        records = fetch_mandi_prices(
            commodity=commodity,
            state=state,
            limit=batch_size,
            offset=offset,
        )

        if not records:
            break

        all_records.extend(records)
        offset += batch_size

        # Rate limiting — be nice to the government API
        time.sleep(0.5)

        if len(records) < batch_size:
            break  # No more data

    if not all_records:
        logger.warning("⚠️ No records fetched!")
        return pd.DataFrame()

    df = _normalize_records(all_records)
    print(f"✅ Total fetched: {len(df)} records")
    return df


def fetch_prices_for_tracked_crops() -> pd.DataFrame:
    """
    Fetch today's prices for ALL tracked commodities.
    This is the function called by the scheduler every 4 hours.
    """
    all_dfs = []

    print(f"\n{'═' * 60}")
    print(f"🌾 LIVE PRICE FETCH — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═' * 60}")

    for commodity in tqdm(TRACKED_COMMODITIES, desc="Fetching crops"):
        try:
            df = fetch_all_prices(commodity=commodity, max_records=5000)
            if not df.empty:
                all_dfs.append(df)
                print(f"  ✅ {commodity}: {len(df)} records")
        except Exception as e:
            logger.error(f"  ❌ {commodity} failed: {e}")

        # Rate limiting between commodity calls
        time.sleep(1)

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["date", "crop", "mandi", "state"],
        keep="last"
    )

    print(f"\n🎉 Total: {len(combined)} records across {combined['crop'].nunique()} crops")
    return combined


# ════════════════════════════════════════════════════════════════════
# DATA NORMALIZATION  — Clean raw API response
# ════════════════════════════════════════════════════════════════════

def _normalize_records(records: list[dict]) -> pd.DataFrame:
    """
    Normalize raw API records into a clean DataFrame.

    API returns fields like:
    {state, district, market, commodity, variety, grade,
     arrival_date, min_price, max_price, modal_price}

    We rename and clean them for consistency.
    """
    df = pd.DataFrame(records)

    if df.empty:
        return df

    # Rename columns to our standard format
    rename_map = {
        "state": "state",
        "district": "district",
        "market": "mandi",
        "commodity": "crop",
        "variety": "variety",
        "grade": "grade",
        "arrival_date": "date",
        "min_price": "min_price",
        "max_price": "max_price",
        "modal_price": "modal_price",
    }
    df = df.rename(columns=rename_map)

    # Parse dates (format: "14/04/2026")
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y", errors="coerce")

    # Convert prices to float
    for col in ["min_price", "max_price", "modal_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Clean string columns
    for col in ["crop", "mandi", "state", "district"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()

    # Drop rows with missing essential data
    df = df.dropna(subset=["date", "modal_price"])

    # Add metadata
    df["source"] = "data.gov.in"
    df["fetched_at"] = datetime.utcnow()

    # Sort by date
    df = df.sort_values("date", ascending=False).reset_index(drop=True)

    return df


# ════════════════════════════════════════════════════════════════════
# DATABASE STORAGE — Save fetched prices to PostgreSQL
# ════════════════════════════════════════════════════════════════════

def save_to_database(df: pd.DataFrame) -> int:
    """
    Save fetched price records to the PostgreSQL database.

    Uses SQLAlchemy to insert records, skipping duplicates.
    Returns the number of new records inserted.
    """
    if df.empty:
        return 0

    try:
        from api.database import SessionLocal, Price

        session = SessionLocal()
        inserted = 0

        for _, row in df.iterrows():
            # Check if record already exists (same date + crop + mandi)
            exists = session.query(Price).filter(
                Price.date == row["date"].date() if hasattr(row["date"], "date") else row["date"],
                Price.crop == row["crop"],
                Price.mandi == row["mandi"],
            ).first()

            if not exists:
                price = Price(
                    date=row["date"].date() if hasattr(row["date"], "date") else row["date"],
                    crop=row["crop"],
                    mandi=row["mandi"],
                    state=row.get("state", ""),
                    district=row.get("district", ""),
                    min_price=row.get("min_price"),
                    max_price=row.get("max_price"),
                    modal_price=row["modal_price"],
                    source="data.gov.in",
                )
                session.add(price)
                inserted += 1

        session.commit()
        session.close()

        logger.info(f"💾 Inserted {inserted} new records to database")
        return inserted

    except Exception as e:
        logger.error(f"❌ Database save failed: {e}")
        logger.info("💡 Tip: Make sure PostgreSQL is running and DATABASE_URL is set in .env")
        return 0


def save_to_csv(df: pd.DataFrame, output_dir: str = "data/raw") -> str:
    """
    Save fetched prices to CSV file as backup.
    Creates one file per day: prices_2026-04-14.csv
    """
    if df.empty:
        return ""

    os.makedirs(output_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(output_dir, f"prices_{today}.csv")

    if os.path.exists(filepath):
        # Append to existing file
        existing = pd.read_csv(filepath, parse_dates=["date"])
        df = pd.concat([existing, df], ignore_index=True)
        df = df.drop_duplicates(subset=["date", "crop", "mandi", "state"], keep="last")

    df.to_csv(filepath, index=False)
    print(f"💾 Saved to CSV → {filepath} ({len(df)} records)")
    return filepath


# ════════════════════════════════════════════════════════════════════
# HISTORICAL DATA — Fetch past prices for model training
# ════════════════════════════════════════════════════════════════════

def fetch_historical_prices(
    commodity: str = "Onion",
    state: str = "Madhya Pradesh",
    days_back: int = 365,
) -> pd.DataFrame:
    """
    Fetch historical price data by querying the API for past dates.

    Note: data.gov.in API only returns CURRENT day's prices.
    For historical data, we accumulate daily snapshots over time.
    The first time you run this, you'll only get today's data.
    After running the scheduler for 30+ days, you'll have enough
    historical data to train the model.

    For immediate historical data, download from agmarknet.gov.in manually.
    """
    print(f"\n📅 Fetching historical data for {commodity} in {state}...")
    print(f"   Note: data.gov.in API only provides TODAY's prices.")
    print(f"   Historical data accumulates as the scheduler runs daily.")
    print(f"   For immediate historical data, download CSVs from agmarknet.gov.in")

    # Fetch today's prices as a starting point
    df = fetch_all_prices(commodity=commodity, state=state)
    return df


# ════════════════════════════════════════════════════════════════════
# QUICK STATS — Show what we just fetched
# ════════════════════════════════════════════════════════════════════

def print_price_summary(df: pd.DataFrame):
    """Print a nice summary of fetched prices."""
    if df.empty:
        print("⚠️ No data to summarize")
        return

    print(f"\n{'═' * 60}")
    print(f"📊 PRICE SUMMARY — {df['date'].max().strftime('%d %b %Y') if pd.notna(df['date'].max()) else 'Today'}")
    print(f"{'═' * 60}")
    print(f"  Total records:  {len(df):,}")
    print(f"  Crops:          {df['crop'].nunique()}")
    print(f"  Markets:        {df['mandi'].nunique()}")
    print(f"  States:         {df['state'].nunique()}")

    # Top 10 crops by record count
    print(f"\n  {'Commodity':<25} {'Min ₹':<10} {'Max ₹':<10} {'Modal ₹':<10} {'Records'}")
    print(f"  {'─' * 65}")

    for crop in df["crop"].value_counts().head(15).index:
        crop_df = df[df["crop"] == crop]
        print(
            f"  {crop:<25} "
            f"₹{crop_df['min_price'].min():>7,.0f} "
            f"₹{crop_df['max_price'].max():>7,.0f} "
            f"₹{crop_df['modal_price'].median():>7,.0f} "
            f"{len(crop_df):>6}"
        )

    print(f"{'═' * 60}")


# ════════════════════════════════════════════════════════════════════
# MAIN — Command line interface
# ════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="🌾 KrishiMitra — Live AGMARKNET Price Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.scraper                          # Fetch all tracked crops
  python -m src.scraper --commodity Onion        # Fetch only onion prices
  python -m src.scraper --state "Madhya Pradesh" # Fetch one state
  python -m src.scraper --save-db                # Also save to database
        """
    )

    parser.add_argument("--commodity", type=str, help="Specific commodity to fetch")
    parser.add_argument("--state", type=str, help="Specific state to filter")
    parser.add_argument("--market", type=str, help="Specific market/mandi")
    parser.add_argument("--save-db", action="store_true", help="Save to PostgreSQL database")
    parser.add_argument("--max-records", type=int, default=10000, help="Max records to fetch")

    args = parser.parse_args()

    print("\n" + "🌾" * 30)
    print("🌾 KrishiMitra — Live AGMARKNET Price Scraper")
    print("🌾" * 30)
    print(f"📡 Source: data.gov.in (Ministry of Agriculture)")
    print(f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.commodity:
        # Fetch specific commodity
        df = fetch_all_prices(
            commodity=args.commodity,
            state=args.state,
            max_records=args.max_records,
        )
    else:
        # Fetch all tracked commodities
        df = fetch_prices_for_tracked_crops()

    if not df.empty:
        # Always save to CSV
        save_to_csv(df)

        # Optionally save to database
        if args.save_db:
            inserted = save_to_database(df)
            print(f"💾 Database: {inserted} new records inserted")

        # Show summary
        print_price_summary(df)
    else:
        print("❌ No data fetched. Check your internet connection.")


if __name__ == "__main__":
    main()
