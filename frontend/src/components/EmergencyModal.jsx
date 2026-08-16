import React, { useState } from 'react';
import { submitEmergencyOverride } from '../services/api';

export default function EmergencyModal({ junction, onClose, onComplete }) {
  const [phaseId, setPhaseId] = useState(1);
  const [duration, setDuration] = useState(45);
  const [reason, setReason] = useState('Ambulance / Fire Priority');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!junction) return null;

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await submitEmergencyOverride({
        junction_id: junction.junction_id,
        phase_id: Number(phaseId),
        duration_seconds: Number(duration),
        reason,
        authorized_by: 'ICCC_Operator_01',
      });
      setLoading(false);
      onComplete();
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to issue command');
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="modal-content">
        <div className="modal-header">
          <h2 className="modal-title">Manual Signal Override: {junction.name}</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {error && (
          <div style={{ color: 'var(--color-red)', fontSize: '0.85rem' }}>{error}</div>
        )}

        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label className="form-label">Target Green Phase</label>
            <select
              className="form-select"
              value={phaseId}
              onChange={(e) => setPhaseId(e.target.value)}
            >
              <option value="1">Phase 1: Main Arterial Through</option>
              <option value="2">Phase 2: Cross Street Feeder</option>
              <option value="3">Phase 3: Right Turn / Dedicated</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Hold Duration (Seconds)</label>
            <input
              type="number"
              className="form-input"
              value={duration}
              min="15"
              max="120"
              onChange={(e) => setDuration(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Audit Log Reason / Authorization</label>
            <input
              type="text"
              className="form-input"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Ambulance from Care Hospital"
              required
            />
          </div>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-danger" disabled={loading}>
              {loading ? 'Transmitting...' : 'Issue Green Override'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
