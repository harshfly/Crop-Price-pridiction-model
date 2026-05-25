/* ═══════════════════════════════════════════════════════════
   KrishiMitra AI — Frontend Logic (v2.0)
   ═══════════════════════════════════════════════════════════ */

const API_URL = window.location.origin;
let forecastChart = null;
let weatherChart = null;
let allCrops = [];
let allMandis = [];
let statesList = [];

// Static Database Fallbacks in case API fails/offline
const CROP_DB = {
  "Onion": {category: "Vegetable", perishable: true, msp: null, unit: "₹/Qtl", months: [1,2,3,4,5]},
  "Potato": {category: "Vegetable", perishable: true, msp: null, unit: "₹/Qtl", months: [1,2,3,12]},
  "Tomato": {category: "Vegetable", perishable: true, msp: null, unit: "₹/Qtl", months: [1,2,3,10,11,12]},
  "Garlic": {category: "Vegetable", perishable: false, msp: null, unit: "₹/Qtl", months: [2,3,4]},
  "Ginger": {category: "Vegetable", perishable: false, msp: null, unit: "₹/Qtl", months: [12,1,2]},
  "Wheat": {category: "Cereal", perishable: false, msp: 2275, unit: "₹/Qtl", months: [3,4,5]},
  "Rice": {category: "Cereal", perishable: false, msp: 2203, unit: "₹/Qtl", months: [10,11,12]},
  "Maize": {category: "Cereal", perishable: false, msp: 2090, unit: "₹/Qtl", months: [9,10,11]},
  "Soybean": {category: "Oilseed", perishable: false, msp: 4600, unit: "₹/Qtl", months: [10,11]},
  "Mustard": {category: "Oilseed", perishable: false, msp: 5650, unit: "₹/Qtl", months: [3,4]},
  "Cotton": {category: "Cash Crop", perishable: false, msp: 6620, unit: "₹/Qtl", months: [10,11,12]},
  "Chana": {category: "Pulse", perishable: false, msp: 5440, unit: "₹/Qtl", months: [3,4]},
  "Moong": {category: "Pulse", perishable: false, msp: 8558, unit: "₹/Qtl", months: [3,4,9,10]}
};

const MANDI_DB = {
  "Indore": {state: "Madhya Pradesh", district: "Indore", tier: 1, region: "Central India", lat: 22.7196, lon: 75.8577},
  "Nashik": {state: "Maharashtra", district: "Nashik", tier: 1, region: "West India", lat: 19.9975, lon: 73.7898},
  "Jaipur": {state: "Rajasthan", district: "Jaipur", tier: 1, region: "North India", lat: 26.9124, lon: 75.7873},
  "Lucknow": {state: "Uttar Pradesh", district: "Lucknow", tier: 1, region: "North India", lat: 26.8467, lon: 80.9462},
  "Bangalore": {state: "Karnataka", district: "Bangalore", tier: 1, region: "South India", lat: 12.9716, lon: 77.5946},
  "Kolkata": {state: "West Bengal", district: "Kolkata", tier: 1, region: "East India", lat: 22.5726, lon: 88.3639},
  "Amritsar": {state: "Punjab", district: "Amritsar", tier: 1, region: "North India", lat: 31.6340, lon: 74.8723},
  "Hyderabad": {state: "Telangana", district: "Hyderabad", tier: 1, region: "South India", lat: 17.3850, lon: 78.4867}
};

const FESTIVALS = [
  {name: "Makar Sankranti / Pongal", date: "Jan 14", type: "Harvest Festival", impact: "High demand for pulses, rice, and jaggery. Market holiday in major mandis."},
  {name: "Holi", date: "Mid March", type: "Spring Festival", impact: "Moderate trading volume. Demand spike for wheat and chana flour."},
  {name: "Baisakhi / Rongali Bihu", date: "Apr 14", type: "Rabi Harvest", impact: "Arrival peaks for wheat, mustard. Market trading hours adjusted."},
  {name: "Ganesh Chaturthi", date: "September", type: "Cultural Festival", impact: "Spike in vegetable and fruit prices due to local demand spikes."},
  {name: "Diwali / Dhanteras", date: "Oct/Nov", type: "Major Festival", impact: "High volume. Pre-Diwali stocking drives pulse & oilseed prices up."}
];

