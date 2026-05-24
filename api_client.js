// ═══════════════════════════════════════════════════════════════════
// KrishiMitra AI — Frontend API Client
// Connects the KrishiMitra web/mobile app to the FastAPI backend
// ═══════════════════════════════════════════════════════════════════
//
// USAGE:
//   const api = new KrishiMitraAPI("https://your-api.railway.app");
//   const prediction = await api.getPrediction("onion", "indore");
// ═══════════════════════════════════════════════════════════════════

class KrishiMitraAPI {
    constructor(baseUrl = "http://localhost:8000") {
        this.BASE = baseUrl;
        this.CACHE_MINUTES = 30;
        this.TIMEOUT = 10000; // 10 seconds
        this.VERSION = "v1";
    }

    // ── Internal: Make API request with error handling ─────────────
    async _request(method, path, body = null) {
        const url = `${this.BASE}${path}`;

        const options = {
            method,
            headers: { "Content-Type": "application/json" },
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        // Add timeout using AbortController
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.TIMEOUT);
        options.signal = controller.signal;

        try {
            this._showLoading(true);
            const response = await fetch(url, options);
            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `API error: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);

            if (error.name === "AbortError") {
                console.error(`⏰ Request timeout: ${path}`);
                this._showError("सर्वर से जवाब नहीं आया। कृपया दोबारा कोशिश करें।");
            } else {
                console.error(`❌ API Error [${path}]:`, error.message);
                this._showError("सर्वर से कनेक्शन नहीं हो पा रहा है।");
            }

            return null;
        } finally {
            this._showLoading(false);
        }
    }

    // ── Cache helpers ──────────────────────────────────────────────
    _getCached(key) {
        try {
            const item = localStorage.getItem(`km_${key}`);
            if (!item) return null;

            const { data, expiry } = JSON.parse(item);
            if (Date.now() > expiry) {
                localStorage.removeItem(`km_${key}`);
                return null;
            }
            return data;
        } catch {
            return null;
        }
    }

    _setCache(key, data, minutes = this.CACHE_MINUTES) {
        try {
            const item = {
                data,
                expiry: Date.now() + minutes * 60 * 1000,
            };
            localStorage.setItem(`km_${key}`, JSON.stringify(item));
        } catch {
            // localStorage full — silently fail
        }
    }

    // ── UI helpers ────────────────────────────────────────────────
    _showLoading(show) {
        const spinner = document.getElementById("loadingSpinner");
        if (spinner) spinner.style.display = show ? "flex" : "none";
    }

    _showError(message) {
        const errorEl = document.getElementById("errorMessage");
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = "block";
            setTimeout(() => { errorEl.style.display = "none"; }, 5000);
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // PUBLIC API METHODS
    // ═══════════════════════════════════════════════════════════════

    /**
     * Get AI price prediction for a crop at a mandi.
     * Returns predicted price, confidence, SHAP factors, and signal.
     */
    async getPrediction(crop, mandi = "indore", daysAhead = 7) {
        const cacheKey = `pred_${crop}_${mandi}_${daysAhead}`;
        const cached = this._getCached(cacheKey);
        if (cached) return cached;

        const data = await this._request("POST", "/predict/price", {
            crop,
            mandi,
            days_ahead: daysAhead,
        });

        if (data) {
            this._setCache(cacheKey, data, 30);
        }
        return data || MOCK_PREDICTIONS[crop] || MOCK_PREDICTIONS.default;
    }

    /**
     * Get today's live prices from AGMARKNET.
     */
    async getLivePrices(crop = "all", mandi = "indore") {
        const cacheKey = `live_${crop}_${mandi}`;
        const cached = this._getCached(cacheKey);
        if (cached) return cached;

        const data = await this._request("GET", `/prices/live?crop=${crop}&mandi=${mandi}`);

        if (data) {
            this._setCache(cacheKey, data, 15); // Cache for 15 min
        }
        return data;
    }

    /**
     * Get historical price data for charts.
     */
    async getPriceHistory(crop, mandi = "indore", days = 30) {
        const cacheKey = `hist_${crop}_${mandi}_${days}`;
        const cached = this._getCached(cacheKey);
        if (cached) return cached;

        const data = await this._request(
            "GET",
            `/prices/history?crop=${crop}&mandi=${mandi}&days=${days}`
        );

        if (data) {
            this._setCache(cacheKey, data, 60); // Cache for 1 hour
        }
        return data;
    }

    /**
     * Compare prices across different mandis.
     */
    async getMandiComparison(crop, quantity = 100, fromCity = "indore") {
        const data = await this._request(
            "GET",
            `/mandis/compare?crop=${crop}&quantity=${quantity}&from_city=${fromCity}`
        );
        return data;
    }

    /**
     * Get current weather impact on crop prices.
     */
    async getWeatherImpact(city = "indore", crop = "onion") {
        const cacheKey = `weather_${city}_${crop}`;
        const cached = this._getCached(cacheKey);
        if (cached) return cached;

        const data = await this._request(
            "GET",
            `/weather/impact?city=${city}&crop=${crop}`
        );

        if (data) {
            this._setCache(cacheKey, data, 60);
        }
        return data;
    }

    /**
     * Set a price alert for the user.
     */
    async setAlert(crop, mandi, targetPrice, userId = "anonymous") {
        return await this._request("POST", "/alerts/set", {
            user_id: userId,
            crop,
            mandi,
            target_price: targetPrice,
            direction: "above",
        });
    }

    /**
     * Check API health.
     */
    async checkHealth() {
        return await this._request("GET", "/health");
    }

    // ═══════════════════════════════════════════════════════════════
    // PAGE-LEVEL UPDATE FUNCTIONS
    // ═══════════════════════════════════════════════════════════════

    /**
     * Update the entire home page with fresh data.
     * Calls all APIs in parallel for speed.
     */
    async updateHomePage(userCrops = ["onion", "potato", "tomato"], userMandi = "indore") {
        console.log("🔄 Updating home page...");

        // Run all API calls simultaneously (much faster than one-by-one)
        const results = await Promise.allSettled([
            ...userCrops.map(crop => this.getPrediction(crop, userMandi)),
            this.getLivePrices("all", userMandi),
            this.getWeatherImpact(userMandi, userCrops[0]),
        ]);

        const predictions = results.slice(0, userCrops.length);
        const livePrices = results[userCrops.length];
        const weather = results[userCrops.length + 1];

        // Update price cards
        predictions.forEach((result, i) => {
            if (result.status === "fulfilled" && result.value) {
                this._updatePriceCard(userCrops[i], result.value);
            }
        });

        // Update live prices ticker
        if (livePrices.status === "fulfilled" && livePrices.value) {
            this._updateLiveTicker(livePrices.value);
        }

        // Update weather banner
        if (weather.status === "fulfilled" && weather.value) {
            this._updateWeatherBanner(weather.value);
        }

        console.log("✅ Home page updated!");
    }

    /**
     * Update the forecast/chart page for a specific crop.
     */
    async updateForecastPage(crop, mandi = "indore") {
        const [prediction, history] = await Promise.allSettled([
            this.getPrediction(crop, mandi),
            this.getPriceHistory(crop, mandi, 90),
        ]);

        if (prediction.status === "fulfilled" && prediction.value) {
            this._updateForecastChart(crop, prediction.value);
            this._updateShapFactors(prediction.value.shap_factors);
            this._updateSignalBadge(prediction.value.signal);
        }

        if (history.status === "fulfilled" && history.value) {
            this._updateHistoryChart(crop, history.value);
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // DOM UPDATE HELPERS
    // ═══════════════════════════════════════════════════════════════

    _updatePriceCard(crop, prediction) {
        const card = document.getElementById(`price-card-${crop}`);
        if (!card) return;

        const priceEl = card.querySelector(".price-value");
        const changeEl = card.querySelector(".price-change");
        const signalEl = card.querySelector(".signal-badge");

        if (priceEl) priceEl.textContent = `₹${prediction.predicted_price?.toLocaleString()}`;
        if (changeEl) {
            const change = prediction.predicted_price - prediction.current_price;
            const pct = ((change / prediction.current_price) * 100).toFixed(1);
            changeEl.textContent = `${change >= 0 ? "+" : ""}₹${change.toLocaleString()} (${pct}%)`;
            changeEl.className = `price-change ${change >= 0 ? "up" : "down"}`;
        }
        if (signalEl) {
            signalEl.textContent = prediction.signal;
            signalEl.className = `signal-badge signal-${prediction.signal?.toLowerCase()}`;
        }
    }

    _updateLiveTicker(livePrices) {
        const ticker = document.getElementById("live-ticker");
        if (!ticker || !livePrices.prices) return;

        ticker.innerHTML = livePrices.prices.map(p =>
            `<span class="ticker-item">${p.crop}: ₹${p.modal_price?.toLocaleString()}</span>`
        ).join(" · ");
    }

    _updateWeatherBanner(weather) {
        const banner = document.getElementById("weather-banner");
        if (!banner) return;

        banner.innerHTML = `
            <span>🌤 ${weather.city}: ${weather.temperature ?? "--"}°C</span>
            <span>${weather.impact_summary}</span>
        `;
    }

    _updateForecastChart(crop, prediction) {
        const chartEl = document.getElementById("forecast-chart");
        if (!chartEl || !prediction["7_day_forecast"]) return;

        // This would integrate with Chart.js or similar
        console.log(`📊 Forecast for ${crop}:`, prediction["7_day_forecast"]);
    }

    _updateShapFactors(factors) {
        const container = document.getElementById("shap-factors");
        if (!container || !factors) return;

        container.innerHTML = factors.map(f => `
            <div class="shap-factor ${f.direction}">
                <span class="factor-name">${f.factor}</span>
                <span class="factor-impact">${f.direction === "up" ? "+" : ""}₹${f.impact_rs}</span>
            </div>
        `).join("");
    }

    _updateSignalBadge(signal) {
        const badge = document.getElementById("signal-badge");
        if (!badge) return;

        badge.textContent = signal;
        badge.className = `signal-badge signal-${signal?.toLowerCase()}`;
    }
}


// ═══════════════════════════════════════════════════════════════════
// MOCK DATA — Fallback when API is unavailable
// ═══════════════════════════════════════════════════════════════════

const MOCK_PREDICTIONS = {
    onion: {
        crop: "Onion", mandi: "Indore",
        prediction_date: new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0],
        current_price: 2840, predicted_price: 3120,
        confidence_low: 2980, confidence_high: 3260, confidence_pct: 87,
        signal: "HOLD",
        shap_factors: [
            { factor: "Rainfall shortage", impact_rs: 312, direction: "up" },
            { factor: "Low mandi arrivals", impact_rs: 248, direction: "up" },
            { factor: "Festival demand", impact_rs: 220, direction: "up" },
        ],
        "7_day_forecast": [2840, 2910, 2870, 3010, 3060, 3100, 3120],
        model_version: "mock",
    },
    potato: {
        crop: "Potato", mandi: "Indore",
        prediction_date: new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0],
        current_price: 1650, predicted_price: 1580,
        confidence_low: 1480, confidence_high: 1680, confidence_pct: 79,
        signal: "SELL",
        shap_factors: [
            { factor: "High mandi arrivals", impact_rs: -180, direction: "down" },
            { factor: "Harvest season", impact_rs: -120, direction: "down" },
        ],
        "7_day_forecast": [1650, 1630, 1610, 1600, 1590, 1585, 1580],
        model_version: "mock",
    },
    tomato: {
        crop: "Tomato", mandi: "Indore",
        prediction_date: new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0],
        current_price: 3200, predicted_price: 3450,
        confidence_low: 3200, confidence_high: 3700, confidence_pct: 72,
        signal: "HOLD",
        shap_factors: [
            { factor: "Temperature spike (spoilage)", impact_rs: 200, direction: "up" },
        ],
        "7_day_forecast": [3200, 3250, 3300, 3350, 3380, 3420, 3450],
        model_version: "mock",
    },
    default: {
        crop: "Unknown", mandi: "Indore",
        predicted_price: 2500, current_price: 2500,
        confidence_pct: 50, signal: "WAIT",
        shap_factors: [],
        "7_day_forecast": [2500, 2500, 2500, 2500, 2500, 2500, 2500],
        model_version: "mock",
    },
};


// ═══════════════════════════════════════════════════════════════════
// INITIALIZE — Auto-create API instance
// ═══════════════════════════════════════════════════════════════════

// Set your API URL here (or read from meta tag / env)
const API_URL = document.querySelector('meta[name="api-url"]')?.content
    || "http://localhost:8000";

const krishiAPI = new KrishiMitraAPI(API_URL);

// Auto-update home page on load
document.addEventListener("DOMContentLoaded", () => {
    krishiAPI.updateHomePage().catch(err => {
        console.error("Failed to update home page:", err);
    });
});
