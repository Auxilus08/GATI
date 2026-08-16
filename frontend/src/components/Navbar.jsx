import React from 'react';

export default function Navbar({ activeTab, setActiveTab }) {
  return (
    <header className="navbar">
      <div className="brand-group">
        <span className="brand-logo-badge">GATI</span>
        <div>
          <span className="brand-title">Governance-ready AI Traffic Intelligence</span>
          <span className="brand-sub">Nagpur Smart City ICCC</span>
        </div>
      </div>
      <div className="nav-status">
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className={`btn ${activeTab === 'live' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('live')}
          >
            Live Junction Grid
          </button>
          <button
            className={`btn ${activeTab === 'corridor' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('corridor')}
          >
            Corridor Green Wave
          </button>
        </div>
        <div className="status-indicator">
          <span className="status-dot"></span>
          <span>Central Ingestion: Online</span>
        </div>
      </div>
    </header>
  );
}