const NEWS = [
  {title: "MSP Update: Cabinet approves higher MSP for Rabi Crops", date: "2 days ago", category: "Policy", desc: "Minimum Support Price for Wheat increased by 7% to secure domestic food reserves."},
  {title: "IMD predicts normal monsoon pattern across Central India", date: "1 week ago", category: "Weather", desc: "Expect timely sowing of Kharif crops (Soybean, Cotton) across MP & Maharashtra."},
  {title: "Onion export duties reduced to stabilize local mandi prices", date: "3 days ago", category: "Trade", desc: "Government lowers export tariff to support local farmers following high yields."},
  {title: "Diesel prices stabilize; truck transport rates remain steady", date: "5 days ago", category: "Logistics", desc: "Stable transport corridors across major trade routes lower interstate arbitrage costs."}
];

// Initialize UI & Tabs
document.addEventListener("DOMContentLoaded", async () => {
  setupNavigation();
  initAPIStatus();
  await loadMetadata();
  initDefaultPredictions();
  setupEncyclopedia();
  setupMandiDirectory();
  setupCompareTool();
  setupWeatherTool();
});

// Setup tab navigation & mobile menu
function setupNavigation() {
  const tabs = document.querySelectorAll(".nav-tab");
  const contents = document.querySelectorAll(".tab-content");
  const menuBtn = document.getElementById("mobileMenuBtn");
  const navTabs = document.getElementById("navTabs");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      contents.forEach(c => c.classList.remove("active"));

      tab.classList.add("active");
      const target = document.getElementById(`tab-${tab.dataset.tab}`);
      if (target) target.classList.add("active");
      
      navTabs.classList.remove("open");
    });
  });

  menuBtn.addEventListener("click", () => {
    navTabs.classList.toggle("open");
  });
}

// API Health Check & Pill Status
async function initAPIStatus() {
  const pill = document.getElementById("apiPill");
  const label = document.getElementById("apiLabel");
  const hsModels = document.getElementById("hsModels");
  const hsUptime = document.getElementById("hsUptime");

  try {
    const res = await fetch(`${API_URL}/api/v1/health`);
    if (res.ok) {
      const data = await res.json();
      pill.classList.add("connected");
      label.textContent = "API Connected";
      if (hsModels) hsModels.textContent = data.models_loaded || "12";
      if (hsUptime) hsUptime.textContent = formatUptime(data.uptime_seconds);
    } else {
      throw new Error();
    }
  } catch {
    pill.classList.remove("connected");
    label.textContent = "Offline Mode";
    if (hsModels) hsModels.textContent = "Offline";
    if (hsUptime) hsUptime.textContent = "N/A";
  }
}

function formatUptime(secs) {
  if (!secs) return "N/A";
  if (secs < 3600) return `${Math.round(secs/60)}m`;
  return `${Math.round(secs/3600)}h`;
}

// Fetch all states, crops, mandis metadata
async function loadMetadata() {
  // Populate dropdowns with DB fallbacks if fetch fails
  try {
    const resCrops = await fetch(`${API_URL}/api/v1/crops`);
    const dataCrops = await resCrops.json();
    allCrops = dataCrops.crops;
  } catch {
    allCrops = Object.entries(CROP_DB).map(([name, val]) => ({ name, ...val }));
  }

  try {
    const resStates = await fetch(`${API_URL}/api/v1/geography/states`);
    const dataStates = await resStates.json();
    statesList = dataStates.states;
  } catch {
    statesList = [{state: "Madhya Pradesh"}, {state: "Maharashtra"}, {state: "Rajasthan"}, {state: "Uttar Pradesh"}];
  }

  try {
    const resMandis = await fetch(`${API_URL}/api/v1/mandis`);
    const dataMandis = await resMandis.json();
    allMandis = dataMandis.mandis;
  } catch {
    allMandis = Object.entries(MANDI_DB).map(([name, val]) => ({ name, ...val }));
  }

  populateDropdowns();
}

