// ═══════════════════════════════════════════════════════════════
// KrishiMitra AI — Premium Dashboard Logic
// ═══════════════════════════════════════════════════════════════

const API = "http://127.0.0.1:8001/api/v1";
let forecastChart = null;
let weatherChart = null;
let allCrops = [];
let allMandis = [];
let allStates = [];

// ── Utility ──────────────────────────────────────────────────
async function api(endpoint, options = {}) {
  try {
    const url = endpoint.startsWith("http") ? endpoint : `${API}${endpoint}`;
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json", ...options.headers },
      ...options,
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return await res.json();
  } catch (e) {
    console.error(`API Error: ${endpoint}`, e);
    return null;
  }
}

function formatPrice(n) {
  if (n == null || isNaN(n)) return "—";
  return "₹" + Math.round(n).toLocaleString("en-IN");
}

function haversineDist(lat1, lon1, lat2, lon2) {
  const R = 6371; // km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}

// ── Initialize ───────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", init);

async function init() {
  // Check API health
  const health = await api("/health");
  const statusEl = document.getElementById("apiStatus");
  if (health && health.status === "ok") {
    statusEl.innerHTML = `<span class="dot"></span><span>API Connected</span>`;
  } else {
    statusEl.innerHTML = `<span class="dot" style="background:#ef4444"></span><span>Offline</span>`;
  }

  // Load static data
  const cropsData = await api("/crops");
  if (cropsData) {
    allCrops = cropsData.crops;
    const sel = document.getElementById("cropSelect");
    sel.innerHTML = '<option value="Onion">Onion</option>';
    allCrops.forEach(c => {
      if (c.name !== "Onion") {
        sel.innerHTML += `<option value="${c.name}">${c.name}</option>`;
      }
    });
  }

  const statesData = await api("/geography/states");
  if (statesData) {
    allStates = statesData.states;
    const sel = document.getElementById("stateSelect");
    sel.innerHTML = '<option value="all">All States</option>';
    allStates.forEach(s => {
      sel.innerHTML += `<option value="${s.state}">${s.state}</option>`;
    });
  }

  const mandisData = await api("/mandis");
  if (mandisData) {
    allMandis = mandisData.mandis;
    populateMandiSelect(allMandis);
  }

  document.getElementById("stateSelect").addEventListener("change", async (e) => {
    const state = e.target.value;
    const data = await api(`/mandis?state=${encodeURIComponent(state)}`);
    if (data) populateMandiSelect(data.mandis);
  });

  // Init charts
  initChart();
  initWeatherChart();

  // Run initial default prediction
  runPrediction();
}

function populateMandiSelect(mandis) {
  const sel = document.getElementById("mandiSelect");
  const current = sel.value;
  sel.innerHTML = '';
  mandis.forEach(m => {
    const opt = document.createElement("option");
    opt.value = m.name;
    opt.textContent = `${m.name} — ${m.state}`;
    if (m.name === current) opt.selected = true;
    sel.appendChild(opt);
  });
}

// ── Geolocation Auto-Detect ──────────────────────────────────
function autoDetectLocation() {
  const btn = document.getElementById("locationBtn");
  if (!navigator.geolocation) return alert("Geolocation not supported by browser.");
  
  btn.style.opacity = "0.5";
  navigator.geolocation.getCurrentPosition(
    pos => {
      const { latitude, longitude } = pos.coords;
      let closest = null;
      let minDist = Infinity;
      
      allMandis.forEach(m => {
        const d = haversineDist(latitude, longitude, m.lat, m.lon);
        if (d < minDist) {
          minDist = d;
          closest = m;
        }
      });
      
      if (closest) {
        document.getElementById("stateSelect").value = closest.state;
        // Trigger change to load state mandis
        api(`/mandis?state=${encodeURIComponent(closest.state)}`).then(data => {
          if (data) populateMandiSelect(data.mandis);
          document.getElementById("mandiSelect").value = closest.name;
          runPrediction();
        });
      }
      btn.style.opacity = "1";
    },
    err => {
      alert("Could not detect location. Please allow GPS permissions.");
      btn.style.opacity = "1";
    }
  );
}

// ── Chart Setup ──────────────────────────────────────────────
function initChart() {
  const ctx = document.getElementById("forecastChart").getContext("2d");
  
  // Create beautiful gradient
  const grad = ctx.createLinearGradient(0, 0, 0, 400);
  grad.addColorStop(0, "rgba(16,185,129,0.3)");
  grad.addColorStop(1, "rgba(16,185,129,0.01)");

  forecastChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Price Trajectory",
          data: [],
          borderColor: "#10b981",
          backgroundColor: grad,
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointRadius: 6,
          pointBackgroundColor: "#10b981",
          pointBorderColor: "#ffffff",
          pointBorderWidth: 2,
        }
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.9)",
          titleColor: "#f1f5f9",
          bodyColor: "#34d399",
          padding: 12,
          displayColors: false,
          callbacks: {
            label: ctx => `Predicted: ₹${Math.round(ctx.parsed.y).toLocaleString("en-IN")} / Qtl`,
          },
        },
      },
      scales: {
        x: { grid: { display: false } },
        y: { grid: { color: "rgba(0,0,0,0.05)", drawBorder: false } },
      },
      interaction: { intersect: false, mode: "index" },
    },
  });
}

