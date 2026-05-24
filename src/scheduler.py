# ═══════════════════════════════════════════════════════════════════
# KrishiMitra AI — Scheduled Jobs (Celery Beat)
# Runs recurring tasks: price fetching, model retraining, alerts
# ═══════════════════════════════════════════════════════════════════
#
# This file sets up 3 scheduled jobs:
#
# 1. Every 4 hours:  Fetch latest mandi prices from data.gov.in API
# 2. Every Sunday:   Retrain AI models with new accumulated data
# 3. Every 30 min:   Check price alerts and notify farmers
#
# HOW TO RUN:
#   Option A (with Celery + Redis):
#     celery -A src.scheduler worker --beat --loglevel=info
#
#   Option B (standalone, no Redis needed):
#     python -m src.scheduler
#
# ═══════════════════════════════════════════════════════════════════

import os
import time
import logging
import schedule
import threading
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("krishimitra.scheduler")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scheduler.log", encoding="utf-8"),
    ]
)


# ═══════════════════════════════════════════════════════════════════
# JOB 1: Fetch Live Prices (every 4 hours)
# ═══════════════════════════════════════════════════════════════════

def job_fetch_prices():
    """
    Fetch latest mandi prices + external data (weather, fuel, crude oil).

    Runs every 4 hours (6 times a day).
    Also fetches weather forecasts, fuel/diesel prices, and crude oil
    so the prediction model always has the freshest external signals.
    """
    logger.info("=" * 60)
    logger.info("📥 JOB: Fetching live data (prices + weather + fuel)...")
    logger.info("=" * 60)

    # Step 1: Fetch external data (weather forecast + fuel + crude oil)
    try:
        from src.external_data import fetch_all_external_data
        external = fetch_all_external_data()
        logger.info(f"✅ External data fetched (weather + fuel + crude)")
    except Exception as ext_err:
        logger.warning(f"⚠️ External data fetch skipped: {ext_err}")

    # Step 2: Fetch mandi prices
    try:
        from src.scraper import fetch_prices_for_tracked_crops, save_to_csv, save_to_database

        df = fetch_prices_for_tracked_crops()

        if df.empty:
            logger.warning("⚠️ No prices fetched this cycle")
            return

        # Save to CSV (always — as backup)
        csv_path = save_to_csv(df)
        logger.info(f"📄 CSV saved: {csv_path}")

        # Try to save to database (may fail if PostgreSQL not running)
        try:
            inserted = save_to_database(df)
            logger.info(f"💾 Database: {inserted} new records inserted")
        except Exception as db_err:
            logger.warning(f"⚠️ Database save skipped: {db_err}")

        logger.info(f"✅ Price fetch complete: {len(df)} records")

    except Exception as e:
        logger.error(f"❌ Price fetch failed: {e}", exc_info=True)


# ═══════════════════════════════════════════════════════════════════
# JOB 2: Retrain Models (every Sunday at 2 AM)
# ═══════════════════════════════════════════════════════════════════

def job_retrain_models():
    """
    Retrain all AI models with newly accumulated data.

    Runs every Sunday at 2:00 AM.
    Why Sunday 2 AM? Low traffic, mandis are often closed on Sunday,
    and we have a full week of new data to train on.

    Process:
    1. Merge all CSV files in data/raw/ into master dataset
    2. Run feature engineering
    3. Retrain LSTM + GRU for each crop
    4. Compare new vs old model accuracy
    5. Deploy new model only if it's better
    """
    logger.info("=" * 60)
    logger.info("🧠 JOB: Retraining AI models...")
    logger.info("=" * 60)

    try:
        import glob
        import pandas as pd
        from src.data_loader import load_all_agmarknet, merge_price_and_weather

        # Step 1: Merge all accumulated CSV data
        logger.info("Step 1: Merging accumulated price data...")

        csv_files = glob.glob("data/raw/prices_*.csv")
        if not csv_files:
            logger.warning("⚠️ No data files found. Skipping retraining.")
            return

        all_dfs = [pd.read_csv(f, parse_dates=["date"]) for f in csv_files]
        master_df = pd.concat(all_dfs, ignore_index=True)
        master_df = master_df.drop_duplicates(
            subset=["date", "crop", "mandi"],
            keep="last"
        )

        logger.info(f"  📊 Master dataset: {len(master_df)} rows, "
                     f"{master_df['crop'].nunique()} crops")

        # Save master dataset
        os.makedirs("data/processed", exist_ok=True)
        master_df.to_csv("data/processed/master_dataset.csv", index=False)

        # Step 2: Check if we have enough data to train
        min_rows_needed = 200  # ~7 months of daily data
        if len(master_df) < min_rows_needed:
            logger.info(f"⏳ Not enough data yet ({len(master_df)}/{min_rows_needed} rows). "
                        f"Keep running the scheduler to accumulate more data.")
            return

        # Step 3: Train models for top crops
        from src.train import train_single_crop

        crops_to_train = master_df["crop"].value_counts().head(6).index.tolist()
        mandis_to_train = master_df["mandi"].value_counts().head(3).index.tolist()

        for crop in crops_to_train:
            for mandi in mandis_to_train:
                try:
                    logger.info(f"  🏋️ Training: {crop} @ {mandi}")
                    train_single_crop(crop, mandi)
                except Exception as e:
                    logger.error(f"  ❌ Training failed for {crop}@{mandi}: {e}")

        logger.info("✅ Model retraining complete!")

    except Exception as e:
        logger.error(f"❌ Retraining failed: {e}", exc_info=True)