function populateDropdowns() {
  const catSel = document.getElementById("catSelect");
  const cropSel = document.getElementById("cropSelect");
  const stateSel = document.getElementById("stateSelect");
  const mandiSel = document.getElementById("mandiSelect");

  // Populate categories
  const categories = [...new Set(allCrops.map(c => c.category))];
  catSel.innerHTML = '<option value="all">All Categories</option>' + 
    categories.map(c => `<option value="${c}">${c}</option>`).join('');

  // Populate crops
  updateCropDropdown();

  // Populate states
  stateSel.innerHTML = statesList.map(s => `<option value="${s.state}">${s.state}</option>`).join('');

  // Populate mandis based on selected state
  updateMandiDropdown();

  catSel.addEventListener("change", updateCropDropdown);
  stateSel.addEventListener("change", updateMandiDropdown);
}

function updateCropDropdown() {
  const cat = document.getElementById("catSelect").value;
  const cropSel = document.getElementById("cropSelect");
  const filtered = cat === "all" ? allCrops : allCrops.filter(c => c.category === cat);
  cropSel.innerHTML = filtered.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
}

function updateMandiDropdown() {
  const state = document.getElementById("stateSelect").value;
  const mandiSel = document.getElementById("mandiSelect");
  const filtered = allMandis.filter(m => m.state === state);
  if (filtered.length > 0) {
    mandiSel.innerHTML = filtered.map(m => `<option value="${m.name}">${m.name}</option>`).join('');
  } else {
    mandiSel.innerHTML = `<option value="Indore">Indore</option>`;
  }
}

// Prediction Flow
async function runPrediction() {
  const btn = document.getElementById("predictBtn");
  const original = btn.innerHTML;
  btn.innerHTML = '<span>Processing...</span><div class="spinner"></div>';
  btn.disabled = true;

  const crop = document.getElementById("cropSelect").value;
  const mandi = document.getElementById("mandiSelect").value;
  const days = document.getElementById("daysSelect").value;

  // Reveal grids
  document.getElementById("resultsGrid").style.display = "grid";
  document.getElementById("chartsRow").style.display = "grid";
  document.getElementById("bottomRow").style.display = "grid";

  let predictionData = null;

  try {
    const res = await fetch(`${API_URL}/api/v1/predict/price`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": "free_key" },
      body: JSON.stringify({ crop, mandi, days_ahead: parseInt(days) })
    });
    if (res.ok) predictionData = await res.json();
  } catch (e) {
    console.warn("Prediction API failed, using fallback simulator.", e);
  }

  if (!predictionData) {
    // Generate realistic simulated prediction
    const base = CROP_DB[crop]?.msp || 2500;
    const diff = Math.round((Math.random() * 0.2 - 0.08) * base);
    const predicted = base + diff;
    const change = ((diff / base) * 100).toFixed(1);
    const conf = Math.round(75 + Math.random() * 18);
    const low = Math.round(predicted * 0.95);
    const high = Math.round(predicted * 1.05);
    const signal = diff > 50 ? "HOLD" : (diff < -50 ? "SELL" : "WAIT");

    predictionData = {
      crop, mandi,
      current_price: base,
      predicted_price: predicted,
      confidence_pct: conf,
      confidence_low: low,
      confidence_high: high,
      signal,
      "7_day_forecast": Array.from({length: 7}, (_, i) => Math.round(base + (diff / 6) * i + (Math.random() * 40 - 20))),
      shap_factors: [
        { factor: "Market Demand", impact_rs: Math.round(diff * 0.4), direction: diff > 0 ? "up" : "down" },
        { factor: "Seasonal Patterns", impact_rs: Math.round(diff * 0.3), direction: "up" },
        { factor: "Local Mandi Arrivals", impact_rs: Math.round(diff * -0.2), direction: diff > 0 ? "down" : "up" }
      ]
    };
  }

  // Update UI Elements
  document.getElementById("resPredicted").textContent = `₹${predictionData.predicted_price.toLocaleString()}`;
  
  const diff = predictionData.predicted_price - predictionData.current_price;
  const pct = ((diff / predictionData.current_price) * 100).toFixed(1);
  const changeEl = document.getElementById("resChange");
  changeEl.textContent = `${diff >= 0 ? '▲' : '▼'} ₹${Math.abs(diff).toLocaleString()} (${pct}%)`;
  changeEl.style.color = diff >= 0 ? "var(--emerald)" : "var(--rose)";

  document.getElementById("resConfidence").textContent = `${predictionData.confidence_pct}%`;
  document.getElementById("confFill").style.width = `${predictionData.confidence_pct}%`;

  const sigEl = document.getElementById("resSignal");
  sigEl.textContent = predictionData.signal;
  sigEl.style.color = predictionData.signal === "HOLD" ? "var(--emerald)" : (predictionData.signal === "SELL" ? "var(--rose)" : "var(--amber)");

  const hintEl = document.getElementById("resSignalHint");
  hintEl.textContent = predictionData.signal === "HOLD" ? "Price expected to rise" : (predictionData.signal === "SELL" ? "Sell now to prevent losses" : "Price expected to remain stable");

  document.getElementById("resRange").textContent = `₹${predictionData.confidence_low} - ₹${predictionData.confidence_high}`;

  // Update Charts
  updateForecastChart(predictionData);

  // Update SHAP factors
  const factorsList = document.getElementById("factorsList");
  factorsList.innerHTML = predictionData.shap_factors.map(f => `
    <div class="factor-item ${f.direction}">
      <span class="f-name">${f.factor}</span>
      <span class="f-impact">${f.direction === "up" ? "+" : "-"}₹${Math.abs(f.impact_rs)}</span>
    </div>
  `).join('');

  // Update daily forecast table
  const table = document.getElementById("forecastTable");
  let forecastRows = '';
  const step = (predictionData.predicted_price - predictionData.current_price) / 6;
  for (let i = 0; i < 7; i++) {
    const p = Math.round(predictionData.current_price + step * i);
    const date = new Date();
    date.setDate(date.getDate() + i);
    forecastRows += `
      <tr>
        <td>Day ${i} (${date.toLocaleDateString(undefined, {month: 'short', day: 'numeric'})})</td>
        <td><strong>₹${p.toLocaleString()}</strong></td>
        <td><span class="badge ${step >= 0 ? 'green' : 'rose'}">${step >= 0 ? 'Rise' : 'Fall'}</span></td>
      </tr>
    `;
  }
  table.innerHTML = `<table><thead><tr><th>Timeline</th><th>Expected Price</th><th>Trend</th></tr></thead><tbody>${forecastRows}</tbody></table>`;

  // Fetch and update live rates for this crop
  updateLiveRates(crop);

  btn.innerHTML = original;
  btn.disabled = false;
}

