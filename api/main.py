# ═══════════════════════════════════════════════════════════════════
# KrishiMitra AI — FastAPI Main Application (v2.0)
# Entry point: uvicorn api.main:app --reload --port 8000
# ═══════════════════════════════════════════════════════════════════

import os
import time
import glob
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("api.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("krishimitra")

limiter = Limiter(key_func=get_remote_address)
LOADED_MODELS = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all trained models at startup for instant predictions."""
    logger.info("🚀 Starting KrishiMitra AI API v2.0...")
    start = time.time()

    model_dir = os.getenv("MODEL_DIR", "models/saved")

    # Auto-discover all saved models (supports .keras, .h5, .pkl)
    if os.path.exists(model_dir):
        # Import custom layers for Keras deserialization
        try:
            from src.model import TemporalAttention, PositionalEncoding
            custom_objects = {
                "TemporalAttention": TemporalAttention,
                "PositionalEncoding": PositionalEncoding,
            }
        except ImportError:
            custom_objects = {}

        # Load Keras models (.keras or .h5)
        for ext in ["*.keras", "*.h5"]:
            for filepath in glob.glob(os.path.join(model_dir, ext)):
                fname = os.path.basename(filepath).rsplit(".", 1)[0]
                if "_best" in fname:
                    fname = fname.replace("_best", "")
                try:
                    import tensorflow as tf
                    LOADED_MODELS[fname] = tf.keras.models.load_model(filepath, custom_objects=custom_objects)
                    logger.info(f"  ✅ Loaded: {fname}")
                except Exception as e:
                    logger.warning(f"  ⚠️  Failed: {fname}: {e}")

        # Load XGBoost/sklearn models (.pkl)
        for filepath in glob.glob(os.path.join(model_dir, "*.pkl")):
            fname = os.path.basename(filepath).rsplit(".", 1)[0]
            if "scaler" in fname or "stacking" in fname or "corrector" in fname:
                continue  # Skip utility files
            try:
                import joblib
                LOADED_MODELS[fname] = joblib.load(filepath)
                logger.info(f"  ✅ Loaded: {fname}")
            except Exception as e:
                logger.warning(f"  ⚠️  Failed: {fname}: {e}")

    elapsed = time.time() - start
    logger.info(f"✅ Loaded {len(LOADED_MODELS)} models in {elapsed:.1f}s")

    from api.routes import set_models
    set_models(LOADED_MODELS)

    yield
    logger.info("🛑 Shutting down KrishiMitra AI API...")
    LOADED_MODELS.clear()


app = FastAPI(
    title="KrishiMitra AI API",
    description=(
        "🌾 Enterprise AI-powered crop price prediction for Indian agricultural markets.\n\n"
        "**Features:**\n"
        "- 40+ crops, 50+ mandis across 15 states\n"
        "- 7-day price forecasts with >90% accuracy\n"
        "- GPS-based mandi discovery & transport cost estimation\n"
        "- SHAP explainability & HOLD/SELL signals\n"
        "- State-wise price comparison & geographic heatmaps\n"
        "- API key authentication for commercial use\n\n"
        "**Auth:** Pass `X-API-Key` header for premium access."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.0f}ms)")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("APP_ENV") == "development" else "Something went wrong",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


from api.routes import router
app.include_router(router, prefix="/api/v1")
app.include_router(router)

# ── Serve Frontend Dashboard ──────────────────────────────────
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/dashboard", StaticFiles(directory=frontend_dir, html=True), name="frontend")


@app.get("/", tags=["System"])
async def root():
    """Redirect to dashboard if frontend exists, else return API info."""
    if os.path.exists(os.path.join(frontend_dir, "index.html")):
        return RedirectResponse(url="/dashboard/")
    return {
        "name": "KrishiMitra AI API",
        "version": "2.0.0",
        "docs": "/docs",
        "dashboard": "/dashboard",
        "health": "/api/v1/health",
        "description": "🌾 Enterprise AI crop price prediction — 40+ crops, 50+ mandis",
    }
