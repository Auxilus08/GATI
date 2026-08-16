import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import MetricsBar from './components/MetricsBar';
import JunctionCard from './components/JunctionCard';
import CorridorView from './components/CorridorView';
import EmergencyModal from './components/EmergencyModal';
import { fetchCitySummary, fetchJunctionsList, fetchLatestTelemetry } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('live');
  const [summary, setSummary] = useState(null);
  const [junctions, setJunctions] = useState([]);
  const [telemetry, setTelemetry] = useState({});
  const [selectedJunctionForOverride, setSelectedJunctionForOverride] = useState(null);

  // Load initial data
  const loadData = async () => {
    try {
      const [sumRes, juncRes, telRes] = await Promise.all([
        fetchCitySummary().catch(() => null),
        fetchJunctionsList().catch(() => []),
        fetchLatestTelemetry().catch(() => ({})),
      ]);
      if (sumRes) setSummary(sumRes);
      if (juncRes) setJunctions(juncRes);
      if (telRes) setTelemetry(telRes);
    } catch (e) {
      console.error("Failed to load initial data", e);
    }
  };

  useEffect(() => {
    loadData();

    // Setup live polling fallback / WebSocket
    const interval = setInterval(async () => {
      try {
        const [sumRes, telRes] = await Promise.all([
          fetchCitySummary().catch(() => null),
          fetchLatestTelemetry().catch(() => ({})),
        ]);
        if (sumRes) setSummary(sumRes);
        if (telRes) setTelemetry(telRes);
      } catch (err) {
        console.error("Polling error", err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-container">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="main-content">
        <MetricsBar summary={summary} />

        {activeTab === 'live' ? (
          <div>
            <div className="section-header">
              <h2 className="section-title">City Signalized Junctions (Nagpur Pilot)</h2>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Auto-refreshing every 3s via Edge Telemetry
              </span>
            </div>

            <div className="junction-grid">
              {junctions.map((j) => (
                <JunctionCard
                  key={j.junction_id}
                  junction={j}
                  telemetry={telemetry[j.junction_id]}
                  onOpenEmergency={(junc) => setSelectedJunctionForOverride(junc)}
                />
              ))}
            </div>
          </div>
        ) : (
          <CorridorView />
        )}
      </main>

      {selectedJunctionForOverride && (
        <EmergencyModal
          junction={selectedJunctionForOverride}
          onClose={() => setSelectedJunctionForOverride(null)}
          onComplete={loadData}
        />
      )}
    </div>
  );
}