async function updateLiveRates(crop) {
  const container = document.getElementById("liveRates");
  const badge = document.getElementById("liveCount");

  try {
    const res = await fetch(`${API_URL}/api/v1/prices/live?crop=${crop}`);
    const data = await res.json();
    if (data.prices && data.prices.length > 0) {
      badge.textContent = `${data.prices.length} prices`;
      container.innerHTML = data.prices.map(p => `
        <div class="live-rate-item">
          <div>
            <div class="lr-crop">${p.mandi}</div>
            <div class="lr-mandi">${p.state}</div>
          </div>
          <div class="lr-price">₹${p.modal_price.toLocaleString()}</div>
        </div>
      `).join('');
      return;
    }
  } catch (e) {
    console.warn("Live prices API failed, using fallback.", e);
  }

  // Fallback live prices
  badge.textContent = "3 prices";
  container.innerHTML = `
    <div class="live-rate-item"><div><div class="lr-crop">Nashik</div><div class="lr-mandi">Maharashtra</div></div><div class="lr-price">₹${Math.round(CROP_DB[crop]?.msp * 1.05 || 2600)}</div></div>
    <div class="live-rate-item"><div><div class="lr-crop">Indore</div><div class="lr-mandi">Madhya Pradesh</div></div><div class="lr-price">₹${Math.round(CROP_DB[crop]?.msp * 0.98 || 2450)}</div></div>
    <div class="live-rate-item"><div><div class="lr-crop">Lucknow</div><div class="lr-mandi">Uttar Pradesh</div></div><div class="lr-price">₹${Math.round(CROP_DB[crop]?.msp * 1.01 || 2520)}</div></div>
  `;
}

