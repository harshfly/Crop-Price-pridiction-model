import React from 'react';
import { motion } from 'framer-motion';
import { Terminal, Zap, Globe, Shield, Code, Server } from 'lucide-react';

const SaaS_Landing = ({ onTryNow }) => {
  return (
    <div className="landing-container" style={{ display: 'flex', flexDirection: 'column', gap: '80px', marginTop: '40px' }}>
      
      {/* Hero Section */}
      <section style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ flex: 1, maxWidth: '600px' }}>
          <motion.div 
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 style={{ fontSize: '4rem', marginBottom: '20px', lineHeight: 1.1 }}>
              Enterprise <span className="gradient-text">AI Crop Price</span> Prediction API
            </h1>
            <p style={{ fontSize: '1.2rem', color: 'var(--text-muted)', marginBottom: '40px' }}>
              Empower your Agritech UI with our Global Unified XGBoost Model. Over 93.4% accuracy across 40+ crops and 50+ Indian Mandis. Built for scale.
            </p>
            <div style={{ display: 'flex', gap: '20px' }}>
              <button className="btn-primary" onClick={onTryNow} style={{ padding: '16px 32px', fontSize: '1.1rem' }}>
                <Zap size={20} /> Try Dashboard Now
              </button>
              <button className="btn-secondary" style={{ padding: '16px 32px', fontSize: '1.1rem' }}>
                <Code size={20} /> View Documentation
              </button>
            </div>
          </motion.div>
        </div>

        {/* 3D Floating Elements */}
        <div className="perspective-container" style={{ flex: 1, height: '400px', position: 'relative' }}>
          <motion.div
            animate={{ 
              rotateY: [0, 10, -10, 0],
              rotateX: [0, -5, 5, 0],
              y: [0, -15, 15, 0]
            }}
            transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
            className="glass-panel-heavy"
            style={{ 
              position: 'absolute', 
              right: '10%', 
              top: '10%', 
              padding: '30px',
              width: '350px',
              border: '1px solid var(--accent-glow)',
              boxShadow: '0 20px 50px rgba(0, 255, 136, 0.2)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
              <span style={{ color: 'var(--text-muted)' }}>POST /predict/price</span>
              <span style={{ color: 'var(--accent-glow)' }}>200 OK</span>
            </div>
            <pre style={{ color: '#fff', fontSize: '0.9rem', overflowX: 'hidden' }}>
{`{
  "crop": "Wheat",
  "mandi": "Indore",
  "predicted_price": 388.0,
  "confidence_pct": 100.0,
  "signal": "SELL"
}`}
            </pre>
          </motion.div>
        </div>
      </section>

      {/* Features Grid */}
      <section style={{ textAlign: 'center' }}>
        <h2 style={{ fontSize: '2.5rem', marginBottom: '50px' }}>Built for <span className="gradient-text">Developers & Agritech</span></h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '30px' }}>
          
          <div className="glass-panel" style={{ padding: '40px 30px', textAlign: 'left' }}>
            <Server color="var(--accent-glow-secondary)" size={40} style={{ marginBottom: '20px' }} />
            <h3>Decoupled SaaS API</h3>
            <p style={{ color: 'var(--text-muted)', marginTop: '10px' }}>Integrate the prediction engine directly into any UI, App, or internal dashboard using simple HTTP POST requests.</p>
          </div>

          <div className="glass-panel" style={{ padding: '40px 30px', textAlign: 'left' }}>
            <Globe color="var(--accent-glow)" size={40} style={{ marginBottom: '20px' }} />
            <h3>Real-Time Data Streams</h3>
            <p style={{ color: 'var(--text-muted)', marginTop: '10px' }}>Features are engineered dynamically using live OpenWeatherMap and crude oil data APIs every hour.</p>
          </div>

          <div className="glass-panel" style={{ padding: '40px 30px', textAlign: 'left' }}>
            <Shield color="var(--danger-glow)" size={40} style={{ marginBottom: '20px' }} />
            <h3>X-API-Key Authentication</h3>
            <p style={{ color: 'var(--text-muted)', marginTop: '10px' }}>Secure, rate-limited, and production-ready endpoints to easily monetize your Agritech application.</p>
          </div>

        </div>
      </section>

      {/* Pricing Section */}
      <section style={{ textAlign: 'center', marginBottom: '100px' }}>
        <h2 style={{ fontSize: '2.5rem', marginBottom: '50px' }}>Transparent <span className="gradient-text">Pricing</span></h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px' }}>
          
          {['Free', 'Starter', 'Business', 'Enterprise'].map((tier, idx) => (
            <div key={tier} className="glass-panel" style={{ padding: '40px 20px', borderTop: idx === 2 ? '4px solid var(--accent-glow)' : '' }}>
              <h3 style={{ fontSize: '1.5rem', marginBottom: '10px' }}>{tier}</h3>
              <p style={{ color: 'var(--text-muted)', marginBottom: '30px' }}>
                {idx === 0 ? '100 requests/day' : idx === 1 ? '1,000 req/day' : idx === 2 ? '10,000 req/day' : 'Unlimited'}
              </p>
              <h2 style={{ fontSize: '2.5rem', marginBottom: '30px' }}>
                {idx === 0 ? '$0' : idx === 1 ? '$49' : idx === 2 ? '$199' : 'Custom'}
              </h2>
              <button className={idx === 2 ? "btn-primary" : "btn-secondary"} style={{ width: '100%' }}>
                {idx === 0 ? 'Start Free' : 'Upgrade'}
              </button>
            </div>
          ))}

        </div>
      </section>

    </div>
  );
};

export default SaaS_Landing;