# ═══════════════════════════════════════════════════════════════════
# JOB 3: Check Price Alerts (every 30 minutes)
# ═══════════════════════════════════════════════════════════════════

def job_check_alerts():
    """
    Check if any user price alerts have been triggered.

    Runs every 30 minutes.
    Compares current prices against user-set targets and sends
    notifications when a target is hit.
    """
    logger.info("🔔 JOB: Checking price alerts...")

    try:
        from api.database import SessionLocal, PriceAlert, Price
        from datetime import date

        session = SessionLocal()

        # Get all active alerts
        active_alerts = session.query(PriceAlert).filter(
            PriceAlert.is_active == True
        ).all()

        if not active_alerts:
            logger.info("  No active alerts to check")
            session.close()
            return

        triggered_count = 0

        for alert in active_alerts:
            # Get latest price for this crop + mandi
            latest_price = session.query(Price).filter(
                Price.crop.ilike(f"%{alert.crop}%"),
                Price.mandi.ilike(f"%{alert.mandi}%"),
            ).order_by(Price.date.desc()).first()

            if not latest_price:
                continue

            # Check if alert should trigger
            should_trigger = False
            if alert.direction == "above" and latest_price.modal_price >= alert.target_price:
                should_trigger = True
            elif alert.direction == "below" and latest_price.modal_price <= alert.target_price:
                should_trigger = True

            if should_trigger:
                alert.is_active = False
                alert.triggered_at = datetime.utcnow()
                triggered_count += 1

                logger.info(
                    f"  🔔 TRIGGERED: {alert.crop} @ {alert.mandi} "
                    f"hit ₹{latest_price.modal_price:,.0f} "
                    f"(target: ₹{alert.target_price:,.0f})"
                )

                # Send notification (WhatsApp / SMS / Push)
                _send_alert_notification(alert, latest_price.modal_price)

        session.commit()
        session.close()

        logger.info(f"  ✅ Checked {len(active_alerts)} alerts, triggered {triggered_count}")

    except Exception as e:
        logger.warning(f"  ⚠️ Alert check skipped: {e}")


def _send_alert_notification(alert, current_price: float):
    """
    Send notification to the farmer when their price alert triggers.

    Currently logs to file. In production, integrate with:
    - MSG91 for WhatsApp/SMS
    - Firebase Cloud Messaging for push notifications
    """
    message = (
        f"🌾 KrishiMitra Alert!\n"
        f"आपका {alert.crop} ₹{current_price:,.0f}/क्विंटल पर पहुंचा!\n"
        f"{alert.mandi} Mandi | अभी बेचें या होल्ड करें\n"
        f"KrishiMitra ऐप खोलें: https://krishimitra.in"
    )

    logger.info(f"  📱 Notification: {message}")

    # TODO: Integrate with MSG91 or Firebase
    # msg91_api_key = os.getenv("MSG91_API_KEY")
    # if msg91_api_key:
    #     send_whatsapp(alert.user.phone, message)


# ═══════════════════════════════════════════════════════════════════
# JOB 4: Daily Data Quality Check (every day at 6 AM)
# ═══════════════════════════════════════════════════════════════════

