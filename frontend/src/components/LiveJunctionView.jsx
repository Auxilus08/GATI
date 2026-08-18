import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  Camera,
  CircleDotDashed,
  Expand,
  Maximize2,
  ShieldAlert,
  Signal,
} from 'lucide-react';

const FALLBACK_APPROACHES = [
  { id: 'APP_NORTH', name: 'Wardha Road — North approach', direction: 'Northbound', lanes: 3 },
  { id: 'APP_EAST', name: 'Central Avenue — East approach', direction: 'Eastbound', lanes: 3 },
  { id: 'APP_SOUTH', name: 'Wardha Road — South approach', direction: 'Southbound', lanes: 3 },
  { id: 'APP_WEST', name: 'Maharajbagh Road — West approach', direction: 'Westbound', lanes: 2 },
];

const FALLBACK_TELEMETRY = {
  APP_NORTH: { total_pcu: 22, queue_length_m: 76, avg_speed_kmh: 28, vehicle_counts: { two_wheeler: 14, auto_rickshaw: 3, car: 8, bus: 1, truck: 0 } },
  APP_EAST: { total_pcu: 29, queue_length_m: 112, avg_speed_kmh: 17, vehicle_counts: { two_wheeler: 18, auto_rickshaw: 6, car: 9, bus: 1, truck: 1 } },
  APP_SOUTH: { total_pcu: 17, queue_length_m: 54, avg_speed_kmh: 33, vehicle_counts: { two_wheeler: 10, auto_rickshaw: 3, car: 6, bus: 0, truck: 0 } },
  APP_WEST: { total_pcu: 12, queue_length_m: 38, avg_speed_kmh: 36, vehicle_counts: { two_wheeler: 7, auto_rickshaw: 2, car: 5, bus: 0, truck: 0 } },
};

const directionFor = (approach, index) => approach.direction || ['Northbound', 'Eastbound', 'Southbound', 'Westbound', 'Inbound'][index % 5];
const shortName = (approach) => (approach.name || approach.id).replace(/\s*\([^)]*\)/, '').replace(/\s*—.*/, '');

function FeedScene({ approach, telemetry, isActive, compact, onSelect, phaseActive }) {
  const vehicleCount = Math.max(3, Math.min(8, Math.round(Number(telemetry.total_pcu || 8) / 4)));
  const queue = Number(telemetry.queue_length_m || telemetry.total_pcu * 5.5 || 0);
  const speed = Number(telemetry.avg_speed_kmh || 0);
  const direction = directionFor(approach, 0);

  return (
    <button
      type="button"
      className={`junction-feed ${compact ? 'junction-feed--compact' : 'junction-feed--main'} ${isActive ? 'is-selected' : ''}`}
      onClick={onSelect}
      aria-pressed={isActive}
      aria-label={`Open ${shortName(approach)} camera feed`}
    >
      <div className="junction-feed__road" aria-hidden="true">
        <div className="junction-feed__median" />
        <div className="junction-feed__stop-line" />
        {[...Array(vehicleCount)].map((_, index) => (
          <span
            className={`junction-feed__vehicle vehicle-${index % 4}`}
            key={`${approach.id}-${index}`}
            style={{ '--vehicle-x': `${10 + ((index * 19) % 80)}%`, '--vehicle-y': `${16 + ((index * 23) % 68)}%` }}
          />
        ))}
        <span className="junction-feed__scan-line" />
      </div>
      <span className="junction-feed__topline">
        <span className="junction-feed__live"><i /> LIVE</span>
        <span>CAM {approach.id.replace('APP_', '')}</span>
      </span>
      <span className="junction-feed__label">
        <strong>{shortName(approach)}</strong>
        <small>{direction} · {approach.lanes || 2} lanes</small>
      </span>
      {!compact && (
        <span className="junction-feed__metrics">
          <span><b>{queue.toFixed(0)}m</b> queue</span>
          <span><b>{speed.toFixed(0)} km/h</b> flow</span>
          <span className={phaseActive ? 'feed-status feed-status--go' : 'feed-status'}>{phaseActive ? 'Green movement' : 'Hold line'}</span>
        </span>
      )}
      {telemetry.emergency && <span className="junction-feed__emergency"><ShieldAlert size={13} /> Priority vehicle</span>}
    </button>
  );
}

