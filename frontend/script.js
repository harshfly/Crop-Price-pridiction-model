// ═══════════════════════════════════════════════════════════════════
// KRISHIMITRA AI - FRONTEND LOGIC (v2.0)
// ═══════════════════════════════════════════════════════════════════

const API_URL = "http://localhost:8000";
let chartInstance = null;

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    checkApiStatus();
    initChart();
});

// Check if FastAPI backend is running
async function checkApiStatus() {
    const statusEl = document.getElementById("apiStatus");
    try {
        const res = await fetch(`${API_URL}/`);
        if (res.ok) {
            statusEl.innerHTML = `<div class="pulse-dot"></div><span>API Connected</span>`;
        }
    } catch (e) {
        statusEl.innerHTML = `<div class="pulse-dot" style="background:#f59e0b;"></div><span style="color:#f59e0b">Demo Mode (API Offline)</span>`;
    }
}

// Generate Forecast
async function runPrediction() {
    const btn = document.getElementById("predictBtn");
    const originalText = btn.innerHTML;
    btn.innerHTML = `<span>Simulating...</span><svg class="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path></svg>`;
    
    // Gather inputs
    const state = document.getElementById("stateSelect").value;
    const mandi = document.getElementById("mandiSelect").value;
    const crop = document.getElementById("cropSelect").value;

    try {
        // Try to fetch from FastAPI
        const response = await fetch(`${API_URL}/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                state: state,
                mandi: mandi,
                crop: crop,
                forecast_rain_tomorrow: Math.random() * 5,
                forecast_temp_max_tomorrow: 28 + Math.random() * 10,
                forecast_severity_tomorrow: Math.random() * 2
            })
        });

        if (response.ok) {
            const data = await response.json();
            updateUI(data.predicted_price_quintal, data.confidence_pct);
            return;
        }
    } catch (e) {
        console.log("API offline, using simulated data for demonstration.");
    }

    // Fallback Simulation for UI Demonstration
    setTimeout(() => {
        const basePrice = getBasePrice(crop);
        const volatility = Math.random() * 200 - 100;
        const finalPrice = Math.round(basePrice + volatility);
        const confidence = Math.round(85 + Math.random() * 10);
        updateUI(finalPrice, confidence);
        btn.innerHTML = originalText;
    }, 800);
}

function getBasePrice(crop) {
    const prices = {
        "Onion": 2200,
        "Tomato": 1800,
        "Potato": 1500,
        "Wheat": 2500,
        "Rice": 3200
    };
    return prices[crop] || 2000;
}

function updateUI(price, confidence) {
    // Update Stats
    document.getElementById("predPrice").innerText = `₹${price.toLocaleString()}`;
    document.getElementById("predSignal").innerText = price > getBasePrice(document.getElementById("cropSelect").value) ? "📈 Trending Up" : "📉 Trending Down";
    document.getElementById("predSignal").className = `stat-change ${price > getBasePrice(document.getElementById("cropSelect").value) ? 'positive' : 'negative'}`;
    
    document.getElementById("predConfidence").innerText = `${confidence}%`;
    document.getElementById("confFill").style.width = `${confidence}%`;

    // Weather impact sim
    const weatherImpacts = ["Nominal", "Low Rain Risk", "Heatwave Warning"];
    const wIdx = Math.floor(Math.random() * weatherImpacts.length);
    document.getElementById("weatherImpact").innerText = weatherImpacts[wIdx];

    // Update Chart
    updateChart(price);
}

function initChart() {
    const ctx = document.getElementById("forecastChart").getContext("2d");
    
    // Emerald Gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(16, 185, 129, 0.4)');
    gradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Day -3', 'Day -2', 'Day -1', 'Today', 'Day +1', 'Day +2', 'Day +3', 'Day +4', 'Day +5', 'Day +6', 'Day +7'],
            datasets: [{
                label: 'Historical',
                data: [null, null, null, null, null, null, null, null, null, null, null],
                borderColor: '#cbd5e1',
                borderWidth: 2,
                borderDash: [5, 5],
                tension: 0.4
            }, {
                label: 'Forecast',
                data: [null, null, null, null, null, null, null, null, null, null, null],
                borderColor: '#10b981',
                backgroundColor: gradient,
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#10b981',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleFont: { family: 'Outfit' },
                    bodyFont: { family: 'Outfit' },
                    padding: 12,
                    cornerRadius: 8
                }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    border: { display: false }
                },
                x: {
                    grid: { display: false },
                    border: { display: false }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });

    // Initial dummy data
    runPrediction();
}

function updateChart(targetPrice) {
    if (!chartInstance) return;
    
    const hist = [];
    let current = targetPrice * 0.9;
    for(let i=0; i<4; i++) {
        hist.push(current);
        current += (Math.random() * 100 - 50);
    }

    const future = [null, null, null, hist[3]];
    current = hist[3];
    for(let i=0; i<7; i++) {
        current += (targetPrice - current) * 0.3 + (Math.random() * 50 - 25);
        future.push(current);
    }

    chartInstance.data.datasets[0].data = hist.concat([null, null, null, null, null, null, null]);
    chartInstance.data.datasets[1].data = future;
    chartInstance.update();
}

// Add CSS animation for spinner
const style = document.createElement('style');
style.innerHTML = `
@keyframes spin { 100% { transform: rotate(360deg); } }
.animate-spin { animation: spin 1s linear infinite; }
`;
document.head.appendChild(style);