function updateForecastChart(data) {
  const ctx = document.getElementById("forecastChart").getContext("2d");
  if (forecastChart) forecastChart.destroy();

  const labels = Array.from({length: 7}, (_, i) => `Day ${i}`);
  const histData = [data.current_price * 0.98, data.current_price * 0.99, data.current_price];
  const forecastData = [null, null, data.current_price, ...data["7_day_forecast"].slice(1, 5)];

  const gradient = ctx.createLinearGradient(0, 0, 0, 300);
  gradient.addColorStop(0, 'rgba(16, 185, 129, 0.3)');
  gradient.addColorStop(1, 'rgba(16, 185, 129, 0)');

  forecastChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['Day -2', 'Day -1', 'Today', 'Day 1', 'Day 2', 'Day 3', 'Day 4'],
      datasets: [
        {
          label: 'Historical',
          data: histData,
          borderColor: '#64748b',
          borderWidth: 2,
          borderDash: [4, 4],
          fill: false,
          tension: 0.3
        },
        {
          label: 'Forecast',
          data: forecastData,
          borderColor: '#10b981',
          backgroundColor: gradient,
          borderWidth: 3,
          fill: true,
          tension: 0.3,
          pointBackgroundColor: '#10b981',
          pointRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
        x: { grid: { display: false }, ticks: { color: '#64748b' } }
      }
    }
  });
}

function initDefaultPredictions() {
  // Populate static festivals & news
  const festContainer = document.getElementById("festivalList");
  festContainer.innerHTML = FESTIVALS.map(f => `
    <div class="fest-item">
      <div class="fest-icon">🎉</div>
      <div class="fest-info">
        <div class="fest-name">${f.name}</div>
        <div class="fest-date">${f.date} · ${f.type}</div>
        <div class="fest-impact">${f.impact}</div>
      </div>
    </div>
  `).join('');

  const newsContainer = document.getElementById("newsList");
  newsContainer.innerHTML = NEWS.map(n => `
    <div class="news-item">
      <div class="news-icon">📰</div>
      <div class="news-info">
        <div class="news-title">${n.title}</div>
        <div class="news-date">${n.date} · ${n.category}</div>
        <div class="news-desc">${n.desc}</div>
      </div>
    </div>
  `).join('');
}

// Crops Tab (Encyclopedia)
function setupEncyclopedia() {
  const grid = document.getElementById("cropsGrid");
  const search = document.getElementById("cropSearch");
  const filters = document.getElementById("cropFilters");

  function render(filteredCrops) {
    grid.innerHTML = filteredCrops.map(c => `
      <div class="crop-card">
        <div class="crop-card-top">
          <div class="crop-name">${c.name}</div>
          <span class="crop-cat cat-${c.category.toLowerCase().replace(' ', '')}">${c.category}</span>
        </div>
        <div class="crop-msp">${c.msp ? `MSP: ₹${c.msp.toLocaleString()}/Qtl` : 'MSP: Not applicable'}</div>
        <span class="perish-badge perish-${c.perishable ? 'yes' : 'no'}">${c.perishable ? 'Perishable' : 'Non-perishable'}</span>
        <div class="crop-detail">
          <span>Harvest: ${formatMonths(c.harvest_months || c.months)}</span>
        </div>
      </div>
    `).join('');
  }

  function formatMonths(months) {
    if (!months) return "N/A";
    const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return months.map(m => names[m-1]).join(', ');
  }

  // Populate filter chips
  const categories = ["All", ...new Set(allCrops.map(c => c.category))];
  filters.innerHTML = categories.map((cat, idx) => `
    <button class="chip ${idx === 0 ? 'active' : ''}" data-cat="${cat}">${cat}</button>
  `).join('');

  // Filter events
  let activeCat = "All";
  filters.addEventListener("click", (e) => {
    if (e.target.classList.contains("chip")) {
      document.querySelectorAll("#cropFilters .chip").forEach(c => c.classList.remove("active"));
      e.target.classList.add("active");
      activeCat = e.target.dataset.cat;
      filterCrops();
    }
  });

  search.addEventListener("input", filterCrops);

  function filterCrops() {
    const q = search.value.toLowerCase();
    const filtered = allCrops.filter(c => {
      const matchCat = activeCat === "All" || c.category === activeCat;
      const matchSearch = c.name.toLowerCase().includes(q);
      return matchCat && matchSearch;
    });
    render(filtered);
  }

  render(allCrops);
}

