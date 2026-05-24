# ═══════════════════════════════════════════════════════════════════
# KrishiMitra AI — Database Models (SQLAlchemy + TimescaleDB)
# ═══════════════════════════════════════════════════════════════════

import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, Boolean,
    DateTime, Date, Text, ARRAY, ForeignKey, Index, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
from dotenv import load_dotenv
import uuid

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://krishimitra:password@localhost:5432/krishimitra_db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════
# TABLE: prices — Daily mandi price records (TimescaleDB hypertable)
# ═══════════════════════════════════════════════════════════════════

class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    crop = Column(String(100), nullable=False, index=True)
    mandi = Column(String(100), nullable=False, index=True)
    state = Column(String(100))
    district = Column(String(100))
    min_price = Column(Float)
    max_price = Column(Float)
    modal_price = Column(Float, nullable=False)
    arrivals_qtl = Column(Float)
    source = Column(String(50), default="AGMARKNET")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_prices_crop_mandi_date", "crop", "mandi", "date"),
    )


# ═══════════════════════════════════════════════════════════════════
# TABLE: predictions — All AI predictions (for monitoring accuracy)
# ═══════════════════════════════════════════════════════════════════

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    crop = Column(String(100), nullable=False)
    mandi = Column(String(100), nullable=False)
    prediction_for_date = Column(Date, nullable=False)
    predicted_price = Column(Float, nullable=False)
    confidence_low = Column(Float)
    confidence_high = Column(Float)
    confidence_pct = Column(Float)
    actual_price = Column(Float)                    # Filled later for evaluation
    signal = Column(String(10))                     # HOLD / SELL / WAIT
    model_version = Column(String(20), default="1.0.0")
    shap_factors_json = Column(Text)                # JSON string of SHAP factors

    __table_args__ = (
        Index("idx_pred_crop_mandi", "crop", "mandi"),
    )


# ═══════════════════════════════════════════════════════════════════
# TABLE: users — Farmer profiles
# ═══════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String(15), unique=True, nullable=False)
    name = Column(String(200))
    state = Column(String(100))
    district = Column(String(100))
    preferred_crops = Column(Text)                  # JSON list: ["onion","potato"]
    preferred_mandis = Column(Text)                 # JSON list: ["indore","dewas"]
    language = Column(String(10), default="hi")     # hi, en, mr, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    alerts = relationship("PriceAlert", back_populates="user")
    posts = relationship("CommunityPost", back_populates="user")


# ═══════════════════════════════════════════════════════════════════
# TABLE: price_alerts — User-set price notifications
# ═══════════════════════════════════════════════════════════════════

class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    crop = Column(String(100), nullable=False)
    mandi = Column(String(100), nullable=False)
    target_price = Column(Float, nullable=False)
    direction = Column(String(10), default="above") # above / below
    is_active = Column(Boolean, default=True)
    triggered_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="alerts")


# ═══════════════════════════════════════════════════════════════════
# TABLE: community_posts — User-reported prices (crowdsourced data)
# ═══════════════════════════════════════════════════════════════════

class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    crop = Column(String(100), nullable=False)
    mandi = Column(String(100), nullable=False)
    reported_price = Column(Float)
    image_url = Column(Text)
    description = Column(Text)
    verified = Column(Boolean, default=False)
    upvotes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="posts")


# ═══════════════════════════════════════════════════════════════════
# DATABASE UTILITIES
# ═══════════════════════════════════════════════════════════════════

def get_db():
    """Get a database session (FastAPI dependency injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Create all tables in the database.
    Also sets up TimescaleDB hypertable for the prices table.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created!")

    # Convert prices table to TimescaleDB hypertable (for fast time-series queries)
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
            conn.execute(text(
                "SELECT create_hypertable('prices', 'date', "
                "if_not_exists => TRUE, migrate_data => TRUE);"
            ))
            conn.commit()
        print("✅ TimescaleDB hypertable created for 'prices' table!")
    except Exception as e:
        print(f"⚠️  TimescaleDB setup skipped (not available): {e}")
        print("   Regular PostgreSQL tables will be used instead.")


def drop_all_tables():
    """Drop all tables (DANGEROUS — for development only)."""
    Base.metadata.drop_all(bind=engine)
    print("🗑️  All tables dropped!")


# ═══════════════════════════════════════════════════════════════════
# SQL for manual setup (if not using SQLAlchemy migrations)
# ═══════════════════════════════════════════════════════════════════

SETUP_SQL = """
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Prices table (main time-series data)
CREATE TABLE IF NOT EXISTS prices (
    id SERIAL,
    date DATE NOT NULL,
    crop VARCHAR(100) NOT NULL,
    mandi VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    district VARCHAR(100),
    min_price FLOAT,
    max_price FLOAT,
    modal_price FLOAT NOT NULL,
    arrivals_qtl FLOAT,
    source VARCHAR(50) DEFAULT 'AGMARKNET',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('prices', 'date', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_prices_crop_mandi_date ON prices (crop, mandi, date DESC);
CREATE INDEX IF NOT EXISTS idx_prices_date ON prices (date DESC);
"""


if __name__ == "__main__":
    print("🗃️ Initializing KrishiMitra database...")
    init_db()
