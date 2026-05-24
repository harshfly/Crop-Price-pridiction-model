# ═══════════════════════════════════════════════════════════════════
# KrishiMitra AI — Geography & Mandi Master Database
# 50+ mandis across India with GPS, state, transport cost matrix
# ═══════════════════════════════════════════════════════════════════
#
# This file is the single source of truth for all geographic data.
# Every mandi, its GPS coordinates, the state it belongs to, and
# inter-mandi transport cost estimates are defined here.
#
# Used by:
#   - /api/v1/mandis/nearby   → Find nearest mandis to farmer
#   - /api/v1/mandis/compare  → Net profit after transport
#   - /api/v1/geography/*     → State-wise, region-wise aggregation
#   - src/scheduler.py        → Decide which mandis to auto-train
# ═══════════════════════════════════════════════════════════════════

import math
from typing import Optional


# ═══════════════════════════════════════════════════════════════════
# MANDI MASTER — GPS coordinates + metadata for every tracked mandi
# ═══════════════════════════════════════════════════════════════════

MANDI_DATABASE = {
    # ─── Madhya Pradesh ───────────────────────────────────────────
    "Indore":       {"lat": 22.7196, "lon": 75.8577, "state": "Madhya Pradesh", "district": "Indore",     "tier": 1, "region": "Central India"},
    "Dewas":        {"lat": 22.9676, "lon": 76.0534, "state": "Madhya Pradesh", "district": "Dewas",      "tier": 2, "region": "Central India"},
    "Ujjain":       {"lat": 23.1765, "lon": 75.7885, "state": "Madhya Pradesh", "district": "Ujjain",     "tier": 2, "region": "Central India"},
    "Bhopal":       {"lat": 23.2599, "lon": 77.4126, "state": "Madhya Pradesh", "district": "Bhopal",     "tier": 1, "region": "Central India"},
    "Mandsaur":     {"lat": 24.0667, "lon": 75.0833, "state": "Madhya Pradesh", "district": "Mandsaur",   "tier": 2, "region": "Central India"},
    "Sehore":       {"lat": 23.2000, "lon": 77.0833, "state": "Madhya Pradesh", "district": "Sehore",     "tier": 3, "region": "Central India"},
    "Ratlam":       {"lat": 23.3340, "lon": 75.0367, "state": "Madhya Pradesh", "district": "Ratlam",     "tier": 2, "region": "Central India"},
    "Neemuch":      {"lat": 24.4609, "lon": 74.8780, "state": "Madhya Pradesh", "district": "Neemuch",    "tier": 2, "region": "Central India"},
    "Jabalpur":     {"lat": 23.1815, "lon": 79.9864, "state": "Madhya Pradesh", "district": "Jabalpur",   "tier": 1, "region": "Central India"},
    "Gwalior":      {"lat": 26.2183, "lon": 78.1828, "state": "Madhya Pradesh", "district": "Gwalior",    "tier": 1, "region": "Central India"},
    "Khandwa":      {"lat": 21.8238, "lon": 76.3523, "state": "Madhya Pradesh", "district": "Khandwa",    "tier": 2, "region": "Central India"},
    "Shajapur":     {"lat": 23.4264, "lon": 76.2700, "state": "Madhya Pradesh", "district": "Shajapur",   "tier": 3, "region": "Central India"},

    # ─── Maharashtra ──────────────────────────────────────────────
    "Nashik":       {"lat": 19.9975, "lon": 73.7898, "state": "Maharashtra", "district": "Nashik",      "tier": 1, "region": "West India"},
    "Pune":         {"lat": 18.5204, "lon": 73.8567, "state": "Maharashtra", "district": "Pune",        "tier": 1, "region": "West India"},
    "Mumbai":       {"lat": 19.0760, "lon": 72.8777, "state": "Maharashtra", "district": "Mumbai",      "tier": 1, "region": "West India"},
    "Nagpur":       {"lat": 21.1458, "lon": 79.0882, "state": "Maharashtra", "district": "Nagpur",      "tier": 1, "region": "Central India"},
    "Aurangabad":   {"lat": 19.8762, "lon": 75.3433, "state": "Maharashtra", "district": "Aurangabad",  "tier": 2, "region": "West India"},
    "Solapur":      {"lat": 17.6599, "lon": 75.9064, "state": "Maharashtra", "district": "Solapur",     "tier": 2, "region": "West India"},
    "Kolhapur":     {"lat": 16.7050, "lon": 74.2433, "state": "Maharashtra", "district": "Kolhapur",    "tier": 2, "region": "West India"},
    "Lasalgaon":    {"lat": 20.1447, "lon": 73.8414, "state": "Maharashtra", "district": "Nashik",      "tier": 2, "region": "West India"},

    # ─── Rajasthan ────────────────────────────────────────────────
    "Jaipur":       {"lat": 26.9124, "lon": 75.7873, "state": "Rajasthan", "district": "Jaipur",      "tier": 1, "region": "North India"},
    "Jodhpur":      {"lat": 26.2389, "lon": 73.0243, "state": "Rajasthan", "district": "Jodhpur",     "tier": 1, "region": "North India"},
    "Kota":         {"lat": 25.2138, "lon": 75.8648, "state": "Rajasthan", "district": "Kota",        "tier": 2, "region": "North India"},
    "Udaipur":      {"lat": 24.5854, "lon": 73.7125, "state": "Rajasthan", "district": "Udaipur",     "tier": 2, "region": "North India"},
    "Alwar":        {"lat": 27.5530, "lon": 76.6346, "state": "Rajasthan", "district": "Alwar",       "tier": 2, "region": "North India"},

    # ─── Uttar Pradesh ────────────────────────────────────────────
    "Lucknow":      {"lat": 26.8467, "lon": 80.9462, "state": "Uttar Pradesh", "district": "Lucknow",    "tier": 1, "region": "North India"},
    "Agra":         {"lat": 27.1767, "lon": 78.0081, "state": "Uttar Pradesh", "district": "Agra",       "tier": 1, "region": "North India"},
    "Kanpur":       {"lat": 26.4499, "lon": 80.3319, "state": "Uttar Pradesh", "district": "Kanpur",     "tier": 1, "region": "North India"},
    "Varanasi":     {"lat": 25.3176, "lon": 83.0098, "state": "Uttar Pradesh", "district": "Varanasi",   "tier": 1, "region": "North India"},
    "Meerut":       {"lat": 28.9845, "lon": 77.7064, "state": "Uttar Pradesh", "district": "Meerut",     "tier": 2, "region": "North India"},
    "Allahabad":    {"lat": 25.4358, "lon": 81.8463, "state": "Uttar Pradesh", "district": "Allahabad",  "tier": 2, "region": "North India"},

    # ─── Gujarat ──────────────────────────────────────────────────
    "Ahmedabad":    {"lat": 23.0225, "lon": 72.5714, "state": "Gujarat", "district": "Ahmedabad",   "tier": 1, "region": "West India"},
    "Rajkot":       {"lat": 22.3039, "lon": 70.8022, "state": "Gujarat", "district": "Rajkot",      "tier": 1, "region": "West India"},
    "Surat":        {"lat": 21.1702, "lon": 72.8311, "state": "Gujarat", "district": "Surat",       "tier": 1, "region": "West India"},
    "Gondal":       {"lat": 21.9634, "lon": 70.7953, "state": "Gujarat", "district": "Rajkot",      "tier": 2, "region": "West India"},

    # ─── Karnataka ────────────────────────────────────────────────
    "Bangalore":    {"lat": 12.9716, "lon": 77.5946, "state": "Karnataka", "district": "Bangalore",  "tier": 1, "region": "South India"},
    "Hubli":        {"lat": 15.3647, "lon": 75.1240, "state": "Karnataka", "district": "Dharwad",    "tier": 2, "region": "South India"},
    "Belgaum":      {"lat": 15.8497, "lon": 74.4977, "state": "Karnataka", "district": "Belgaum",   "tier": 2, "region": "South India"},

    # ─── Tamil Nadu ───────────────────────────────────────────────
    "Chennai":      {"lat": 13.0827, "lon": 80.2707, "state": "Tamil Nadu", "district": "Chennai",    "tier": 1, "region": "South India"},
    "Coimbatore":   {"lat": 11.0168, "lon": 76.9558, "state": "Tamil Nadu", "district": "Coimbatore", "tier": 1, "region": "South India"},
    "Madurai":      {"lat": 9.9252,  "lon": 78.1198, "state": "Tamil Nadu", "district": "Madurai",    "tier": 2, "region": "South India"},

    # ─── Punjab / Haryana ─────────────────────────────────────────
    "Amritsar":     {"lat": 31.6340, "lon": 74.8723, "state": "Punjab", "district": "Amritsar",     "tier": 1, "region": "North India"},
    "Ludhiana":     {"lat": 30.9010, "lon": 75.8573, "state": "Punjab", "district": "Ludhiana",     "tier": 1, "region": "North India"},
    "Karnal":       {"lat": 29.6857, "lon": 76.9905, "state": "Haryana", "district": "Karnal",      "tier": 2, "region": "North India"},
    "Hisar":        {"lat": 29.1492, "lon": 75.7217, "state": "Haryana", "district": "Hisar",       "tier": 2, "region": "North India"},

    # ─── Andhra Pradesh / Telangana ───────────────────────────────
    "Hyderabad":    {"lat": 17.3850, "lon": 78.4867, "state": "Telangana", "district": "Hyderabad",  "tier": 1, "region": "South India"},
    "Guntur":       {"lat": 16.3067, "lon": 80.4365, "state": "Andhra Pradesh", "district": "Guntur",    "tier": 2, "region": "South India"},
    "Kurnool":      {"lat": 15.8281, "lon": 78.0373, "state": "Andhra Pradesh", "district": "Kurnool",   "tier": 2, "region": "South India"},

    # ─── West Bengal / Bihar ──────────────────────────────────────
    "Kolkata":      {"lat": 22.5726, "lon": 88.3639, "state": "West Bengal", "district": "Kolkata",    "tier": 1, "region": "East India"},
    "Patna":        {"lat": 25.6093, "lon": 85.1376, "state": "Bihar", "district": "Patna",          "tier": 1, "region": "East India"},

    # ─── Delhi NCR ────────────────────────────────────────────────
    "Azadpur":      {"lat": 28.7041, "lon": 77.1818, "state": "Delhi", "district": "Delhi",          "tier": 1, "region": "North India"},

    # ─── Kerala ───────────────────────────────────────────────────
    "Kochi":        {"lat": 9.9312,  "lon": 76.2673, "state": "Kerala", "district": "Ernakulam",      "tier": 1, "region": "South India"},
    "Trivandrum":   {"lat": 8.5241,  "lon": 76.9366, "state": "Kerala", "district": "Thiruvananthapuram","tier": 1, "region": "South India"},
    "Kozhikode":    {"lat": 11.2588, "lon": 75.7804, "state": "Kerala", "district": "Kozhikode",      "tier": 2, "region": "South India"},

    # ─── Assam / North East ───────────────────────────────────────
    "Guwahati":     {"lat": 26.1445, "lon": 91.7362, "state": "Assam", "district": "Kamrup",          "tier": 1, "region": "East India"},
    "Silchar":      {"lat": 24.8333, "lon": 92.7833, "state": "Assam", "district": "Cachar",          "tier": 2, "region": "East India"},

    # ─── Odisha ───────────────────────────────────────────────────
    "Bhubaneswar":  {"lat": 20.2961, "lon": 85.8245, "state": "Odisha", "district": "Khordha",        "tier": 1, "region": "East India"},
    "Cuttack":      {"lat": 20.4625, "lon": 85.8828, "state": "Odisha", "district": "Cuttack",        "tier": 2, "region": "East India"},

    # ─── Uttarakhand ──────────────────────────────────────────────
    "Dehradun":     {"lat": 30.3165, "lon": 78.0322, "state": "Uttarakhand", "district": "Dehradun",  "tier": 1, "region": "North India"},
    "Haldwani":     {"lat": 29.2190, "lon": 79.5130, "state": "Uttarakhand", "district": "Nainital",  "tier": 2, "region": "North India"},

    # ─── Chhattisgarh ─────────────────────────────────────────────
    "Raipur":       {"lat": 21.2514, "lon": 81.6296, "state": "Chhattisgarh", "district": "Raipur",   "tier": 1, "region": "Central India"},
    "Bilaspur":     {"lat": 22.0797, "lon": 82.1409, "state": "Chhattisgarh", "district": "Bilaspur", "tier": 2, "region": "Central India"},

    # ─── Jharkhand ────────────────────────────────────────────────
    "Ranchi":       {"lat": 23.3441, "lon": 85.3096, "state": "Jharkhand", "district": "Ranchi",      "tier": 1, "region": "East India"},
    "Jamshedpur":   {"lat": 22.8046, "lon": 86.2029, "state": "Jharkhand", "district": "East Singhbhum","tier": 2, "region": "East India"},
}


