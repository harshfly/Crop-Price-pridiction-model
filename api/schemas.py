# ═══════════════════════════════════════════════════════════════════
# KrishiMitra AI — Pydantic Schemas (Request / Response models)
# Defines the shape of all data going in and out of the API
# ═══════════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════
# REQUEST MODELS — What the client sends to us
# ═══════════════════════════════════════════════════════════════════

class PredictRequest(BaseModel):
    """Request body for POST /predict/price"""
    crop: str = Field(..., example="onion", description="Crop name")
    mandi: str = Field(default="indore", example="indore", description="Mandi/market name")
    days_ahead: int = Field(default=7, ge=1, le=30, description="Days to forecast (1-30)")


class AlertRequest(BaseModel):
    """Request body for POST /alerts/set"""
    user_id: str = Field(..., description="User identifier")
    crop: str = Field(..., example="onion")
    mandi: str = Field(default="indore", example="indore")
    target_price: float = Field(..., gt=0, description="Price target in ₹/quintal")
    direction: str = Field(default="above", description="Trigger when price goes 'above' or 'below' target")


class GradeRequest(BaseModel):
    """Request body for POST /scan/grade"""
    image_base64: str = Field(..., description="Base64 encoded crop image")
    crop: Optional[str] = Field(default=None, description="Optional crop name for context")


class NearbyMandiRequest(BaseModel):
    """Request body for POST /mandis/nearby"""
    lat: float = Field(..., description="Farmer's latitude")
    lon: float = Field(..., description="Farmer's longitude")
    crop: Optional[str] = Field(default=None, description="Optional: filter by crop")
    radius_km: float = Field(default=200, ge=10, le=1000, description="Search radius in km")
    quantity_qtl: float = Field(default=100, ge=1, description="Quantity in quintals for transport cost")


class BulkPredictRequest(BaseModel):
    """Request body for POST /predict/bulk — Predict multiple crops at once"""
    crops: List[str] = Field(..., description="List of crop names")
    mandi: str = Field(default="indore", description="Mandi name")
    days_ahead: int = Field(default=7, ge=1, le=30)


# ═══════════════════════════════════════════════════════════════════
# RESPONSE MODELS — What we send back to the client
# ═══════════════════════════════════════════════════════════════════

class ShapFactor(BaseModel):
    """One explainability factor from SHAP analysis"""
    factor: str = Field(..., example="Rainfall shortage (Maharashtra)")
    impact_rs: float = Field(..., example=312, description="Impact in ₹")
    direction: str = Field(..., example="up", description="up / down / neutral")


class PredictResponse(BaseModel):
    """Response for POST /predict/price"""
    crop: str
    mandi: str
    prediction_date: str
    current_price: float
    predicted_price: float
    confidence_low: float
    confidence_high: float
    confidence_pct: float
    signal: str = Field(..., description="HOLD / SELL / WAIT")
    shap_factors: List[ShapFactor]
    seven_day_forecast: List[float] = Field(alias="7_day_forecast")
    model_version: str
    generated_at: str

    class Config:
        populate_by_name = True


class LivePriceItem(BaseModel):
    """One crop's live price from a mandi"""
    crop: str
    mandi: str
    state: str
    min_price: float
    max_price: float
    modal_price: float
    arrivals_qtl: Optional[float] = None
    date: str
    source: str = "AGMARKNET"


class LivePricesResponse(BaseModel):
    """Response for GET /prices/live"""
    prices: List[LivePriceItem]
    fetched_at: str
    source: str = "AGMARKNET"


class PriceHistoryPoint(BaseModel):
    """One data point in price history"""
    date: str
    modal_price: float
    min_price: float
    max_price: float
    arrivals_qtl: Optional[float] = None


class PriceHistoryResponse(BaseModel):
    """Response for GET /prices/history"""
    crop: str
    mandi: str
    days: int
    history: List[PriceHistoryPoint]


class MandiComparisonItem(BaseModel):
    """One mandi in the comparison list"""
    mandi: str
    state: str
    modal_price: float
    distance_km: Optional[float] = None
    transport_cost: Optional[float] = None
    net_profit: Optional[float] = None


class MandiComparisonResponse(BaseModel):
    """Response for GET /mandis/compare"""
    crop: str
    quantity_qtl: float
    from_city: str
    mandis: List[MandiComparisonItem]
    best_mandi: str
    best_net_profit: float


class WeatherImpactResponse(BaseModel):
    """Response for GET /weather/impact"""
    city: str
    crop: str
    temperature: Optional[float] = None
    rainfall_7d: Optional[float] = None
    humidity: Optional[float] = None
    forecast_7d: Optional[List[dict]] = None
    impact_summary: str
    price_impact_direction: str
    price_impact_estimate_rs: float


class AlertResponse(BaseModel):
    """Response for POST /alerts/set"""
    alert_id: str
    status: str = "active"
    message: str


class HealthResponse(BaseModel):
    """Response for GET /health"""
    status: str = "ok"
    model_version: str
    uptime_seconds: float
    models_loaded: int
    timestamp: str


# ═══════════════════════════════════════════════════════════════════
# NEW: Geography & Location Responses
# ═══════════════════════════════════════════════════════════════════

class MandiInfo(BaseModel):
    """Full information about a single mandi"""
    name: str
    lat: float
    lon: float
    state: str
    district: str
    tier: int
    region: str
    distance_km: Optional[float] = None


class NearbyMandiItem(BaseModel):
    """One mandi in nearby search results, with transport cost"""
    mandi: str
    state: str
    district: str
    lat: float
    lon: float
    distance_km: float
    transport_cost: float
    cost_per_qtl: float
    latest_prices: Optional[List[dict]] = None


class NearbyMandisResponse(BaseModel):
    """Response for POST /mandis/nearby"""
    farmer_lat: float
    farmer_lon: float
    radius_km: float
    mandis: List[NearbyMandiItem]
    total_found: int


class StateWisePriceItem(BaseModel):
    """Aggregated price for a state"""
    state: str
    avg_price: float
    min_price: float
    max_price: float
    mandi_count: int
    top_mandi: str
    top_mandi_price: float


class StateWisePricesResponse(BaseModel):
    """Response for GET /geography/state-prices"""
    crop: str
    states: List[StateWisePriceItem]
    national_avg: float
    cheapest_state: str
    costliest_state: str


class CropInfoResponse(BaseModel):
    """Response for GET /crops/{crop_name}"""
    name: str
    category: str
    perishable: bool
    harvest_months: List[int]
    msp: Optional[float] = None
    unit: str
    available_mandis: List[str] = []


class CropListResponse(BaseModel):
    """Response for GET /crops"""
    total: int
    categories: List[str]
    crops: List[dict]


class MandiDetailResponse(BaseModel):
    """Response for GET /mandis/{mandi_name}"""
    name: str
    lat: float
    lon: float
    state: str
    district: str
    tier: int
    region: str
    available_crops: List[str] = []
    latest_prices: List[dict] = []


class TransportEstimateResponse(BaseModel):
    """Response for GET /transport/estimate"""
    from_location: str
    to_mandi: str
    distance_km: float
    fuel_litres: float
    fuel_cost: float
    loading_cost: float
    total_cost: float
    cost_per_qtl: float
    quantity_qtl: float


class APIKeyResponse(BaseModel):
    """Response for POST /auth/register"""
    api_key: str
    plan: str
    rate_limit: str
    message: str

class FuelPriceItem(BaseModel):
    city: str
    diesel_price: float
    diesel_change: float
    date: str

class FuelPriceResponse(BaseModel):
    prices: List[FuelPriceItem]
    fetched_at: str
