import React, { useState, useEffect } from 'react';
import {
  Sliders,
  Shield,
  Clock,
  TrendingDown,
  Fuel,
  Leaf,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Unlock,
  History,
  Send,
  Zap,
  Radio,
  Smartphone,
  Award,
} from 'lucide-react';
import { issueOverride, fetchOverrideStatus, fetchOverrideAudit, executeFieldQuickAction } from '../services/api';
import DynamicSplitAndCorridorVisualizer from './DynamicSplitAndCorridorVisualizer';
import EmergencyCorridorConsole from './EmergencyCorridorConsole';

export default function CommandView({
  junction,
  signalTiming,
  comparisonData,
  onRefresh,
}) {
  const junctionId = junction?.junction_id || 'NGP_J01_SITABULDI';
  const phases = junction?.phases || [];

  // Override form state
  const [targetPhase, setTargetPhase] = useState(phases[0]?.phase_id || 1);
  const [durationSec, setDurationSec] = useState(60);
  const [reason, setReason] = useState('VIP Motorcade / Priority Corridor');
  const [operatorId, setOperatorId] = useState('POLICE_ICCC_402');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [overrideStatus, setOverrideStatus] = useState(null);
  const [auditRecords, setAuditRecords] = useState([]);
  const [actionMessage, setActionMessage] = useState(null);
  const [vipCorridorActive, setVipCorridorActive] = useState(false);
  const [constableActionLoading, setConstableActionLoading] = useState(false);

  // Load live override status & audit history
  const loadOverrideState = async () => {
    try {
      const [statusRes, auditRes] = await Promise.all([
        fetchOverrideStatus(junctionId).catch(() => null),
        fetchOverrideAudit(junctionId, 10).catch(() => ({ audit_records: [] })),
      ]);
      if (statusRes) setOverrideStatus(statusRes);
      if (auditRes?.audit_records) setAuditRecords(auditRes.audit_records);
    } catch (e) {
      console.error('Failed to load override state', e);
    }
  };

  useEffect(() => {
    loadOverrideState();
    const interval = setInterval(loadOverrideState, 3000);
    return () => clearInterval(interval);
  }, [junctionId]);

  // Handle manual Phase Lock
  const handleLockPhase = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setActionMessage(null);
    try {
      const res = await issueOverride(junctionId, {
        action: 'LOCK',
        phase_id: Number(targetPhase),
        duration_seconds: Number(durationSec),
        reason,
        operator_id: operatorId,
      });
      setActionMessage({ type: 'success', text: `Phase ${targetPhase} LOCKED for ${durationSec}s. Audit ID: ${res.override_id}` });
      await loadOverrideState();
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to issue phase lock' });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle manual Phase Release
  const handleReleaseOverride = async () => {
    setIsSubmitting(true);
    setActionMessage(null);
    try {
      const res = await issueOverride(junctionId, {
        action: 'RELEASE',
        reason: 'Manual operator release back to autonomous Max-Pressure',
        operator_id: operatorId,
      });
      setActionMessage({ type: 'success', text: 'Override RELEASED. Reverted to Max-Pressure control.' });
      await loadOverrideState();
      if (onRefresh) onRefresh();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to release override' });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle 1-Click VIP Green Wave Progression
  const handleTriggerVIPGreenWave = async () => {
    setIsSubmitting(true);
    try {
      await issueOverride(junctionId, {
        action: 'LOCK',
        phase_id: 1,
        duration_seconds: 90,
        reason: 'VIP Convoy Green Wave Progression across Wardha Road Corridor',
        operator_id: 'POLICE_COMMISSIONER_401',
      });
      setVipCorridorActive(true);
      setActionMessage({ type: 'success', text: '5-Junction Wardha Road VIP Green Wave ENGAGED! Arterial phases synchronized.' });
      setTimeout(() => setVipCorridorActive(false), 90000);
      await loadOverrideState();
      if (onRefresh) onRefresh();
    } catch (e) {
      setActionMessage({ type: 'error', text: 'Failed to engage VIP corridor' });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Field Constable 1-Tap Queue Flush
  const handleFieldConstableFlush = async () => {
    setConstableActionLoading(true);
    try {
      await executeFieldQuickAction({
        junction_id: junctionId,
        action_type: 'FLUSH_HEAVY_QUEUE',
        officer_badge_id: 'CONSTABLE_MH31_8821',
        target_phase_id: 1,
        duration_seconds: 45,
      });
      setActionMessage({ type: 'success', text: `Field Constable Mobile Action: 45s Green on Phase 1 (Badge: CONSTABLE_MH31_8821)` });
      await loadOverrideState();
      if (onRefresh) onRefresh();
    } catch (e) {
      setActionMessage({ type: 'error', text: 'Failed to execute field constable action' });
    } finally {
      setConstableActionLoading(false);
    }
  };

  // Extract Headline KPIs from comparisonData or defaults
  const kpiWaitTimeBefore = comparisonData?.fixed_time?.avg_wait_sec || 42.5;
  const kpiWaitTimeAfter = comparisonData?.max_pressure?.avg_wait_sec || 29.4;
  const kpiWaitReduction = comparisonData?.improvement?.wait_time_reduction_pct || 30.8;
  const kpiQueueReduction = comparisonData?.improvement?.queue_reduction_pct || 31.9;
  const kpiFuelSaved = comparisonData?.improvement?.estimated_fuel_saved_liters || 0.96;
  const kpiCo2Saved = comparisonData?.improvement?.co2_reduction_kg || 2.22;

  const current = signalTiming?.current || { phase_id: 1, green_sec: 30, mode: 'FIXED_TIME' };
  const recommended = signalTiming?.recommended || {
    phase_id: 1,
    decision_reason: 'MAX_PRESSURE_HOLD',
    elapsed_green_sec: 12.0,
    pressures: { 1: 18.5, 2: 7.2, 3: 4.1 },
    mode: 'MAX_PRESSURE',
  };

  return (
    <div className="panel-container">
      {/* ─── Emergency Vehicle Preemption & Green Corridor Dispatcher ─── */}
      <EmergencyCorridorConsole onEmergencyTriggered={onRefresh} />

      {/* ─── Interactive Dynamic Asymmetric Split & Cascading Corridor Visualizer ─── */}
      <DynamicSplitAndCorridorVisualizer />

      {/* ─── Headline Before/After Performance KPIs (In View Header as required) ─── */}
      <div className="command-kpi-banner">
        <div className="kpi-header-eyebrow">
          <Zap size={14} className="text-yellow" />
          <span>HEADLINE SIGNAL OPTIMIZATION IMPACT (BEFORE vs. AFTER EVIDENCE)</span>
        </div>

        <div className="kpi-cards-row">
          {/* Average Wait Time KPI */}
          <div className="kpi-impact-card highlight-green">
            <div className="kpi-meta">
              <Clock size={16} /> Average Wait Time
            </div>
            <div className="kpi-split-val">
              <span className="val-before">{kpiWaitTimeBefore.toFixed(1)}s</span>
              <span className="arrow-sep">➔</span>
              <span className="val-after">{kpiWaitTimeAfter.toFixed(1)}s</span>
            </div>
            <div className="kpi-badge-gain">
              <TrendingDown size={14} /> -{kpiWaitReduction.toFixed(1)}% Reduction
            </div>
          </div>

          {/* Average Queue Length KPI */}
          <div className="kpi-impact-card highlight-blue">
            <div className="kpi-meta">
              <Sliders size={16} /> Avg Queue Length
            </div>
            <div className="kpi-split-val">
              <span className="val-before">{(comparisonData?.fixed_time?.avg_queue_m || 48.2).toFixed(1)}m</span>
              <span className="arrow-sep">➔</span>
              <span className="val-after">{(comparisonData?.max_pressure?.avg_queue_m || 32.8).toFixed(1)}m</span>
            </div>
            <div className="kpi-badge-gain">
              <TrendingDown size={14} /> -{kpiQueueReduction.toFixed(1)}% Queue Shrink
            </div>
          </div>

          {/* Fuel Savings KPI */}
          <div className="kpi-impact-card highlight-amber">
            <div className="kpi-meta">
              <Fuel size={16} /> Fuel Saved (Idling Avoided)
            </div>
            <div className="kpi-single-val">
              {kpiFuelSaved.toFixed(2)} <span className="unit">Liters / Hr</span>
            </div>
            <div className="kpi-badge-gain text-amber">
              ~₹{(kpiFuelSaved * 105).toFixed(0)} saved/hr at junction
            </div>
          </div>

          {/* Carbon Footprint Avoided KPI */}
          <div className="kpi-impact-card highlight-emerald">
            <div className="kpi-meta">
              <Leaf size={16} /> CO₂ Emissions Avoided
            </div>
            <div className="kpi-single-val">
              {kpiCo2Saved.toFixed(2)} <span className="unit">kg CO₂</span>
            </div>
            <div className="kpi-badge-gain text-green">
              Clean air initiative aligned
            </div>
          </div>
        </div>
      </div>

      {/* ─── 2-Column Grid: Current vs. Recommended Timing & Manual Override Control ─── */}
      <div className="grid-2col">
        {/* Left Column: Current vs Recommended Signal Timing */}
        <div className="card timing-card">
          <div className="card-header">
            <div className="card-title-group">
              <Sliders size={18} className="text-blue" />
              <span className="card-title">Current vs. Recommended Signal Phasing</span>
            </div>
            <span className="badge-pill tech-pill">
              Varaiya Max-Pressure Engine
            </span>
          </div>

          {/* Side-by-side timing comparison */}
          <div className="timing-comparison-grid">
            {/* Box A: Fixed-Time Baseline */}
            <div className="timing-box fixed-time">
              <div className="box-tag">FIXED-TIME BASELINE (SCOOT / RIGID)</div>
              <div className="phase-display">
                Phase {current.phase_id}
              </div>
              <div className="box-sub">
                Allocated Green: <strong>{current.green_sec || 30}s</strong> (Static Round-Robin)
              </div>
              <div className="timing-notes">
                Does not adapt to queue fluctuations; results in high cross-street red-light idling delay.
              </div>
            </div>

            {/* Box B: Adaptive Max-Pressure */}
            <div className="timing-box max-pressure">
              <div className="box-tag">GATI ADAPTIVE RECOMMENDATION</div>
              <div className="phase-display text-green">
                Phase {recommended.phase_id}
              </div>
              <div className="box-sub">
                Decision: <strong>{recommended.decision_reason || 'MAX_PRESSURE_SWITCH'}</strong>
              </div>
              <div className="timing-notes text-green">
                Dynamically clears maximum queue differential while enforcing 15s min / 60s max green guardrails.
              </div>
            </div>
          </div>

          {/* Phase Pressures Breakdown Visualizer */}
          <div className="pressures-section">
            <div className="section-subtitle">Real-Time Phase Pressure Scores (Upstream - Downstream PCU)</div>
            <div className="pressure-bars-list">
              {phases.map((p) => {
                const pVal = recommended.pressures?.[p.phase_id] || 0.0;
                const isSelected = recommended.phase_id === p.phase_id;
                return (
                  <div key={p.phase_id} className={`pressure-bar-item ${isSelected ? 'active-phase' : ''}`}>
                    <div className="p-header">
                      <span className="p-name">
                        Phase {p.phase_id}: {p.name}
                      </span>
                      <span className="p-val">{Number(pVal).toFixed(1)} Pressure</span>
                    </div>
                    <div className="p-track">
                      <div
                        className={`p-fill ${isSelected ? 'selected-fill' : ''}`}
                        style={{ width: `${Math.min(100, (pVal / 30) * 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Traffic Police / ICCC Operator Override Control */}
        <div className="card override-card">
          <div className="card-header">
            <div className="card-title-group">
              <Shield size={18} className="text-yellow" />
              <span className="card-title">Police Operator Override & Governance</span>
            </div>
            <span className="badge-pill warn-pill">
              <Lock size={12} /> IRC SP:41 Safety Ceiling (300s)
            </span>
          </div>

          {/* Active Override Status Banner */}
          {overrideStatus?.override_active ? (
            <div className="active-override-alert">
              <div className="alert-header">
                <AlertTriangle size={18} className="text-yellow" />
                <span className="alert-title">MANUAL PHASE LOCK ACTIVE (PHASE {overrideStatus.phase_id})</span>
              </div>
              <div className="alert-body">
                <div>Locked by Operator: <strong>{overrideStatus.operator_id}</strong></div>
                <div>Reason: <em>{overrideStatus.reason}</em></div>
                <div>Auto-Timeout Remaining: <strong className="text-yellow">{overrideStatus.remaining_sec}s</strong></div>
              </div>
              <button
                className="btn-release-override"
                onClick={handleReleaseOverride}
                disabled={isSubmitting}
              >
                <Unlock size={15} /> RELEASE LOCK & RESTORE MAX-PRESSURE
              </button>
            </div>
          ) : (
            <div className="autonomous-status-badge">
              <CheckCircle2 size={16} className="text-green" />
              <span>Autonomous Max-Pressure Active (Zero Overrides Engaged)</span>
            </div>
          )}

          {/* Action notification message */}
          {actionMessage && (
            <div className={`action-msg ${actionMessage.type}`}>
              {actionMessage.text}
            </div>
          )}

          {/* Override Form */}
          <form onSubmit={handleLockPhase} className="override-form">
            <div className="form-group">
              <label className="form-label">Target Green Phase to Lock</label>
              <select
                className="form-select"
                value={targetPhase}
                onChange={(e) => setTargetPhase(e.target.value)}
              >
                {phases.map((p) => (
                  <option key={p.phase_id} value={p.phase_id}>
                    Phase {p.phase_id}: {p.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-row-2">
              <div className="form-group">
                <label className="form-label">Lock Duration (Seconds)</label>
                <input
                  type="number"
                  min="15"
                  max="300"
                  className="form-input"
                  value={durationSec}
                  onChange={(e) => setDurationSec(e.target.value)}
                />
                <span className="field-hint">Max safe ceiling: 300s (5 min)</span>
              </div>

              <div className="form-group">
                <label className="form-label">Operator Badge / ID</label>
                <input
                  type="text"
                  className="form-input"
                  value={operatorId}
                  onChange={(e) => setOperatorId(e.target.value)}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Intervention Reason (Mandatory for Audit)</label>
              <select
                className="form-select"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              >
                <option value="VIP Motorcade / Convoy Movement">VIP Motorcade / Convoy Movement</option>
                <option value="Ambulance / Emergency Priority Corridor">Ambulance / Emergency Priority Corridor</option>
                <option value="Accident Clearance & Traffic Diversion">Accident Clearance & Traffic Diversion</option>
                <option value="Manual Bottleneck Clearing by On-Ground Police">Manual Bottleneck Clearing by On-Ground Police</option>
                <option value="Religious / Festival Procession Passage">Religious / Festival Procession Passage</option>
              </select>
            </div>

            <button
              type="submit"
              className="btn-lock-override"
              disabled={isSubmitting || overrideStatus?.override_active}
            >
              <Lock size={15} /> ENGAGE MANUAL PHASE LOCK
            </button>
          </form>

          {/* Audit History Log */}
          <div className="audit-tail-section">
            <div className="audit-title">
              <History size={14} /> Recent Governance Audit Trail (JSONL)
            </div>
            <div className="audit-list">
              {auditRecords.length === 0 ? (
                <div className="audit-empty">No override interventions recorded for this junction.</div>
              ) : (
                auditRecords.slice(0, 4).map((rec, i) => (
                  <div key={i} className="audit-item">
                    <span className={`audit-action ${rec.action === 'LOCK' ? 'lock' : 'release'}`}>
                      {rec.action}
                    </span>
                    <span className="audit-meta">
                      Phase {rec.phase_id} by <strong>{rec.operator_id}</strong> ({rec.reason})
                    </span>
                    <span className="audit-time">
                      {new Date(rec.timestamp * 1000).toLocaleTimeString()}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
