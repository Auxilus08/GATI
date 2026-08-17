import React from 'react';
import {
  Activity,
  Sliders,
  TrendingUp,
  Radio,
  MapPin,
  ShieldCheck,
  ChevronDown,
} from 'lucide-react';

export default function Navbar({
  activeTab,
  setActiveTab,
  junctions,
  selectedJunctionId,
  onSelectJunction,
  isConnected,
}) {
  return (
    <header className="navbar">
      {/* Brand & City Identification */}
      <div className="nav-left">
        <div className="brand-badge">
          <span className="brand-name">GATI</span>
          <span className="brand-version">v0.2</span>
        </div>
        <div className="brand-info">
          <div className="brand-headline">Traffic Intelligence Platform</div>
          <div className="brand-subtext">
            <MapPin size={12} /> Nagpur Smart City ICCC Console
          </div>
        </div>
      </div>

      {/* 3-Panel View Switcher Tabs in Simple Human-Friendly Words */}
      <nav className="nav-tabs">
        <button
          className={`nav-tab-btn ${activeTab === 'live' ? 'active' : ''}`}
          onClick={() => setActiveTab('live')}
        >
          <Activity size={16} />
          <span>1. Live Camera & Signal</span>
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'command' ? 'active' : ''}`}
          onClick={() => setActiveTab('command')}
        >
          <Sliders size={16} />
          <span>2. Smart Signal Controls</span>
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'predictive' ? 'active' : ''}`}
          onClick={() => setActiveTab('predictive')}
        >
          <TrendingUp size={16} />
          <span>3. Predictions & Safety Risk</span>
        </button>
      </nav>

      {/* Junction Selector Dropdown & Live Connection Status */}
      <div className="nav-right">
        {/* Dynamic Junction Selector */}
        <div className="junction-select-wrapper">
          <select
            className="nav-junction-select"
            value={selectedJunctionId}
            onChange={(e) => onSelectJunction(e.target.value)}
          >
            {junctions.map((j) => (
              <option key={j.junction_id} value={j.junction_id}>
                {j.name} ({j.junction_id})
              </option>
            ))}
          </select>
        </div>

        {/* Live Network Health Status */}
        <div className="status-pill">
          <span className={`pulse-indicator ${isConnected ? 'online' : 'reconnecting'}`} />
          <span className="status-text">
            {isConnected ? 'LIVE TELEMETRY' : 'CONNECTING...'}
          </span>
        </div>
      </div>
    </header>
  );
}
