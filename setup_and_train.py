# ═══════════════════════════════════════════════════════════════════
# KrishiMitra AI — Auto Setup & Download Script
# ONE COMMAND to download data, prepare features, and train models
# ═══════════════════════════════════════════════════════════════════
#
# USAGE:
#   python setup_and_train.py              # Full auto setup
#   python setup_and_train.py --skip-train # Only download data
#   python setup_and_train.py --crop Onion # Train specific crop
#
# WHAT THIS DOES:
#   Step 1: Create all necessary folders
#   Step 2: Download LIVE mandi prices from data.gov.in API (FREE)
#   Step 3: Download historical data from data.gov.in (bulk)
#   Step 4: Fetch weather forecast + fuel prices
#   Step 5: Merge everything into master dataset
#   Step 6: Train AI models
# ═══════════════════════════════════════════════════════════════════

import os
import sys
import time
import json
import argparse
import subprocess
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════════════
# STEP 1: Create Project Folders
# ═══════════════════════════════════════════════════════════════════

def setup_folders():
    """Create all necessary folders if they don't exist."""
    folders = [
        "data/raw",
        "data/processed",
        "data/external/weather",
        "models/saved",
        "logs",
    ]
    print("\n📁 Step 1: Creating project folders...")
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"  ✅ {folder}/")

    # Create .env if missing
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            import shutil
            shutil.copy(".env.example", ".env")
            print("  ✅ .env created from .env.example")
        else:
            with open(".env", "w") as f:
                f.write("# KrishiMitra AI — Environment\n")
                f.write("DATA_GOV_API_KEY=579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b\n")
                f.write("OPENWEATHER_API_KEY=\n")
                f.write("MODEL_DIR=models/saved\n")
            print("  ✅ .env created with default API key")


# ═══════════════════════════════════════════════════════════════════
# STEP 2: Install Python Dependencies
# ═══════════════════════════════════════════════════════════════════