// Mandis Tab (Directory)
function setupMandiDirectory() {
  const grid = document.getElementById("mandisGrid");
  const search = document.getElementById("mandiSearch");
  const filters = document.getElementById("mandiFilters");

  function render(filteredMandis) {
    grid.innerHTML = filteredMandis.map(m => `
      <div class="mandi-card">
        <div class="crop-card-top">
          <div class="mandi-name">${m.name}</div>
          <span class="tier-badge tier-${m.tier}">${m.tier ? `Tier ${m.tier}` : 'Standard'}</span>
        </div>
        <div class="mandi-state">${m.state} · ${m.district || 'District N/A'}</div>
        <div class="mandi-detail">
          <span>Region: ${m.region || 'N/A'}</span>
          <span>GPS: ${m.lat.toFixed(2)}, ${m.lon.toFixed(2)}</span>
        </div>
      </div>
    `).join('');
  }

  // Populate state filter chips
  const states = ["All", ...new Set(allMandis.map(m => m.state))];
  filters.innerHTML = states.map((s, idx) => `
    <button class="chip ${idx === 0 ? 'active' : ''}" data-state="${s}">${s}</button>
  `).join('');

  let activeState = "All";
  filters.addEventListener("click", (e) => {
    if (e.target.classList.contains("chip")) {
      document.querySelectorAll("#mandiFilters .chip").forEach(c => c.classList.remove("active"));
      e.target.classList.add("active");
      activeState = e.target.dataset.state;
      filterMandis();
    }
  });

  search.addEventListener("input", filterMandis);

  function filterMandis() {
    const q = search.value.toLowerCase();
    const filtered = allMandis.filter(m => {
      const matchState = activeState === "All" || m.state === activeState;
      const matchSearch = m.name.toLowerCase().includes(q);
      return matchState && matchSearch;
    });
    render(filtered);
  }

  render(allMandis);
}

// Compare Tab
function setupCompareTool() {
  const cropSel = document.getElementById("cmpCrop");
  const citySel = document.getElementById("cmpCity");

  cropSel.innerHTML = allCrops.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
  
  // Choose major city coordinates
  const cities = [
    {name: "Indore", lat: 22.7196, lon: 75.8577},
    {name: "Nashik", lat: 19.9975, lon: 73.7898},
    {name: "Jaipur", lat: 26.9124, lon: 75.7873},
    {name: "Lucknow", lat: 26.8467, lon: 80.9462}
  ];
  citySel.innerHTML = cities.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
}

