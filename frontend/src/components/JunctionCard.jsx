import React from 'react';

export default function JunctionCard({ junction, telemetry, onOpenEmergency }) {
  const t = telemetry || {};
  const approaches = t.approaches || {};
  const signalState = t.signal_state || 'UNKNOWN';
  const risk = t.risk || { risk_score: 0, category: 'OPTIMAL' };

  return (
    <div className="junction-card">
      <div className="junction-card-header">
        <div>
          <h3 className="junction-name">{junction.name}</h3>
          <div className="junction-id">{junction.junction_id}</div>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span className={`phase-pill ${signalState}`}>
            {signalState} (Phase {t.active_phase_id || 1})
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
        <span style={{ color: 'var(--text-secondary)' }}>Risk Index:</span>
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            color:
              risk.category === 'HIGH_RISK'
                ? 'var(--color-red)'
                : risk.category === 'MODERATE'
                ? 'var(--color-yellow)'
                : 'var(--color-green)',
          }}
        >
          {risk.risk_score} / 100 ({risk.category})
        </span>
      </div>

      <table className="approaches-table">
        <thead>
          <tr>
            <th>Approach</th>
            <th>PCU</th>
            <th>Queue</th>
            <th>Speed</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(approaches).length === 0 ? (
            <tr>
              <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                Awaiting edge telemetry stream...
              </td>
            </tr>
          ) : (
            Object.entries(approaches).map(([appId, m]) => (
              <tr key={appId}>
                <td>{appId}</td>
                <td className="pcu-badge">{m.total_pcu}</td>
                <td>{m.queue_length_m} m</td>
                <td>{m.avg_speed_kmh} km/h</td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {t.emergency_active && (
        <div
          style={{
            backgroundColor: 'var(--color-red-bg)',
            color: 'var(--color-red)',
            padding: '6px 10px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.8rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          🚨 Emergency Priority Signal Active
        </div>
      )}

      <div className="card-actions">
        <button
          className="btn btn-outline"
          style={{ flex: 1 }}
          onClick={() => onOpenEmergency(junction)}
        >
          Manual Override
        </button>
      </div>
    </div>
  );
}