# ═══════════════════════════════════════════════════════════════════
# CROP MASTER — Full list of tracked crops with metadata
# ═══════════════════════════════════════════════════════════════════

CROP_DATABASE = {
    # ─── Vegetables ───────────────────────────────────────────────
    "Onion":            {"category": "Vegetable",    "perishable": True,  "harvest_months": [1,2,3,4,5],     "msp": None,   "unit": "₹/Qtl"},
    "Potato":           {"category": "Vegetable",    "perishable": True,  "harvest_months": [1,2,3,12],      "msp": None,   "unit": "₹/Qtl"},
    "Tomato":           {"category": "Vegetable",    "perishable": True,  "harvest_months": [1,2,3,10,11,12],"msp": None,   "unit": "₹/Qtl"},
    "Garlic":           {"category": "Vegetable",    "perishable": False, "harvest_months": [2,3,4],         "msp": None,   "unit": "₹/Qtl"},
    "Ginger":           {"category": "Vegetable",    "perishable": False, "harvest_months": [12,1,2],        "msp": None,   "unit": "₹/Qtl"},
    "Green Chilli":     {"category": "Vegetable",    "perishable": True,  "harvest_months": [10,11,12,1,2],  "msp": None,   "unit": "₹/Qtl"},
    "Capsicum":         {"category": "Vegetable",    "perishable": True,  "harvest_months": [11,12,1,2,3],   "msp": None,   "unit": "₹/Qtl"},
    "Cauliflower":      {"category": "Vegetable",    "perishable": True,  "harvest_months": [11,12,1,2],     "msp": None,   "unit": "₹/Qtl"},
    "Cabbage":          {"category": "Vegetable",    "perishable": True,  "harvest_months": [11,12,1,2],     "msp": None,   "unit": "₹/Qtl"},
    "Brinjal":          {"category": "Vegetable",    "perishable": True,  "harvest_months": [10,11,12,1],    "msp": None,   "unit": "₹/Qtl"},
    "Coriander(Leaves)":{"category": "Vegetable",    "perishable": True,  "harvest_months": [1,2,3,10,11],   "msp": None,   "unit": "₹/Qtl"},
    "Peas":             {"category": "Vegetable",    "perishable": True,  "harvest_months": [12,1,2,3],      "msp": None,   "unit": "₹/Qtl"},
    "Bitter Gourd":     {"category": "Vegetable",    "perishable": True,  "harvest_months": [3,4,5,6,7],     "msp": None,   "unit": "₹/Qtl"},
    "Okra":             {"category": "Vegetable",    "perishable": True,  "harvest_months": [3,4,5,6,7,8],   "msp": None,   "unit": "₹/Qtl"},

    # ─── Fruits ───────────────────────────────────────────────────
    "Banana":           {"category": "Fruit",        "perishable": True,  "harvest_months": [1,2,3,4,5,6,7,8,9,10,11,12], "msp": None, "unit": "₹/Qtl"},
    "Apple":            {"category": "Fruit",        "perishable": True,  "harvest_months": [8,9,10],        "msp": None,   "unit": "₹/Qtl"},
    "Mango":            {"category": "Fruit",        "perishable": True,  "harvest_months": [4,5,6,7],       "msp": None,   "unit": "₹/Qtl"},
    "Lemon":            {"category": "Fruit",        "perishable": True,  "harvest_months": [1,2,3,7,8,9],   "msp": None,   "unit": "₹/Qtl"},
    "Pomegranate":      {"category": "Fruit",        "perishable": True,  "harvest_months": [10,11,12,1,2],  "msp": None,   "unit": "₹/Qtl"},
    "Grapes":           {"category": "Fruit",        "perishable": True,  "harvest_months": [1,2,3,4],       "msp": None,   "unit": "₹/Qtl"},

    # ─── Cereals & Grains (MSP crops) ────────────────────────────
    "Wheat":            {"category": "Cereal",       "perishable": False, "harvest_months": [3,4,5],         "msp": 2275,   "unit": "₹/Qtl"},
    "Rice":             {"category": "Cereal",       "perishable": False, "harvest_months": [10,11,12],      "msp": 2203,   "unit": "₹/Qtl"},
    "Maize":            {"category": "Cereal",       "perishable": False, "harvest_months": [9,10,11],       "msp": 2090,   "unit": "₹/Qtl"},
    "Bajra":            {"category": "Cereal",       "perishable": False, "harvest_months": [9,10,11],       "msp": 2500,   "unit": "₹/Qtl"},
    "Jowar":            {"category": "Cereal",       "perishable": False, "harvest_months": [10,11,12],      "msp": 3180,   "unit": "₹/Qtl"},
    "Ragi":             {"category": "Cereal",       "perishable": False, "harvest_months": [9,10,11],       "msp": 3846,   "unit": "₹/Qtl"},

    # ─── Pulses ───────────────────────────────────────────────────
    "Chana":            {"category": "Pulse",        "perishable": False, "harvest_months": [3,4],           "msp": 5440,   "unit": "₹/Qtl"},
    "Arhar Dal":        {"category": "Pulse",        "perishable": False, "harvest_months": [12,1,2],        "msp": 7000,   "unit": "₹/Qtl"},
    "Moong":            {"category": "Pulse",        "perishable": False, "harvest_months": [3,4,9,10],      "msp": 8558,   "unit": "₹/Qtl"},
    "Urad":             {"category": "Pulse",        "perishable": False, "harvest_months": [9,10],          "msp": 6950,   "unit": "₹/Qtl"},
    "Masoor":           {"category": "Pulse",        "perishable": False, "harvest_months": [3,4],           "msp": 6425,   "unit": "₹/Qtl"},

    # ─── Oilseeds ─────────────────────────────────────────────────
    "Soybean":          {"category": "Oilseed",      "perishable": False, "harvest_months": [10,11],         "msp": 4600,   "unit": "₹/Qtl"},
    "Mustard":          {"category": "Oilseed",      "perishable": False, "harvest_months": [3,4],           "msp": 5650,   "unit": "₹/Qtl"},
    "Groundnut":        {"category": "Oilseed",      "perishable": False, "harvest_months": [10,11],         "msp": 6377,   "unit": "₹/Qtl"},
    "Sunflower":        {"category": "Oilseed",      "perishable": False, "harvest_months": [3,4],           "msp": 6760,   "unit": "₹/Qtl"},

    # ─── Cash Crops ───────────────────────────────────────────────
    "Cotton":           {"category": "Cash Crop",    "perishable": False, "harvest_months": [10,11,12],      "msp": 6620,   "unit": "₹/Qtl"},
    "Sugarcane":        {"category": "Cash Crop",    "perishable": False, "harvest_months": [11,12,1,2,3,4], "msp": 315,    "unit": "₹/Qtl"},
    "Turmeric":         {"category": "Spice",        "perishable": False, "harvest_months": [1,2,3],         "msp": None,   "unit": "₹/Qtl"},
    "Red Chillies":     {"category": "Spice",        "perishable": False, "harvest_months": [2,3,4],         "msp": None,   "unit": "₹/Qtl"},
    "Cumin Seed":       {"category": "Spice",        "perishable": False, "harvest_months": [3,4],           "msp": None,   "unit": "₹/Qtl"},
}