export default function LiveJunctionView({ junction, telemetry, signalTiming }) {
  const approaches = junction?.approaches?.length ? junction.approaches : FALLBACK_APPROACHES;
  const [selectedCam, setSelectedCam] = useState(approaches[0]?.id || 'APP_NORTH');
  const signal = signalTiming?.recommended || telemetry?.signal || {};
  const currentPhaseId = signalTiming?.current?.phase_id || signal.current_phase_id || 1;
  const currentPhase = junction?.phases?.find((phase) => phase.phase_id === currentPhaseId);

  useEffect(() => {
    if (!approaches.some((approach) => approach.id === selectedCam)) setSelectedCam(approaches[0]?.id || 'APP_NORTH');
  }, [approaches, selectedCam]);

  const approachTelemetry = useMemo(() => Object.fromEntries(approaches.map((approach, index) => [
    approach.id,
    telemetry?.approaches?.[approach.id] || FALLBACK_TELEMETRY[approach.id] || {
      total_pcu: 10 + index * 3,
      queue_length_m: 35 + index * 18,
      avg_speed_kmh: 32 - index * 3,
      vehicle_counts: {},
    },
  ])), [approaches, telemetry]);

  const activeApproach = approaches.find((approach) => approach.id === selectedCam) || approaches[0];
  const activeTelemetry = approachTelemetry[activeApproach?.id] || {};
  const activeIds = currentPhase?.active_approaches || [];
  const totalDetected = approaches.reduce((sum, approach) => sum + Number(approachTelemetry[approach.id]?.total_pcu || 0), 0);
  const activeGreen = signalTiming?.recommended?.elapsed_green_sec || telemetry?.signal?.elapsed_green_sec || 0;

  return (
    <div className="panel-container live-operations">
      <section className="live-command-bar" aria-label="Live signal status">
        <div className="live-command-bar__signal"><Signal size={20} /><div><strong>Phase {currentPhaseId} active</strong><span>{currentPhase?.name || 'Adaptive signal operation'}</span></div></div>
        <div className="live-command-bar__readout"><span>Current green</span><strong>{Number(activeGreen).toFixed(0)}s</strong></div>
        <div className="live-command-bar__readout"><span>Junction arrivals</span><strong>{totalDetected.toFixed(0)} PCU</strong></div>
        <div className="live-command-bar__mode"><i /> AI adaptive control</div>
      </section>

      <section className="live-camera-console card" aria-labelledby="camera-console-title">
        <header className="live-camera-console__header">
          <div className="card-title-group"><Camera size={19} className="text-blue" /><div><h2 id="camera-console-title" className="card-title">Live AI camera matrix</h2><span className="sub-caption">Synthetic edge-feed visualization · detections update with telemetry</span></div></div>
          <div className="live-camera-console__health"><CircleDotDashed size={15} /> {approaches.length} approaches online <span>30 FPS</span></div>
        </header>

        <div className="camera-console-grid">
          <div className="camera-console-grid__primary">
            <FeedScene approach={activeApproach} telemetry={activeTelemetry} isActive phaseActive={activeIds.includes(activeApproach?.id)} onSelect={() => setSelectedCam(activeApproach?.id)} />
            <div className="camera-console-grid__primary-footer"><span><Activity size={14} /> AI tracking: vehicles, queues & speed</span><span><Expand size={14} /> Select any road feed below</span></div>
          </div>
          <div className="camera-console-grid__matrix" aria-label="Other junction approaches">
            {approaches.filter((approach) => approach.id !== activeApproach?.id).map((approach) => (
              <FeedScene key={approach.id} approach={approach} telemetry={approachTelemetry[approach.id]} compact isActive={selectedCam === approach.id} phaseActive={activeIds.includes(approach.id)} onSelect={() => setSelectedCam(approach.id)} />
            ))}
          </div>
        </div>
      </section>

      <section className="junction-layout-card card" aria-labelledby="junction-layout-title">
        <header className="junction-layout-card__header"><div><h2 id="junction-layout-title">Intersection movement view</h2><p>Every incoming road is tied to the centre signal controller. Select a road or camera to inspect its live approach.</p></div><span><Maximize2 size={15} /> {approaches.length}-arm junction</span></header>
        <div className="junction-layout">
          <div className="junction-layout__road junction-layout__road--north" />
          <div className="junction-layout__road junction-layout__road--east" />
          <div className="junction-layout__road junction-layout__road--south" />
          <div className="junction-layout__road junction-layout__road--west" />
          <div className="junction-layout__centre"><Signal size={25} /><strong>AI SIGNAL</strong><span>Phase {currentPhaseId}</span></div>
          {approaches.slice(0, 4).map((approach, index) => {
            const positions = ['north', 'east', 'south', 'west'];
            const active = activeIds.includes(approach.id);
            return <button type="button" key={approach.id} className={`junction-layout__approach junction-layout__approach--${positions[index]} ${selectedCam === approach.id ? 'is-selected' : ''}`} onClick={() => setSelectedCam(approach.id)} aria-pressed={selectedCam === approach.id}><i className={active ? 'is-green' : ''} /><strong>{shortName(approach)}</strong><span>{Number(approachTelemetry[approach.id]?.queue_length_m || 0).toFixed(0)}m queue · {active ? 'moving' : 'waiting'}</span></button>;
          })}
        </div>
        <div className="approach-strip">
          {approaches.map((approach) => { const data = approachTelemetry[approach.id]; const queue = Number(data.queue_length_m || data.total_pcu * 5.5 || 0); return <button type="button" key={approach.id} className={selectedCam === approach.id ? 'is-selected' : ''} onClick={() => setSelectedCam(approach.id)}><span><i className={activeIds.includes(approach.id) ? 'is-green' : ''} />{directionFor(approach, 0)}</span><strong>{Number(data.total_pcu || 0).toFixed(0)} vehicles</strong><small>{queue.toFixed(0)}m queue · {Number(data.avg_speed_kmh || 0).toFixed(0)} km/h</small></button>; })}
        </div>
      </section>
    </div>
  );
}