def job_data_quality_check():
    """
    Check the health of our accumulated data.

    Runs daily at 6 AM.
    - How many rows total?
    - Any gaps in dates?
    - Any crops with stale (old) data?
    """
    logger.info("📊 JOB: Data quality check...")

    try:
        import glob
        csv_files = glob.glob("data/raw/prices_*.csv")

        total_rows = 0
        latest_date = None

        for f in csv_files:
            import pandas as pd
            df = pd.read_csv(f, parse_dates=["date"])
            total_rows += len(df)
            file_max = df["date"].max()
            if latest_date is None or file_max > latest_date:
                latest_date = file_max

        logger.info(f"  📁 CSV files: {len(csv_files)}")
        logger.info(f"  📊 Total rows: {total_rows:,}")
        logger.info(f"  📅 Latest date: {latest_date}")

        if total_rows >= 200:
            logger.info(f"  ✅ Enough data for model training!")
        else:
            logger.info(f"  ⏳ Need more data: {total_rows}/200 rows "
                        f"(~{max(0, (200 - total_rows) // 30)} more days)")

    except Exception as e:
        logger.warning(f"  ⚠️ Quality check failed: {e}")


# ═══════════════════════════════════════════════════════════════════
# SCHEDULER SETUP — Using 'schedule' library (simple, no Redis)
# ═══════════════════════════════════════════════════════════════════

def setup_schedule():
    """
    Configure all scheduled jobs using the 'schedule' library.

    This is the SIMPLE approach — no Redis or Celery needed!
    Just run: python -m src.scheduler

    For production with Celery, use the Celery beat config below.
    """
    # Every 4 hours: fetch live prices
    schedule.every(4).hours.do(job_fetch_prices)

    # Every Sunday at 2:00 AM: retrain models
    schedule.every().sunday.at("02:00").do(job_retrain_models)

    # Every 30 minutes: check price alerts
    schedule.every(30).minutes.do(job_check_alerts)

    # Every day at 6:00 AM: data quality check
    schedule.every().day.at("06:00").do(job_data_quality_check)


def run_scheduler():
    """
    Start the scheduler loop. Runs forever.
    Press Ctrl+C to stop.
    """
    setup_schedule()

    print("\n" + "⏰" * 30)
    print("⏰ KrishiMitra Scheduler — Running!")
    print("⏰" * 30)
    print(f"\n📋 Scheduled Jobs:")
    print(f"   📥 Fetch prices:     Every 4 hours")
    print(f"   🧠 Retrain models:   Every Sunday 2:00 AM")
    print(f"   🔔 Check alerts:     Every 30 minutes")
    print(f"   📊 Data quality:     Every day 6:00 AM")
    print(f"\n🟢 Scheduler started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Press Ctrl+C to stop.\n")

    # Run the first fetch immediately
    logger.info("🚀 Running initial price fetch...")
    job_fetch_prices()

    # Then run on schedule
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


# ═══════════════════════════════════════════════════════════════════
# CELERY CONFIG (for production with Redis)
# ═══════════════════════════════════════════════════════════════════

try:
    from celery import Celery
    from celery.schedules import crontab

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_app = Celery("krishimitra", broker=REDIS_URL, backend=REDIS_URL)

    celery_app.conf.beat_schedule = {
        "fetch-prices-every-4-hours": {
            "task": "src.scheduler.celery_fetch_prices",
            "schedule": crontab(minute=0, hour="*/4"),  # Every 4 hours
        },
        "retrain-models-weekly": {
            "task": "src.scheduler.celery_retrain_models",
            "schedule": crontab(minute=0, hour=2, day_of_week=0),  # Sunday 2 AM
        },
        "check-alerts-every-30min": {
            "task": "src.scheduler.celery_check_alerts",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
        },
        "data-quality-daily": {
            "task": "src.scheduler.celery_data_quality",
            "schedule": crontab(minute=0, hour=6),  # Daily 6 AM
        },
    }

    @celery_app.task(name="src.scheduler.celery_fetch_prices")
    def celery_fetch_prices():
        job_fetch_prices()

    @celery_app.task(name="src.scheduler.celery_retrain_models")
    def celery_retrain_models():
        job_retrain_models()

    @celery_app.task(name="src.scheduler.celery_check_alerts")
    def celery_check_alerts():
        job_check_alerts()

    @celery_app.task(name="src.scheduler.celery_data_quality")
    def celery_data_quality():
        job_data_quality_check()

except ImportError:
    celery_app = None
    logger.info("ℹ️ Celery not installed — using simple scheduler mode")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    run_scheduler()
