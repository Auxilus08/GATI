import React, { useState, useEffect } from 'react';
import { Camera, Activity, AlertCircle, ShieldAlert, Cpu, Eye, ArrowUpRight, Gauge } from 'lucide-react';

export default function LiveJunctionView({ junction, telemetry, signalTiming }) {
  const [selectedCam, setSelectedCam] = useState('APP_NORTH');
  const [playbackTime, setPlaybackTime] = useState(0);

  // Animate video simulation frame elements
  useEffect(() => {
    const timer = setInterval(() => {
      setPlaybackTime((prev) => (prev + 1) % 1000);
    }, 100);
    return () => clearInterval(timer);
  }, []);

  const approaches = junction?.approaches || [];
  const approachesData = telemetry?.approaches || {};
  const signal = signalTiming?.recommended || telemetry?.signal || {};
  const currentPhaseId = signalTiming?.current?.phase_id || signal?.current_phase_id || 1;
  const currentPhase = junction?.phases?.find((p) => p.phase_id === currentPhaseId) || {
    name: `Phase ${currentPhaseId}`,
    phase_id: currentPhaseId,
    active_approaches: ['APP_NORTH', 'APP_SOUTH'],
  };

  const activeCam = approaches.find((a) => a.id === selectedCam) || approaches[0] || {
    id: 'APP_NORTH',
    name: 'Wardha Road (Northbound)',
    lanes: 3,
  };

  const currentApproachTelemetry = approachesData[selectedCam] || {
    total_pcu: 14.5,
    queue_length_m: 87.0,
    avg_speed_kmh: 22.4,
    vehicle_counts: { two_wheeler: 8, auto_rickshaw: 4, car: 5, bus: 1 },
    emergency: false,
  };

  const pcuVal = Number(currentApproachTelemetry.total_pcu ?? 0);
  const queueVal = Number(currentApproachTelemetry.queue_length_m ?? (pcuVal * 6.0));
  const speedVal = Number(currentApproachTelemetry.avg_speed_kmh ?? 20.0);

  // Simulated bounding box tracks matching real Indian traffic classes
  const simulatedTracks = [
    { id: 101, class: 'auto_rickshaw', label: '🛺 Auto #101', bbox: [220, 180, 70, 75], speed: 18.4, pcu: 0.8 },
    { id: 102, class: 'two_wheeler', label: '🏍 2W #102', bbox: [160, 240, 45, 60], speed: 28.2, pcu: 0.5 },
    { id: 103, class: 'car', label: '🚗 Car #103', bbox: [320, 140, 90, 85], speed: 22.1, pcu: 1.0 },
    { id: 104, class: 'bus', label: '🚌 Bus #104', bbox: [430, 90, 110, 130], speed: 14.5, pcu: 3.0 },
    { id: 105, class: 'two_wheeler', label: '🏍 2W #105', bbox: [270, 260, 40, 55], speed: 24.0, pcu: 0.5 },
  ];

  return (
    <div className="panel-container">
      {/* ─── Top Signal Phase & Real-Time Status HUD ─── */}
      <div className="hud-banner">
        <div className="hud-signal-group">
          <div className="traffic-signal-box">
            <div className={`signal-bulb red ${telemetry?.signal?.signal_state === 'ALL_RED' ? 'active' : ''}`} />
            <div className={`signal-bulb amber ${telemetry?.signal?.signal_state === 'AMBER' ? 'active' : ''}`} />
            <div className={`signal-bulb green ${telemetry?.signal?.signal_state !== 'ALL_RED' && telemetry?.signal?.signal_state !== 'AMBER' ? 'active' : ''}`} />
          </div>
          <div>
            <div className="hud-eyebrow">ACTIVE SIGNAL PHASE</div>
            <div className="hud-title">
              Phase {currentPhase.phase_id}: {currentPhase.name}
            </div>
          </div>
        </div>

        <div className="hud-stats-group">
          <div className="hud-stat-item">
            <span className="stat-label">Elapsed Green</span>
            <span className="stat-value highlight">
              {signalTiming?.recommended?.elapsed_green_sec || telemetry?.signal?.elapsed_green_sec || '18.0'}s
            </span>
          </div>
          <div className="hud-stat-item">
            <span className="stat-label">Control Mode</span>
            <span className="stat-badge max-pressure">
              {signalTiming?.override_active ? 'OPERATOR OVERRIDE' : 'ADAPTIVE MAX-PRESSURE'}
            </span>
          </div>
          <div className="hud-stat-item">
            <span className="stat-label">Decision Status</span>
            <span className="stat-value text-muted">
              {signalTiming?.recommended?.decision_reason || 'MAX_PRESSURE_HOLD'}
            </span>
          </div>
        </div>
      </div>

      {/* ─── Main 2-Column Grid: Video Feed with Detection Overlay & Approaches Breakdown ─── */}
      <div className="grid-2col">
        {/* Left Column: Live Video Feed Simulation with Detection Overlays */}
        <div className="card feed-card">
          <div className="card-header">
            <div className="card-title-group">
              <Camera size={18} className="text-blue" />
              <span className="card-title">Edge CCTV Feed & Bounding Box Overlay</span>
            </div>
            <div className="feed-tags">
              <span className="badge-pill live-pill">
                <span className="pulse-dot"></span> LIVE 1080p
              </span>
              <span className="badge-pill tech-pill">
                <Cpu size={12} /> YOLOv8n + ByteTrack (FP16)
              </span>
            </div>
          </div>

          {/* Camera Channel Tabs */}
          <div className="camera-tabs">
            {approaches.map((app) => (
              <button
                key={app.id}
                className={`cam-tab-btn ${selectedCam === app.id ? 'active' : ''}`}
                onClick={() => setSelectedCam(app.id)}
              >
                {app.direction || 'Approach'}: {(app.name || app.id).split('(')[0]}
                {approachesData[app.id]?.emergency && (
                  <ShieldAlert size={13} className="text-red" style={{ marginLeft: 4 }} />
                )}
              </button>
            ))}
          </div>

          {/* Simulated CCTV Stream Canvas Container */}
          <div className="video-viewport">
            {/* Background Grid & Road Lanes */}
            <div className="road-carriageway">
              <div className="lane-divider divider-1" />
              <div className="lane-divider divider-2" />
              <div className="stopline-marker">
                <span className="stopline-text">APPROACH STOPLINE (IRC SP:41 ROI)</span>
              </div>
            </div>

            {/* Live Bounding Box Detections Overlay */}
            {simulatedTracks.map((trk) => {
              const yOffset = ((trk.bbox[1] + playbackTime * 2) % 320);
              return (
                <div
                  key={trk.id}
                  className={`detection-box box-${trk.class}`}
                  style={{
                    left: `${trk.bbox[0]}px`,
                    top: `${yOffset}px`,
                    width: `${trk.bbox[2]}px`,
                    height: `${trk.bbox[3]}px`,
                  }}
                >
                  <div className="detection-tag">
                    {trk.label} | {trk.speed} km/h | {trk.pcu} PCU
                  </div>
                </div>
              );
            })}

            {/* Approach Queue Length & PCU Metric Overlay */}
            <div className="feed-hud-overlay">
              <div className="overlay-metric">
                <span className="metric-label">Selected Approach:</span>
                <span className="metric-val">{activeCam.name || activeCam.id}</span>
              </div>
              <div className="overlay-metric">
                <span className="metric-label">Queue Length:</span>
                <span className="metric-val highlight">
                  {queueVal.toFixed(1)} m
                </span>
              </div>
              <div className="overlay-metric">
                <span className="metric-label">Approach PCU:</span>
                <span className="metric-val">{pcuVal.toFixed(1)} PCU</span>
              </div>
              <div className="overlay-metric">
                <span className="metric-label">Avg Speed:</span>
                <span className="metric-val">{speedVal.toFixed(1)} km/h</span>
              </div>
            </div>

            {/* Emergency Vehicle Alert Banner on Feed */}
            {currentApproachTelemetry.emergency && (
              <div className="feed-emergency-banner">
                <ShieldAlert size={18} /> EMERGENCY VEHICLE PRIORITY OVERRIDE ENGAGED
              </div>
            )}
          </div>

          <div className="feed-footer-meta">
            <span>Camera Source: <code>{activeCam.camera_source || 'rtsp://edge-gateway.nagpur:554/stream1'}</code></span>
            <span>Edge Inference Latency: <strong>14.2 ms</strong> | Bandwidth: <strong>3.8 KB/s</strong></span>
          </div>
        </div>

        {/* Right Column: Per-Approach PCU & Queue Length Breakdown */}
        <div className="card approaches-card">
          <div className="card-header">
            <div className="card-title-group">
              <Activity size={18} className="text-green" />
              <span className="card-title">Live Approach Queue Metrics (Lane-Free)</span>
            </div>
            <span className="sub-caption">Indian Road Congress PCU Weights</span>
          </div>

          <div className="approaches-list">
            {approaches.map((app) => {
              const data = approachesData[app.id] || {
                total_pcu: 0,
                queue_length_m: 0,
                avg_speed_kmh: 0,
                vehicle_counts: {},
                emergency: false,
              };
              const isPhaseActive = currentPhase?.active_approaches?.includes(app.id);
              const queueLength = data.queue_length_m || data.total_pcu * 6.0;
              const pressure = signalTiming?.recommended?.pressures?.[app.id] || data.total_pcu;

              return (
                <div
                  key={app.id}
                  className={`approach-metric-card ${isPhaseActive ? 'phase-green' : 'phase-red'} ${selectedCam === app.id ? 'selected' : ''}`}
                  onClick={() => setSelectedCam(app.id)}
                >
                  <div className="approach-header">
                    <div className="approach-name-group">
                      <span className={`phase-dot ${isPhaseActive ? 'green' : 'red'}`} />
                      <div>
                        <div className="approach-title">{app.name}</div>
                        <div className="approach-dir-tag">
                          {app.direction} • {app.lanes} Lanes • Saturation: {app.saturation_flow_pcu_hr} PCU/hr
                        </div>
                      </div>
                    </div>
                    <div className="phase-indicator-pill">
                      {isPhaseActive ? 'GREEN (DISCHARGING)' : 'RED (ACCUMULATING)'}
                    </div>
                  </div>

                  <div className="approach-metrics-grid">
                    <div className="metric-box">
                      <span className="m-label">Queue PCU</span>
                      <span className="m-val">{Number(data.total_pcu ?? 0).toFixed(1)}</span>
                    </div>
                    <div className="metric-box">
                      <span className="m-label">Queue Length</span>
                      <span className="m-val highlight">{Number(queueLength ?? 0).toFixed(1)}m</span>
                    </div>
                    <div className="metric-box">
                      <span className="m-label">Avg Speed</span>
                      <span className="m-val">{Number(data.avg_speed_kmh ?? 20).toFixed(1)} km/h</span>
                    </div>
                    <div className="metric-box">
                      <span className="m-label">Net Pressure</span>
                      <span className="m-val text-blue">{Number(pressure ?? 0).toFixed(1)}</span>
                    </div>
                  </div>

                  {/* Vehicle Class Composition Chips */}
                  <div className="vehicle-class-chips">
                    <span className="v-chip">🏍 {data.vehicle_counts?.two_wheeler || 0} 2W</span>
                    <span className="v-chip">🛺 {data.vehicle_counts?.auto_rickshaw || 0} Auto</span>
                    <span className="v-chip">🚗 {data.vehicle_counts?.car || 0} Car</span>
                    <span className="v-chip">🚌 {data.vehicle_counts?.bus || 0} Bus</span>
                    <span className="v-chip">🚛 {data.vehicle_counts?.truck || 0} Truck</span>
                  </div>

                  {/* Progress Bar for Queue Capacity */}
                  <div className="queue-bar-track">
                    <div
                      className={`queue-bar-fill ${queueLength > 80 ? 'danger' : queueLength > 40 ? 'warning' : 'safe'}`}
                      style={{ width: `${Math.min(100, (queueLength / 120) * 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