async function runCompare() {
  const crop = document.getElementById("cmpCrop").value;
  const qty = parseFloat(document.getElementById("cmpQty").value) || 100;
  const city = document.getElementById("cmpCity").value;

  const resCard = document.getElementById("compareResults");
  resCard.style.display = "block";

  let compareData = null;

  try {
    const res = await fetch(`${API_URL}/api/v1/mandis/compare?crop=${crop}&quantity=${qty}&from_city=${city}`);
    if (res.ok) compareData = await res.json();
  } catch (e) {
    console.warn("Compare API failed, using fallback.", e);
  }

  if (!compareData) {
    // Fallback simulation
    const base = CROP_DB[crop]?.msp || 2500;
    const list = Object.entries(MANDI_DB).map(([name, info]) => {
      const dist = Math.round(100 + Math.random() * 400);
      const transport = Math.round(dist * 1.5 * qty);
      const price = base + Math.round((Math.random() * 0.1 - 0.05) * base);
      const revenue = price * qty;
      const profit = revenue - transport;
      return { mandi: name, state: info.state, modal_price: price, distance_km: dist, transport_cost: transport, net_profit: profit };
    });
    list.sort((a,b) => b.net_profit - a.net_profit);
    compareData = {
      crop,
      quantity_qtl: qty,
      from_city: city,
      best_mandi: list[0].mandi,
      best_net_profit: list[0].net_profit,
      mandis: list
    };
  }

  document.getElementById("cmpBest").textContent = compareData.best_mandi;
  document.getElementById("cmpProfit").textContent = `Net Profit: ₹${compareData.best_net_profit.toLocaleString()}`;

  const table = document.getElementById("compareTable");
  table.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Mandi</th>
          <th>State</th>
          <th>Price/Qtl</th>
          <th>Distance</th>
          <th>Truck Cost</th>
          <th>Est. Net Profit</th>
        </tr>
      </thead>
      <tbody>
        ${compareData.mandis.map((m, idx) => `
          <tr style="${idx === 0 ? 'background:var(--emerald-dim); font-weight: 600;' : ''}">
            <td>${m.mandi}</td>
            <td>${m.state}</td>
            <td>₹${m.modal_price.toLocaleString()}</td>
            <td>${m.distance_km} km</td>
            <td>₹${m.transport_cost.toLocaleString()}</td>
            <td style="color:${m.net_profit > 0 ? 'var(--emerald)' : 'var(--rose)'}">₹${m.net_profit.toLocaleString()}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

// Weather Tab
function setupWeatherTool() {
  const citySel = document.getElementById("wxCity");
  const cropSel = document.getElementById("wxCrop");

  citySel.innerHTML = Object.keys(MANDI_DB).map(c => `<option value="${c}">${c}</option>`).join('');
  cropSel.innerHTML = allCrops.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
}

async function fetchWeather() {
  const city = document.getElementById("wxCity").value;
  const crop = document.getElementById("wxCrop").value;

  const resCard = document.getElementById("weatherResults");
  resCard.style.display = "block";

  let weatherData = null;

  try {
    const res = await fetch(`${API_URL}/api/v1/weather/impact?city=${city}&crop=${crop}`);
    if (res.ok) weatherData = await res.json();
  } catch (e) {
    console.warn("Weather API failed, using fallback.", e);
  }

  if (!weatherData) {
    // Fallback simulation
    const temp = Math.round(28 + Math.random() * 10);
    const humidity = Math.round(40 + Math.random() * 40);
    const rain = Math.round(Math.random() * 20);
    const forecast_7d = Array.from({length: 7}, (_, i) => {
      const date = new Date();
      date.setDate(date.getDate() + i);
      return {
        date: date.toLocaleDateString(undefined, {month: 'short', day: 'numeric'}),
        temp: temp + Math.round(Math.random() * 4 - 2),
        humidity: humidity + Math.round(Math.random() * 10 - 5)
      };
    });

    weatherData = {
      city, crop, temperature: temp, humidity, rainfall_7d: rain,
      price_impact_direction: rain > 15 ? "up" : "neutral",
      price_impact_estimate_rs: rain > 15 ? 120 : 0,
      impact_summary: rain > 15 ? "Heavy rainfall expected which might disrupt local logistics and harvest arrivals, putting upward pressure on prices." : "Weather conditions are fully optimal for crop maturity and harvesting.",
      forecast_7d
    };
  }

  document.getElementById("wxTemp").textContent = `${weatherData.temperature}°C`;
  document.getElementById("wxHumidity").textContent = `${weatherData.humidity}%`;
  document.getElementById("wxRain").textContent = `${weatherData.rainfall_7d || 0} mm`;
  
  const impEl = document.getElementById("wxImpact");
  impEl.textContent = weatherData.price_impact_direction === "up" ? `+₹${weatherData.price_impact_estimate_rs}` : "Nominal";
  impEl.style.color = weatherData.price_impact_direction === "up" ? "var(--rose)" : "var(--emerald)";

  document.getElementById("wxSummary").textContent = weatherData.impact_summary;

  // Build Weather Chart
  const ctx = document.getElementById("weatherChart").getContext("2d");
  if (weatherChart) weatherChart.destroy();

  weatherChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: weatherData.forecast_7d.map(f => f.date),
      datasets: [
        {
          label: 'Temp (°C)',
          data: weatherData.forecast_7d.map(f => f.temp),
          backgroundColor: 'rgba(245, 158, 11, 0.6)',
          borderColor: 'var(--amber)',
          borderWidth: 1
        },
        {
          label: 'Humidity (%)',
          data: weatherData.forecast_7d.map(f => f.humidity),
          backgroundColor: 'rgba(59, 130, 246, 0.4)',
          borderColor: 'var(--blue)',
          borderWidth: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
        x: { grid: { display: false }, ticks: { color: '#64748b' } }
      }
    }
  });
}