# ═══════════════════════════════════════════════════════════════════
# TRANSPORT COST ENGINE — Haversine distance + rate estimation
# ═══════════════════════════════════════════════════════════════════

TRANSPORT_RATE_PER_KM_PER_QTL = 1.2   # ₹ per km per quintal (truck avg)
DIESEL_PRICE_BASE = 90.0              # ₹/litre baseline for fuel adjustment
TRUCK_KM_PER_LITRE = 4.0              # Average mileage for loaded truck
LOADING_COST_PER_QTL = 25.0           # Fixed loading + unloading


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two GPS points in km."""
    R = 6371  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def road_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate road distance (1.35x haversine for Indian roads)."""
    return haversine_km(lat1, lon1, lat2, lon2) * 1.35


def estimate_transport_cost(
    from_lat: float, from_lon: float,
    to_lat: float, to_lon: float,
    quantity_qtl: float = 100,
    diesel_price: float = DIESEL_PRICE_BASE,
) -> dict:
    """
    Estimate transport cost between two GPS points.

    Returns:
        {
            "distance_km": 120.5,
            "fuel_litres": 30.1,
            "fuel_cost": 2709.0,
            "loading_cost": 2500.0,
            "total_cost": 5209.0,
            "cost_per_qtl": 52.1,
        }
    """
    dist_km = road_distance_km(from_lat, from_lon, to_lat, to_lon)
    fuel_litres = dist_km / TRUCK_KM_PER_LITRE
    fuel_cost = fuel_litres * diesel_price
    loading = LOADING_COST_PER_QTL * quantity_qtl
    total = fuel_cost + loading

    return {
        "distance_km": round(dist_km, 1),
        "fuel_litres": round(fuel_litres, 1),
        "fuel_cost": round(fuel_cost, 0),
        "loading_cost": round(loading, 0),
        "total_cost": round(total, 0),
        "cost_per_qtl": round(total / max(quantity_qtl, 1), 1),
    }