def install_dependencies():
    """Install required Python packages."""
    print("\n📦 Step 2: Installing dependencies...")

    # Core packages needed for data download
    core_packages = [
        "requests", "pandas", "numpy", "tqdm",
        "python-dotenv", "beautifulsoup4", "scipy",
        "scikit-learn", "joblib", "matplotlib",
    ]

    # ML packages (install separately — they're large)
    ml_packages = [
        "tensorflow", "xgboost", "lightgbm", "shap",
    ]

    for pkg in core_packages:
        try:
            __import__(pkg.replace("-", "_").split("[")[0])
        except ImportError:
            print(f"  📥 Installing {pkg}...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg, "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    print("  ✅ Core packages ready")

    # Check ML packages
    missing_ml = []
    for pkg in ml_packages:
        try:
            __import__(pkg)
        except ImportError:
            missing_ml.append(pkg)

    if missing_ml:
        print(f"\n  ⚠️ ML packages not installed: {', '.join(missing_ml)}")
        print(f"  Run: pip install {' '.join(missing_ml)}")
        print(f"  (These are needed for training, not for data download)")
        return False

    print("  ✅ ML packages ready")
    return True


# ═══════════════════════════════════════════════════════════════════
# STEP 3: Auto-Download Data from data.gov.in API (FREE)
# ═══════════════════════════════════════════════════════════════════

def download_live_data():
    """
    Download live mandi prices from the FREE data.gov.in API.

    This API is:
    - 100% FREE — no payment, no credit card
    - OFFICIAL — Government of India, Ministry of Agriculture
    - 12,000+ mandis across India
    - Real-time daily prices for 200+ commodities
    """
    print("\n" + "═" * 60)
    print("📡 Step 3: Downloading LIVE data from data.gov.in")
    print("═" * 60)
    print("  Source: Official Government of India API")
    print("  Cost: FREE (no API key purchase needed)")
    print("  Data: Real-time daily prices from 12,000+ mandis\n")

    import requests
    import pandas as pd
    from tqdm import tqdm

    API_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    API_KEY = os.getenv(
        "DATA_GOV_API_KEY",
        "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
    )

    # Crops to download
    crops = [
        "Onion", "Potato", "Tomato", "Wheat", "Garlic",
        "Ginger (Green)", "Maize", "Soyabean", "Rice",
        "Green Chilli", "Capsicum", "Cauliflower",
        "Cabbage", "Brinjal", "Banana", "Apple",
        "Lemon", "Turmeric", "Mustard", "Cotton",
    ]

    all_records = []

    for crop in tqdm(crops, desc="Downloading crops"):
        try:
            offset = 0
            while offset < 5000:
                params = {
                    "api-key": API_KEY,
                    "format": "json",
                    "limit": 1000,
                    "offset": offset,
                    "filters[commodity]": crop,
                }

                resp = requests.get(API_URL, params=params, timeout=30)
                if resp.status_code != 200:
                    break

                data = resp.json()
                records = data.get("records", [])

                if not records:
                    break

                all_records.extend(records)
                offset += 1000

                if len(records) < 1000:
                    break

                time.sleep(0.3)  # Rate limiting

        except Exception as e:
            print(f"  ⚠️ {crop}: {e}")

        time.sleep(0.5)

    if not all_records:
        print("❌ No data received from API. Check internet connection.")
        return None

    # Process records into DataFrame
    df = pd.DataFrame(all_records)

    # Rename columns
    rename = {
        "state": "state", "district": "district",
        "market": "mandi", "commodity": "crop",
        "variety": "variety", "grade": "grade",
        "arrival_date": "date",
        "min_price": "min_price",
        "max_price": "max_price",
        "modal_price": "modal_price",
    }
    df = df.rename(columns=rename)

    # Clean data
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y", errors="coerce")
    for col in ["min_price", "max_price", "modal_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["crop", "mandi", "state", "district"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()

    df = df.dropna(subset=["date", "modal_price"])
    df = df.drop_duplicates(subset=["date", "crop", "mandi", "state"], keep="last")
    df = df.sort_values("date").reset_index(drop=True)

    # Save
    filepath = "data/raw/prices_live_download.csv"
    df.to_csv(filepath, index=False)

    print(f"\n  ✅ Downloaded: {len(df):,} records")
    print(f"  📊 Crops: {df['crop'].nunique()}")
    print(f"  🏪 Markets: {df['mandi'].nunique()}")
    print(f"  📅 Date range: {df['date'].min().strftime('%d %b %Y')} → {df['date'].max().strftime('%d %b %Y')}")
    print(f"  💾 Saved → {filepath}")

    return df


# ═══════════════════════════════════════════════════════════════════
# STEP 4: Download HISTORICAL data (bulk, for training)
# ═══════════════════════════════════════════════════════════════════

def download_historical_data():
    """
    Download bulk historical data from multiple data.gov.in resources.

    data.gov.in has MULTIPLE datasets for commodity prices:
    - Current daily prices (what we use above)
    - Historical monthly data
    - State-wise aggregates

    We download as much as the API provides.
    """
    print("\n" + "═" * 60)
    print("📜 Step 4: Downloading historical bulk data")
    print("═" * 60)

    import requests
    import pandas as pd

    API_KEY = os.getenv(
        "DATA_GOV_API_KEY",
        "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
    )

    # Additional data.gov.in resources for historical prices
    HISTORICAL_RESOURCES = [
        {
            "name": "Daily Commodity Prices (Current)",
            "resource_id": "9ef84268-d588-465a-a308-a864a43d0070",
            "max_records": 30000,
        },
        {
            "name": "Daily Commodity Prices (Alternate)",
            "resource_id": "35985678-0d79-46b4-9ed6-6f13308a1d24",
            "max_records": 20000,
        },
    ]

    all_data = []

    for source in HISTORICAL_RESOURCES:
        print(f"\n  📥 {source['name']}...")
        url = f"https://api.data.gov.in/resource/{source['resource_id']}"
        offset = 0
        source_records = 0

        while offset < source["max_records"]:
            try:
                params = {
                    "api-key": API_KEY,
                    "format": "json",
                    "limit": 1000,
                    "offset": offset,
                }
                resp = requests.get(url, params=params, timeout=30)
                if resp.status_code != 200:
                    break

                data = resp.json()
                records = data.get("records", [])

                if not records:
                    break

                all_data.extend(records)
                source_records += len(records)
                offset += 1000

                if len(records) < 1000:
                    break

                time.sleep(0.3)

            except Exception as e:
                print(f"    ⚠️ Error at offset {offset}: {e}")
                break

        print(f"    Got {source_records:,} records")

    if not all_data:
        print("  ⚠️ No historical data available from API")
        return None

    df = pd.DataFrame(all_data)

    # Try common column names, preventing duplicates
    col_map = {}
    used_targets = set()
    
    for col in df.columns:
        cl = col.lower().strip()
        target = None
        
        if "commodity" in cl: target = "crop"
        elif "market" in cl: target = "mandi"
        elif "state" in cl and "district" not in cl: target = "state"
        elif "district" in cl: target = "district"
        elif "modal" in cl and "price" in cl: target = "modal_price"
        elif "min" in cl and "price" in cl: target = "min_price"
        elif "max" in cl and "price" in cl: target = "max_price"
        elif "date" in cl or "arrival" in cl: target = "date"
        
        if target and target not in used_targets:
            col_map[col] = target
            used_targets.add(target)

    df = df.rename(columns=col_map)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    if "modal_price" in df.columns:
        df["modal_price"] = pd.to_numeric(df["modal_price"], errors="coerce")
    if "min_price" in df.columns:
        df["min_price"] = pd.to_numeric(df["min_price"], errors="coerce")
    if "max_price" in df.columns:
        df["max_price"] = pd.to_numeric(df["max_price"], errors="coerce")

    for col in ["crop", "mandi", "state"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()

    df = df.dropna(subset=["modal_price"])
    df = df.drop_duplicates()

    filepath = "data/raw/prices_historical_bulk.csv"
    df.to_csv(filepath, index=False)

    print(f"\n  ✅ Historical data: {len(df):,} records")
    print(f"  💾 Saved → {filepath}")

    return df


# ═══════════════════════════════════════════════════════════════════
# STEP 5: Fetch External Data (Weather + Fuel + Crude Oil)
# ═══════════════════════════════════════════════════════════════════

def fetch_external():
    """Fetch weather forecasts, fuel prices, and crude oil data."""
    print("\n" + "═" * 60)
    print("🌦️ Step 5: Fetching external data (weather + fuel)")
    print("═" * 60)

    try:
        from src.external_data import fetch_all_external_data
        external = fetch_all_external_data()
        return external
    except Exception as e:
        print(f"  ⚠️ External data fetch skipped: {e}")
        print(f"  (Not critical — model can train without it)")
        return None


# ═══════════════════════════════════════════════════════════════════
# STEP 6: Build Master Dataset
# ═══════════════════════════════════════════════════════════════════

def build_master_dataset():
    """
    Merge all downloaded CSV files into one master dataset.
    This is what the model trains on.
    """
    print("\n" + "═" * 60)
    print("🔀 Step 6: Building master dataset")
    print("═" * 60)

    import pandas as pd
    import glob

    csv_files = glob.glob("data/raw/*.csv")
    if not csv_files:
        print("  ❌ No CSV files found in data/raw/")
        return None

    all_dfs = []
    for f in csv_files:
        try:
            df = pd.read_csv(f, parse_dates=["date"])
            all_dfs.append(df)
            print(f"  📄 {os.path.basename(f)}: {len(df):,} rows")
        except Exception as e:
            print(f"  ⚠️ Skipped {os.path.basename(f)}: {e}")

    if not all_dfs:
        print("  ❌ No valid CSV files")
        return None

    master = pd.concat(all_dfs, ignore_index=True)

    # Deduplicate
    dedup_cols = ["date", "crop", "mandi"]
    existing_cols = [c for c in dedup_cols if c in master.columns]
    if existing_cols:
        master = master.drop_duplicates(subset=existing_cols, keep="last")

    # Sort by date
    if "date" in master.columns:
        master = master.sort_values("date").reset_index(drop=True)

    # Merge with external data (fuel prices)
    fuel_path = "data/external/fuel_prices.csv"
    if os.path.exists(fuel_path):
        try:
            fuel = pd.read_csv(fuel_path)
            # Add diesel price for each mandi
            for _, row in fuel.iterrows():
                city = row.get("city", "")
                mask = master["mandi"].str.lower() == city.lower()
                if mask.any():
                    master.loc[mask, "diesel_price"] = row.get("diesel_price", None)
            print(f"  ⛽ Fuel prices merged")
        except Exception:
            pass

    # Save master dataset
    os.makedirs("data/processed", exist_ok=True)
    output = "data/processed/master_dataset.csv"
    master.to_csv(output, index=False)

    print(f"\n  ✅ Master dataset built!")
    print(f"  📊 Total rows: {len(master):,}")
    if "crop" in master.columns:
        print(f"  🌾 Crops: {master['crop'].nunique()}")
    if "mandi" in master.columns:
        print(f"  🏪 Markets: {master['mandi'].nunique()}")
    if "date" in master.columns and len(master) > 0:
        print(f"  📅 Range: {master['date'].min()} → {master['date'].max()}")
    print(f"  💾 Saved → {output}")

    return master


# ═══════════════════════════════════════════════════════════════════
# STEP 7: Train Models
# ═══════════════════════════════════════════════════════════════════

def train_models():
    """Train the Global Unified model using the master dataset."""
    print("\n" + "═" * 60)
    print("🧠 Step 7: Training Global AI Model")
    print("═" * 60)
    
    try:
        import pandas as pd
        master = pd.read_csv("data/processed/master_dataset.csv", parse_dates=["date"])
        
        if len(master) < 100:
            print(f"  ⚠️ Only {len(master)} rows in dataset. Need 100+ for training.")
            print(f"  💡 The scraper fetched today's data. For more historical data:")
            print(f"     1. Keep running the scheduler daily for 30+ days")
            print(f"     2. Or download CSVs manually from agmarknet.gov.in")
            return

        print(f"  ✅ Master dataset has {len(master)} rows. Ready for global training.")
        
    except FileNotFoundError:
        print("  ❌ Master dataset not found. Please run the scraper first.")
        return
        
    # Optional: ensure LightGBM is installed as it's the fastest
    try:
        import lightgbm
    except ImportError:
        print("  💡 Tip: Install LightGBM for faster global training: pip install lightgbm")

    try:
        from src.train_global import train_global_model
        train_global_model()
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════
# MAIN — One command to rule them all
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="🌾 KrishiMitra AI — Auto Setup, Download, and Train",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
╔═══════════════════════════════════════════════════════════╗
║  ONE COMMAND SETUP:                                       ║
║                                                           ║
║    python setup_and_train.py                              ║
║                                                           ║
║  This will:                                               ║
║    1. Create all folders                                  ║
║    2. Install missing packages                            ║
║    3. Download live data from data.gov.in (FREE)          ║
║    4. Download historical bulk data                       ║
║    5. Fetch weather forecasts + fuel prices               ║
║    6. Build master dataset                                ║
║    7. Train AI models (if enough data)                    ║
╚═══════════════════════════════════════════════════════════╝
        """
    )

    parser.add_argument("--skip-train", action="store_true",
                        help="Only download data, don't train")
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip download, only train on existing data")
    parser.add_argument("--crop", type=str,
                        help="Train specific crop (e.g., Onion)")
    parser.add_argument("--mandi", type=str, default="Indore",
                        help="Train specific mandi (default: Indore)")

    args = parser.parse_args()

    print("\n" + "🌾" * 30)
    print("🌾 KrishiMitra AI — AUTOMATIC SETUP")
    print("🌾" * 30)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📍 Working directory: {os.getcwd()}")

    start = time.time()

    # Step 1: Folders
    setup_folders()

    # Step 2: Dependencies (Skipping because sys.executable uses wrong Python alias path)
    has_ml = True

    if not args.skip_download:
        # Step 3: Download live data
        download_live_data()

        # Step 4: Download historical data
        download_historical_data()

        # Step 5: External data
        fetch_external()

    # Step 6: Build master dataset
    if args.skip_download and os.path.exists("data/processed/master_dataset.csv"):
        print("\n" + "═" * 60)
        print("🔀 Step 6: Skipping rebuild, using existing master dataset")
        print("═" * 60)
        import pandas as pd
        master = pd.read_csv("data/processed/master_dataset.csv", parse_dates=["date"])
        print(f"  ✅ Loaded existing dataset with {len(master):,} rows")
    else:
        master = build_master_dataset()

    # Step 7: Train (if not skipped and data is available)
    if not args.skip_train and has_ml and master is not None:
        train_models()
    elif args.skip_train:
        print("\n⏭️ Training skipped (--skip-train flag)")
    elif not has_ml:
        print("\n⚠️ Training skipped — install ML packages first:")
        print("  pip install tensorflow xgboost lightgbm")

    elapsed = time.time() - start

    print(f"\n{'🎉' * 20}")
    print(f"🎉 SETUP COMPLETE in {elapsed:.0f} seconds!")
    print(f"{'🎉' * 20}")

    print(f"\n📋 NEXT STEPS:")
    print(f"  1. Start scheduler for continuous data:  python -m src.scheduler")
    print(f"  2. Manual training:                      python -m src.train --crop Onion")
    print(f"  3. Start API server:                     python -m api.main")
    print(f"  4. Fetch fresh external data:            python -m src.external_data")


if __name__ == "__main__":
    main()
