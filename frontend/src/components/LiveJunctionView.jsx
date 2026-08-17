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

  const APPROACH_DEFAULT_TELEMETRY = {
    APP_NORTH: {
      total_pcu: 21.5,
      queue_length_m: 129.0,
      avg_speed_kmh: 34.2,
      vehicle_counts: { two_wheeler: 14, auto_rickshaw: 4, car: 9, bus: 2, truck: 0 },
      emergency: false,
    },
    APP_SOUTH: {
      total_pcu: 18.2,
      queue_length_m: 109.2,
      avg_speed_kmh: 29.5,
      vehicle_counts: { two_wheeler: 11, auto_rickshaw: 3, car: 7, bus: 1, truck: 1 },
      emergency: false,
    },
    APP_EAST: {
      total_pcu: 26.8,
      queue_length_m: 160.8,
      avg_speed_kmh: 16.4,
      vehicle_counts: { two_wheeler: 18, auto_rickshaw: 12, car: 5, bus: 0, truck: 1 },
      emergency: false,
    },
    APP_WEST: {
      total_pcu: 8.5,
      queue_length_m: 51.0,
      avg_speed_kmh: 28.0,
      vehicle_counts: { two_wheeler: 9, auto_rickshaw: 2, car: 3, bus: 0, truck: 0 },
      emergency: false,
    },
  };

  const currentApproachTelemetry = approachesData[selectedCam] || APPROACH_DEFAULT_TELEMETRY[selectedCam] || APPROACH_DEFAULT_TELEMETRY.APP_NORTH;
  const pcuVal = Number(currentApproachTelemetry.total_pcu ?? 0);
  const queueVal = Number(currentApproachTelemetry.queue_length_m ?? (pcuVal * 6.0));
  const speedVal = Number(currentApproachTelemetry.avg_speed_kmh ?? 20.0);

  // Simulated bounding box tracks uniquely tailored to each Indian road approach & direction
  const APPROACH_SPECIFIC_TRACKS = {
    APP_NORTH: [
      { id: 101, class: 'bus', label: '🚌 Volvo City Bus #101', bbox: [120, 40, 110, 140], speed: 32.4, pcu: 3.0 },
      { id: 102, class: 'car', label: '🚗 White Sedan #102', bbox: [250, 160, 85, 80], speed: 38.5, pcu: 1.0 },
      { id: 103, class: 'car', label: '🚙 SUV #103', bbox: [360, 90, 90, 85], speed: 35.0, pcu: 1.0 },
      { id: 104, class: 'two_wheeler', label: '🏍 Pulsar #104', bbox: [170, 230, 40, 55], speed: 42.1, pcu: 0.5 },
      { id: 105, class: 'two_wheeler', label: '🏍 Activa #105', bbox: [290, 250, 38, 50], speed: 36.8, pcu: 0.5 },
      { id: 106, class: 'auto_rickshaw', label: '🛺 CNG Auto #106', bbox: [410, 210, 65, 70], speed: 26.2, pcu: 0.8 },
    ],
    APP_SOUTH: [
      { id: 201, class: 'truck', label: '🚛 Logistics Truck #201', bbox: [330, 30, 115, 150], speed: 24.5, pcu: 3.0 },
      { id: 202, class: 'bus', label: '🚌 State Transport Bus #202', bbox: [130, 80, 105, 135], speed: 28.0, pcu: 3.0 },
      { id: 203, class: 'car', label: '🚗 Red Hatchback #203', bbox: [250, 170, 80, 75], speed: 34.2, pcu: 1.0 },
      { id: 204, class: 'two_wheeler', label: '🏍 Splendor #204', bbox: [180, 240, 40, 55], speed: 31.0, pcu: 0.5 },
      { id: 205, class: 'auto_rickshaw', label: '🛺 Auto #205', bbox: [380, 220, 68, 72], speed: 22.4, pcu: 0.8 },
    ],
    APP_EAST: [
      { id: 301, class: 'auto_rickshaw', label: '🛺 Green Auto #301', bbox: [160, 140, 65, 70], speed: 16.2, pcu: 0.8 },
      { id: 302, class: 'auto_rickshaw', label: '🛺 Yellow Auto #302', bbox: [250, 190, 65, 70], speed: 14.8, pcu: 0.8 },
      { id: 303, class: 'auto_rickshaw', label: '🛺 Shared Auto #303', bbox: [350, 110, 68, 72], speed: 18.0, pcu: 0.8 },
      { id: 304, class: 'car', label: '🚕 Yellow Taxi #304', bbox: [180, 50, 80, 75], speed: 19.5, pcu: 1.0 },
      { id: 305, class: 'two_wheeler', label: '🛵 Delivery 2W #305', bbox: [320, 230, 42, 55], speed: 22.0, pcu: 0.5 },
      { id: 306, class: 'truck', label: '🚚 Mini-Tempo #306', bbox: [260, 20, 90, 100], speed: 15.0, pcu: 1.5 },
    ],
    APP_WEST: [
      { id: 401, class: 'two_wheeler', label: '🏍 Enfield #401', bbox: [190, 210, 45, 60], speed: 29.5, pcu: 0.5 },
      { id: 402, class: 'two_wheeler', label: '🛵 Scooter #402', bbox: [260, 240, 40, 50], speed: 26.0, pcu: 0.5 },
      { id: 403, class: 'two_wheeler', label: '🏍 Commuter 2W #403', bbox: [340, 200, 42, 55], speed: 28.4, pcu: 0.5 },
      { id: 404, class: 'car', label: '🚗 Electric Car #404', bbox: [210, 90, 85, 80], speed: 31.2, pcu: 1.0 },
      { id: 405, class: 'auto_rickshaw', label: '🛺 Auto #405', bbox: [320, 130, 65, 70], speed: 21.0, pcu: 0.8 },
    ],
  };

  const simulatedTracks = APPROACH_SPECIFIC_TRACKS[selectedCam] || APPROACH_SPECIFIC_TRACKS.APP_NORTH;


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
            <span className="stat-label">Cabinet Hardware</span>
            <span className="stat-badge safe" style={{ backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.3)' }}>
              NTCIP 1202 CMU OK
            </span>
          </div>
          <div className="hud-stat-item">
            <span className="stat-label">Edge Thermal / Power</span>
            <span className="stat-value text-blue" style={{ fontSize: '13px', fontWeight: 600 }}>
              48.5°C • 8.4W
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
              <span className="badge-pill" style={{ backgroundColor: 'rgba(56, 189, 248, 0.12)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.25)', fontSize: '11px', padding: '3px 8px', borderRadius: '4px' }}>
                📐 4-Point Homography (m/px)
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