def find_nearby_mandis(
    lat: float, lon: float,
    radius_km: float = 200,
    limit: int = 10,
) -> list[dict]:
    """
    Find mandis near a GPS coordinate, sorted by distance.

    Returns:
        [{"name": "Indore", "distance_km": 12.3, "state": "MP", ...}, ...]
    """
    results = []
    for name, info in MANDI_DATABASE.items():
        dist = road_distance_km(lat, lon, info["lat"], info["lon"])
        if dist <= radius_km:
            results.append({
                "name": name,
                "distance_km": round(dist, 1),
                "lat": info["lat"],
                "lon": info["lon"],
                "state": info["state"],
                "district": info["district"],
                "tier": info["tier"],
                "region": info["region"],
            })

    results.sort(key=lambda x: x["distance_km"])
    return results[:limit]


def get_mandis_by_state(state: str) -> list[dict]:
    """Get all mandis in a specific state."""
    results = []
    for name, info in MANDI_DATABASE.items():
        if info["state"].lower() == state.lower():
            results.append({"name": name, **info})
    results.sort(key=lambda x: x["tier"])
    return results


def get_mandis_by_region(region: str) -> list[dict]:
    """Get all mandis in a region (North, South, East, West, Central)."""
    results = []
    for name, info in MANDI_DATABASE.items():
        if region.lower() in info["region"].lower():
            results.append({"name": name, **info})
    results.sort(key=lambda x: x["tier"])
    return results


def get_all_states() -> list[str]:
    """Get unique list of all states with tracked mandis."""
    return sorted(set(info["state"] for info in MANDI_DATABASE.values()))


def get_all_regions() -> list[str]:
    """Get unique list of all regions."""
    return sorted(set(info["region"] for info in MANDI_DATABASE.values()))


def get_crop_info(crop: str) -> Optional[dict]:
    """Get metadata for a specific crop."""
    # Try exact match first, then case-insensitive
    if crop in CROP_DATABASE:
        return {"name": crop, **CROP_DATABASE[crop]}
    for name, info in CROP_DATABASE.items():
        if name.lower() == crop.lower():
            return {"name": name, **info}
    return None


def get_crops_by_category(category: str) -> list[dict]:
    """Get all crops in a category (Vegetable, Fruit, Cereal, Pulse, Oilseed, etc.)"""
    results = []
    for name, info in CROP_DATABASE.items():
        if info["category"].lower() == category.lower():
            results.append({"name": name, **info})
    return results


def get_all_categories() -> list[str]:
    """Get unique crop categories."""
    return sorted(set(info["category"] for info in CROP_DATABASE.values()))
