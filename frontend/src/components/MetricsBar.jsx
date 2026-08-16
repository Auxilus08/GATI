import React from 'react';

export default function MetricsBar({ summary }) {
  const {
    active_junctions = 0,
    total_city_pcu = 0,
    high_risk_junctions = 0,
    active_emergencies = 0,
    system_health = 'OPTIMAL',
  } = summary || {};

  return (
    <div className="metrics-row">
      <div className="metric-card">
        <span className="metric-label">Active Junctions</span>
        <span className="metric-value">{active_junctions}</span>
        <span className="metric-hint">Scale target: ~100 junctions</span>
      </div>

      <div className="metric-card">
        <span className="metric-label">Total City PCU Pressure</span>
        <span className="metric-value">{total_city_pcu.toLocaleString()}</span>
        <span className="metric-hint">Equivalent Passenger Car Units</span>
      </div>

      <div className="metric-card">
        <span className="metric-label">High-Risk Bottlenecks</span>
        <span
          className="metric-value"
          style={{ color: high_risk_junctions > 0 ? 'var(--color-red)' : 'var(--color-green)' }}
        >
          {high_risk_junctions}
        </span>
        <span className="metric-hint">Spillback & queue imbalance</span>
      </div>

      <div className="metric-card">
        <span className="metric-label">Emergency Corridors</span>
        <span
          className="metric-value"
          style={{ color: active_emergencies > 0 ? 'var(--color-yellow)' : 'var(--text-primary)' }}
        >
          {active_emergencies}
        </span>
        <span className="metric-hint">Ambulance / Fire Priority Active</span>
      </div>
    </div>
  );
}