function initWeatherChart() {
  const ctx = document.getElementById("weatherChart").getContext("2d");
  weatherChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: [],
      datasets: [
        {
          type: "line",
          label: "Temperature (°C)",
          data: [],
          borderColor: "#f59e0b",
          backgroundColor: "#f59e0b",
          borderWidth: 2,
          tension: 0.3,
          yAxisID: "y-temp",
        },
        {
          type: "bar",
          label: "Rainfall (mm)",
          data: [],
          backgroundColor: "rgba(59,130,246,0.5)",
          borderRadius: 4,
          yAxisID: "y-rain",
        }
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 } } },
        "y-temp": { position: "left", grid: { display: false } },
        "y-rain": { position: "right", grid: { display: false }, beginAtZero: true },
      },
    },
  });
}

// ── Run Prediction & Fetch Premium APIs ──────────────────────
async function runPrediction() {
  const crop = document.getElementById("cropSelect").value;
  const mandi = document.getElementById("mandiSelect").value;
  const days = parseInt(document.getElementById("daysSelect").value || 7);

  if (!crop || !mandi) return;

  const btn = document.getElementById("predictBtn");
  btn.style.opacity = "0.7";
  btn.textContent = "Predicting...";

  // 1. Primary Prediction API
  const pred = await api("/predict/price", {
    method: "POST",
    body: JSON.stringify({ crop, mandi, days_ahead: days }),
  });

  btn.style.opacity = "1";
  btn.innerHTML = `<span>Predict</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14"></path><path d="M12 5l7 7-7 7"></path></svg>`;

  if (!pred) return alert("Prediction failed.");

  // Update Top Stats
  document.getElementById("statPredicted").textContent = formatPrice(pred.predicted_price);
  const changePct = ((pred.predicted_price - pred.current_price) / pred.current_price * 100).toFixed(1);
  const changeDir = changePct > 0 ? "up" : changePct < 0 ? "down" : "neutral";
  document.getElementById("statPredChange").textContent = `${changePct > 0 ? "+" : ""}${changePct}% in ${days}d`;
  document.getElementById("statPredChange").className = `stat-change ${changePct > 0 ? "positive" : changePct < 0 ? "negative" : "neutral"}`;
  
  document.getElementById("statConfidence").textContent = `${pred.confidence_pct}%`;
  document.getElementById("confFill").style.width = `${pred.confidence_pct}%`;

  const sig = (pred.signal || "WAIT").toLowerCase();
  const sigEmoji = sig === "hold" ? "🟢" : sig === "sell" ? "🔴" : "🟡";
  document.getElementById("statSignal").innerHTML = `${sigEmoji} ${sig.toUpperCase()}`;
  const hints = { hold: "Hold stock", sell: "Sell now", wait: "Market uncertain" };
  document.getElementById("statSignalHint").textContent = hints[sig] || "";
  document.getElementById("signalContainer").className = `stat-card glass-panel signal-card ${sig}`;

  // Update Price Chart
  const forecast = pred["7_day_forecast"] || [];
  const labels = forecast.map((_, i) => `Day ${i + 1}`);
  labels.unshift("Today");
  const prices = [pred.current_price, ...forecast];
  forecastChart.data.labels = labels;
  forecastChart.data.datasets[0].data = prices;
  forecastChart.update();

  // Populate SHAP Factors
  const factorList = document.getElementById("factorList");
  factorList.innerHTML = "";
  (pred.shap_factors || []).forEach(f => {
    const dir = f.direction === "up" ? "positive" : "negative";
    const icon = dir === "positive" ? "↑" : "↓";
    factorList.innerHTML += `
      <div class="factor-item ${dir}">
        <span class="factor-name">${f.factor}</span>
        <span class="factor-impact">₹${Math.abs(f.impact_rs).toLocaleString("en-IN")} ${icon}</span>
      </div>`;
  });

  // Populate Daily Forecast Table
  const fList = document.getElementById("forecastList");
  fList.innerHTML = "";
  forecast.forEach((p, i) => {
    const prev = i === 0 ? pred.current_price : forecast[i - 1];
    const ch = ((p - prev) / prev * 100).toFixed(1);
    const dir = ch > 0 ? "positive" : ch < 0 ? "negative" : "neutral";
    const d = new Date(); d.setDate(d.getDate() + i + 1);
    const label = d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
    fList.innerHTML += `
      <div class="forecast-item">
        <span style="font-weight:600">${label}</span>
        <span>${formatPrice(p)}</span>
        <span class="stat-change ${dir}">${ch > 0 ? "+" : ""}${ch}%</span>
      </div>`;
  });

  // 2. Weather API
  api(`/weather/impact?city=${mandi}&crop=${crop}`).then(weather => {
    if (weather) {
      document.getElementById("weatherImpact").textContent = weather.impact_summary;
      document.querySelector("#weatherImpact + p").textContent = `${weather.temperature}°C • ${weather.rainfall_7d}mm rain`;
    }
  });

  // 3. 14-Day Weather Forecast Chart
  api(`/weather/forecast?city=${mandi}`).then(w => {
    if (w) {
      weatherChart.data.labels = w.dates;
      weatherChart.data.datasets[0].data = w.temperature;
      weatherChart.data.datasets[1].data = w.rainfall;
      weatherChart.update();
    }
  });

  // 4. Market News API
  api(`/news?crop=${crop}&state=${document.getElementById("stateSelect").value}`).then(data => {
    if (data && data.news) {
      const nList = document.getElementById("newsList");
      nList.innerHTML = "";
      data.news.forEach(n => {
        nList.innerHTML += `
          <div class="news-item">
            <div class="news-headline">${n.headline}</div>
            <div class="news-meta">
              <span>${n.source}</span>
              <span>${n.time}</span>
            </div>
          </div>`;
      });
    }
  });

  // 5. Live Rates API
  document.getElementById("liveRatesMandi").textContent = mandi;
  api(`/prices/live?mandi=${mandi}`).then(data => {
    if (data && data.live_rates) {
      const rList = document.getElementById("liveRatesList");
      rList.innerHTML = "";
      data.live_rates.forEach(r => {
        const dir = r.change_pct > 0 ? "positive" : r.change_pct < 0 ? "negative" : "neutral";
        rList.innerHTML += `
          <div class="rate-item">
            <span class="rate-crop">${r.crop}</span>
            <div style="text-align:right">
              <div class="rate-price">${formatPrice(r.price)}</div>
              <div style="font-size:0.8rem" class="stat-change ${dir}">${r.change_pct > 0 ? "+" : ""}${r.change_pct}%</div>
            </div>
          </div>`;
      });
    }
  });

  // 6. Nearby Mandis API
  loadNearbyMandis(crop, mandi);
}

// ── Nearby Mandis ────────────────────────────────────────────
async function loadNearbyMandis(crop, mandiName) {
  const mandiInfo = allMandis.find(m => m.name === mandiName) || allMandis[0];
  const data = await api("/mandis/nearby", {
    method: "POST",
    body: JSON.stringify({ lat: mandiInfo.lat, lon: mandiInfo.lon, radius_km: 300, quantity_qtl: 100, crop }),
  });

  if (!data) return;
  document.getElementById("nearbyBadge").textContent = `${data.total_found} found`;
  const body = document.getElementById("nearbyBody");
  body.innerHTML = "";
  data.mandis.forEach((m, i) => {
    body.innerHTML += `
      <tr>
        <td><strong>${m.mandi}</strong><br><span style="font-size:11px;color:var(--text-muted)">${m.state}</span></td>
        <td>${m.distance_km} km</td>
        <td>${formatPrice(m.transport_cost)}</td>
        <td style="font-weight:700;color:var(--color-primary-dark)">${formatPrice(m.cost_per_qtl)}/qtl</td>
      </tr>`;
  });
}
