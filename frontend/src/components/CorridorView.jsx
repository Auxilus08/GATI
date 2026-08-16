import React, { useState, useEffect } from 'react';
import { fetchCorridors, planGreenWave } from '../services/api';

export default function CorridorView() {
  const [corridors, setCorridors] = useState([]);
  const [targetSpeed, setTargetSpeed] = useState(35);
  const [planResult, setPlanResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchCorridors().then(setCorridors).catch(console.error);
  }, []);

  async function handlePlan() {
    if (corridors.length === 0) return;
    setLoading(true);
    try {
      const res = await planGreenWave({
        corridor_id: corridors[0].corridor_id,
        start_junction_id: corridors[0].junction_sequence[0],
        target_speed_kmh: Number(targetSpeed),
      });
      setPlanResult(res);
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="section-header">
        <h2 className="section-title">Arterial Corridor Green Wave Synchronization</h2>
      </div>

      <div className="metric-card">
        <h3 style={{ fontSize: '1rem', marginBottom: '10px' }}>Wardha Road Arterial Corridor (Sitabuldi - Airport)</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '16px' }}>
          Dynamically coordinates downstream traffic signal offsets so platoons of vehicles (and emergency vehicles) encounter green signals without stop-and-go delays.
        </p>

        <div style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ width: '200px' }}>
            <label className="form-label">Target Platoon Speed (km/h)</label>
            <input
              type="number"
              className="form-input"
              value={targetSpeed}
              onChange={(e) => setTargetSpeed(e.target.value)}
              min="20"
              max="60"
            />
          </div>

          <button className="btn btn-primary" style={{ marginTop: '22px' }} onClick={handlePlan} disabled={loading}>
            {loading ? 'Calculating...' : 'Compute Green Wave Progression'}
          </button>
        </div>
      </div>

      {planResult && (
        <div className="metric-card">
          <h4 style={{ fontSize: '0.95rem', marginBottom: '12px' }}>Calculated Signal Progression Offsets</h4>
          <table className="approaches-table">
            <thead>
              <tr>
                <th>Junction ID</th>
                <th>Calculated Green Offset (Seconds)</th>
                <th>Target Speed</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(planResult.junction_offsets_seconds || {}).map(([jid, offset]) => (
                <tr key={jid}>
                  <td><strong>{jid}</strong></td>
                  <td className="pcu-badge">+{offset} s</td>
                  <td>{planResult.target_speed_kmh} km/h</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
