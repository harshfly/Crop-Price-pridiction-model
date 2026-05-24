import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Filler, Legend } from 'chart.js';
import { getCrops, getMandis, predictPrice, getFuelPrices, getWeatherImpact, getBestMandi } from '../services/api';
import { Activity, ThermometerSun, Truck, Calendar, MapPin, Fuel, CloudRain } from 'lucide-react';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Filler, Legend);

const PredictionDashboard = () => {
  const [crops, setCrops] = useState([]);
  const [mandis, setMandis] = useState([]);
  
  const [selectedCrop, setSelectedCrop] = useState('Wheat');
  const [selectedMandi, setSelectedMandi] = useState('Indore');
  const [daysAhead, setDaysAhead] = useState(7);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [prediction, setPrediction] = useState(null);
  const [fuelData, setFuelData] = useState(null);
  const [weatherData, setWeatherData] = useState(null);
  const [bestMandi, setBestMandi] = useState(null);

  useEffect(() => {
    const fetchDropdowns = async () => {
      const [c, m] = await Promise.all([getCrops(), getMandis()]);
      setCrops(c);
      setMandis(m);
    };
    fetchDropdowns();
  }, []);

  useEffect(() => {
    const fetchLiveData = async () => {
      if (mandis.length === 0) return;
      const mandiObj = mandis.find(m => (m.name || m) === selectedMandi) || { lat: 22.7196, lon: 75.8577 };
      const lat = mandiObj.lat || 22.7196;
      const lon = mandiObj.lon || 75.8577;

      try {
        const [fuel, weather, best] = await Promise.all([
          getFuelPrices(),
          getWeatherImpact(selectedMandi, selectedCrop),
          getBestMandi(selectedCrop, 100, lat, lon)
        ]);
        setFuelData(fuel);
        setWeatherData(weather);
        setBestMandi(best);
      } catch (e) {
        console.error("Auto-fetch live data error", e);
      }
    };
    fetchLiveData();
  }, [selectedCrop, selectedMandi, mandis]);

  const handlePredict = async () => {
    setLoading(true);
    setError('');
    try {
      const pred = await predictPrice(selectedCrop, selectedMandi, daysAhead);
      setPrediction(pred);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getFutureDate = (daysToAdd) => {
    const d = new Date();
    d.setDate(d.getDate() + daysToAdd);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const chartData = prediction ? {
    labels: Array.from({length: daysAhead}, (_, i) => getFutureDate(i + 1)),
    datasets: [
      {
        fill: true,
        label: 'Price Forecast (₹)',
        data: prediction['7_day_forecast'],
        borderColor: 'rgba(0, 255, 136, 1)',
        backgroundColor: 'rgba(0, 255, 136, 0.1)',
        pointBackgroundColor: 'rgba(0, 255, 136, 1)',
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.4
      }
    ]
  } : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
      
      {/* 3D Glass Controls Panel */}
      <motion.div 
        className="glass-panel" 
        style={{ padding: '30px', display: 'flex', gap: '20px', alignItems: 'flex-end', zIndex: 10 }}
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
      >
        <div style={{ flex: 1 }}>
          <label style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>Crop</label>
          <select className="input-field" value={selectedCrop} onChange={e => setSelectedCrop(e.target.value)}>
            {crops.map(c => <option key={c.name || c} value={c.name || c}>{c.name || c}</option>)}
          </select>
        </div>
        <div style={{ flex: 1 }}>
          <label style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>Mandi (Market)</label>
          <select className="input-field" value={selectedMandi} onChange={e => setSelectedMandi(e.target.value)}>
            {mandis.map(m => <option key={m.name || m} value={m.name || m}>{m.name || m}</option>)}
          </select>
        </div>
        <div style={{ flex: 1 }}>
          <label style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>Forecast Horizon</label>
          <select className="input-field" value={daysAhead} onChange={e => setDaysAhead(Number(e.target.value))}>
            <option value={7}>7 Days</option>
            <option value={14}>14 Days</option>
            <option value={30}>30 Days</option>
          </select>
        </div>
        <button 
          className="btn-primary" 
          style={{ height: '48px', padding: '0 40px', width: '200px' }}
          onClick={handlePredict}
          disabled={loading}
        >
          {loading ? 'Analyzing...' : 'Predict Prices'}
        </button>
      </motion.div>

      {error && (
        <div style={{ padding: '15px', background: 'rgba(255, 51, 102, 0.1)', border: '1px solid var(--danger-glow)', borderRadius: '8px', color: 'var(--danger-glow)' }}>
          {error}
        </div>
      )}

      {/* Results Dashboard */}
      {prediction && (
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '30px' }}
        >
          
          {/* Main Visuals: Chart & KPI */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
            
            {/* KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
              <div className="glass-panel" style={{ padding: '25px', position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', right: -20, top: -20, opacity: 0.1 }}><Activity size={100} /></div>
                <h4 style={{ color: 'var(--text-muted)' }}>Current Price</h4>
                <h2 style={{ fontSize: '2.5rem', marginTop: '10px' }}>₹{prediction.current_price}</h2>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '5px' }}>
                  ₹{(prediction.current_price / 100).toFixed(1)} / kg
                </div>
              </div>
              
              <div className="glass-panel" style={{ padding: '25px', position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', right: -20, top: -20, opacity: 0.1 }}><Activity size={100} /></div>
                <h4 style={{ color: 'var(--text-muted)' }}>Predicted ({getFutureDate(daysAhead)})</h4>
                <h2 style={{ fontSize: '2.5rem', marginTop: '10px' }}>₹{prediction.predicted_price}</h2>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '5px' }}>
                  ₹{(prediction.predicted_price / 100).toFixed(1)} / kg
                </div>
              </div>

              <div className="glass-panel" style={{ 
                  padding: '25px', 
                  border: `1px solid ${prediction.signal === 'SELL' ? 'var(--danger-glow)' : 'var(--accent-glow)'}`
                }}>
                <h4 style={{ color: 'var(--text-muted)' }}>Action Signal</h4>
                <h2 style={{ 
                  fontSize: '2.5rem', 
                  marginTop: '10px',
                  color: prediction.signal === 'SELL' ? 'var(--danger-glow)' : 'var(--accent-glow)'
                }}>
                  {prediction.signal}
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Confidence: {prediction.confidence_pct}%</p>
              </div>
            </div>

            {/* Chart */}
            <div className="glass-panel" style={{ padding: '30px', height: '400px' }}>
              <h3 style={{ marginBottom: '20px' }}>Price Trajectory Simulation</h3>
              <Line 
                data={chartData} 
                options={{ 
                  responsive: true, 
                  maintainAspectRatio: false,
                  scales: {
                    y: { grid: { color: 'rgba(255,255,255,0.05)' } },
                    x: { grid: { display: false } }
                  },
                  plugins: { legend: { display: false } }
                }} 
              />
            </div>

            {/* NEW WIDGETS GRID */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
              
              {/* Weather Widget */}
              <div className="glass-panel" style={{ padding: '20px' }}>
                <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}><CloudRain size={20} color="var(--accent-glow-secondary)" /> Weather Impact</h4>
                {weatherData ? (
                  <>
                    <h3 style={{ fontSize: '1.8rem', color: weatherData.price_impact_direction === 'up' ? 'var(--accent-glow)' : 'var(--text-main)' }}>
                      {weatherData.temperature}°C
                    </h3>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '10px' }}>{weatherData.impact_summary}</p>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-glass)', paddingTop: '10px' }}>
                      {weatherData.forecast_7d?.slice(0,4).map((f, i) => (
                         <div key={i} style={{ textAlign: 'center' }}>
                           <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{f.date.substring(5)}</div>
                           <div style={{ fontWeight: 600 }}>{f.temp}°</div>
                         </div>
                      ))}
                    </div>
                  </>
                ) : <p style={{ color: 'var(--text-muted)' }}>Loading...</p>}
              </div>

              {/* Fuel Widget */}
              <div className="glass-panel" style={{ padding: '20px' }}>
                <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}><Fuel size={20} color="var(--danger-glow)" /> Fuel Prices</h4>
                {fuelData && fuelData.prices && fuelData.prices.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {fuelData.prices.slice(0, 3).map((f, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: 'var(--text-muted)' }}>{f.city}</span>
                        <span style={{ fontWeight: 600 }}>₹{f.diesel_price} <span style={{ fontSize: '0.8rem', color: f.diesel_change > 0 ? 'var(--danger-glow)' : 'var(--accent-glow)' }}>({f.diesel_change > 0 ? '+' : ''}{f.diesel_change})</span></span>
                      </div>
                    ))}
                  </div>
                ) : <p style={{ color: 'var(--text-muted)' }}>Loading...</p>}
              </div>

              {/* Best Mandi Widget */}
              <div className="glass-panel" style={{ padding: '20px', border: '1px solid var(--accent-glow)' }}>
                <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '15px' }}><MapPin size={20} color="var(--accent-glow)" /> Best Nearby Market</h4>
                {bestMandi ? (
                  <>
                    <h3 style={{ fontSize: '1.5rem' }}>{bestMandi.best_mandi}</h3>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '10px' }}>
                      Highest Net Profit after Transport
                    </p>
                    <div style={{ background: 'rgba(0, 255, 136, 0.1)', padding: '10px', borderRadius: '8px', color: 'var(--accent-glow)', fontWeight: 600 }}>
                      Est. Profit: ₹{bestMandi.best_net_profit.toLocaleString()}
                    </div>
                  </>
                ) : <p style={{ color: 'var(--text-muted)' }}>Loading...</p>}
              </div>

            </div>

          </div>

          {/* Right Sidebar: SHAP Explainability */}
          <div className="glass-panel" style={{ padding: '30px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h3 style={{ borderBottom: '1px solid var(--border-glass)', paddingBottom: '15px' }}>
              AI Analysis Factors
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              What's driving the price {prediction.signal === 'SELL' ? 'down' : 'up'}?
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '10px' }}>
              {prediction.shap_factors?.map((factor, i) => (
                <div key={i} style={{ background: 'rgba(255,255,255,0.03)', padding: '15px', borderRadius: '8px', borderLeft: `4px solid ${factor.direction === 'up' ? 'var(--accent-glow)' : 'var(--danger-glow)'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 600 }}>{factor.factor}</span>
                    <span style={{ color: factor.direction === 'up' ? 'var(--accent-glow)' : 'var(--danger-glow)' }}>
                      {factor.direction === 'up' ? '+' : '-'}₹{factor.impact_rs}
                    </span>
                  </div>
                  <div style={{ height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min((factor.impact_rs / 500) * 100, 100)}%` }}
                      transition={{ duration: 1, delay: i * 0.2 }}
                      style={{ 
                        height: '100%', 
                        background: factor.direction === 'up' ? 'var(--gradient-main)' : 'var(--danger-glow)' 
                      }} 
                    />
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 'auto', paddingTop: '20px', borderTop: '1px solid var(--border-glass)' }}>
              <h4 style={{ marginBottom: '10px' }}>Live Data Streams</h4>
              <div style={{ display: 'flex', gap: '10px', color: 'var(--text-muted)' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}><ThermometerSun size={16}/> Weather API</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}><Truck size={16}/> Fuel API</span>
              </div>
            </div>
          </div>

        </motion.div>
      )}

    </div>
  );
};

export default PredictionDashboard;
