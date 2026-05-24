import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import SaaS_Landing from './components/SaaS_Landing';
import PredictionDashboard from './components/PredictionDashboard';
import { setApiKey } from './services/api';
import './index.css';

function App() {
  const [activeTab, setActiveTab] = useState('landing'); // 'landing' or 'dashboard'
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [isKeySet, setIsKeySet] = useState(false);

  const handleSetApiKey = () => {
    setApiKey(apiKeyInput);
    setIsKeySet(true);
    setActiveTab('dashboard');
  };

  return (
    <div className="app-container">
      {/* Dynamic Background Elements */}
      <div className="bg-glow-1"></div>
      <div className="bg-glow-2"></div>
      
      {/* Header Navigation */}
      <nav style={{ display: 'flex', justifyContent: 'space-between', padding: '20px 50px', alignItems: 'center', borderBottom: '1px solid var(--border-glass)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <motion.div 
            animate={{ rotate: 360 }} 
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            style={{ width: 40, height: 40, background: 'var(--gradient-main)', borderRadius: '50%', filter: 'blur(5px)' }}
          />
          <h2 style={{ letterSpacing: '2px', fontWeight: 800 }}>KRISHIMITRA <span style={{ color: 'var(--accent-glow)' }}>AI</span></h2>
        </div>
        
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <button 
            className="btn-secondary" 
            style={{ border: activeTab === 'landing' ? '1px solid var(--accent-glow)' : '' }}
            onClick={() => setActiveTab('landing')}
          >
            SaaS Platform
          </button>
          <button 
            className="btn-secondary"
            style={{ border: activeTab === 'dashboard' ? '1px solid var(--accent-glow)' : '' }}
            onClick={() => setActiveTab('dashboard')}
          >
            Live Dashboard
          </button>
          
          <div className="glass-panel" style={{ padding: '5px 15px', display: 'flex', gap: '10px', alignItems: 'center' }}>
            <input 
              type="text" 
              placeholder="Enter API Key (Optional)" 
              className="input-field" 
              style={{ padding: '8px', width: '200px', background: 'transparent', border: 'none' }}
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
            />
            <button className="btn-primary" style={{ padding: '8px 15px' }} onClick={handleSetApiKey}>
              {isKeySet ? 'Updated' : 'Connect'}
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main style={{ padding: '40px 50px' }}>
        <AnimatePresence mode="wait">
          {activeTab === 'landing' ? (
            <motion.div
              key="landing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
            >
              <SaaS_Landing onTryNow={() => setActiveTab('dashboard')} />
            </motion.div>
          ) : (
            <motion.div
              key="dashboard"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.05 }}
              transition={{ duration: 0.5 }}
            >
              <PredictionDashboard />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

export default App;
