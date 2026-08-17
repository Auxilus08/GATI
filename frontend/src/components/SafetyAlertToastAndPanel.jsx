import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  Ambulance,
  PhoneCall,
  Navigation,
  CheckCircle2,
  Clock,
  Car,
  RotateCcw,
  Zap,
  Radio,
  Eye,
  UserCheck,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  fetchSafetyEvents,
  reportSafetyEvent,
  acknowledgeSafetyEvent,
} from '../services/api';

export default function SafetyAlertToastAndPanel({ junctionId = 'NGP_J01_SITABULDI', onEventAction }) {
  const [events, setEvents] = useState([]);
  const [activeAlert, setActiveAlert] = useState(null);
  const [isDispatching, setIsDispatching] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [showLogDrawer, setShowLogDrawer] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Poll for safety events
  const loadEvents = async () => {
    try {
      const res = await fetchSafetyEvents(null, 15);
      if (res?.events) {
        setEvents(res.events);
        // If there's an unacknowledged pending event, make it the active popup
        const unacked = res.events.find((e) => !e.acknowledged && e.status === 'PENDING_OPERATOR_ACK');
        if (unacked && (!activeAlert || activeAlert.event_id !== unacked.event_id)) {
          setActiveAlert(unacked);
        }
      }
    } catch (e) {
      console.warn('Checking safety events...', e);
    }
  };

  useEffect(() => {
    loadEvents();
    const interval = setInterval(loadEvents, 2500);
    return () => clearInterval(interval);
  }, [junctionId]);

  const handleAcknowledgeAndDispatch = async (eventId, actionType) => {
    setIsDispatching(true);
    try {
      await acknowledgeSafetyEvent(eventId, {
        operatorId: 'ICCC_OPERATOR_CHIEF_MH31',
        dispatchAction: actionType || 'DISPATCH_NEAREST_PATROL_AND_AMBULANCE',
        notes: `Emergency response dispatched via 1-Click ICCC console for ${activeAlert?.junction_id}`,
      });

      setFeedback({
        type: 'success',
        text: `✅ DISPATCH CONFIRMED: Nearest units notified. Audit log permanently stamped (Operator: ICCC_OPERATOR_CHIEF_MH31).`,
      });

      setActiveAlert(null);
      await loadEvents();
      if (onEventAction) onEventAction();
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err.message || 'Failed to dispatch authority unit',
      });
    } finally {
      setIsDispatching(false);
    }
  };

  // Simulate Edge Accident
  const handleSimulateEdgeAccident = async () => {
    setIsSimulating(true);
    setFeedback(null);
    try {
      await reportSafetyEvent({
        junction_id: junctionId,
        event_type: 'accident_suspected',
        confidence: 0.95,
        gps_coordinates: { lat: 21.1458, lng: 79.0882 },
        approach_id: 'APP_NORTH',
        track_id: Math.floor(100 + Math.random() * 899),
        vehicle_class: 'car',
        details: {
          description: 'Sudden deceleration (-32 km/h) & lateral vehicle skid anomaly on Northbound Wardha Road',
          speed_kmh: 0.0,
          reasons: ['Sudden deceleration drop (-32.0 km/h)', 'Overturned vehicle orientation (AR=2.8)'],
        },
        snapshot_jpeg_base64: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
      });

      setFeedback({
        type: 'info',
        text: '🚨 Edge AI Accident Event Ingested! Nearest authorities resolved in <20ms.',
      });

      await loadEvents();
    } catch (err) {
      setFeedback({ type: 'error', text: err.message });
    } finally {
      setIsSimulating(false);
    }
  };

  // Simulate Edge Ambulance
  const handleSimulateEdgeAmbulance = async () => {
    setIsSimulating(true);
    setFeedback(null);
    try {
      await reportSafetyEvent({
        junction_id: junctionId,
        event_type: 'ambulance_detected',
        confidence: 0.98,
        gps_coordinates: { lat: 21.1458, lng: 79.0882 },
        approach_id: 'APP_NORTH',
        track_id: Math.floor(100 + Math.random() * 899),
        vehicle_class: 'ambulance',
        details: {
          description: 'Emergency 108 Ambulance detected entering intersection with siren flashers active',
          speed_kmh: 52.0,
        },
      });

      setFeedback({
        type: 'info',
        text: '🚑 Edge AI Ambulance Detected! Green Corridor engaged and emergency dispatch alert logged.',
      });

      await loadEvents();
    } catch (err) {
      setFeedback({ type: 'error', text: err.message });
    } finally {
      setIsSimulating(false);
    }
  };

  const primaryAuth = activeAlert?.nearest_authorities?.primary;
  const medicalAuth = activeAlert?.nearest_authorities?.medical;

  return (
    <div style={{ marginBottom: '20px' }}>
      {/* ─── Active Emergency Pop-Up Alert Modal / Banner ─── */}
      {activeAlert && (
        <div
          style={{
            backgroundColor: activeAlert.event_type === 'accident_suspected' ? '#180e14' : '#0e1824',
            border: `2px solid ${activeAlert.event_type === 'accident_suspected' ? '#ef4444' : '#38bdf8'}`,
            borderRadius: '12px',
            padding: '18px 22px',
            boxShadow: activeAlert.event_type === 'accident_suspected' ? '0 0 30px rgba(239, 68, 68, 0.4)' : '0 0 30px rgba(56, 189, 248, 0.3)',
            marginBottom: '16px',
            animation: 'pulse 1.2s infinite alternate',
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '8px',
                  backgroundColor: activeAlert.event_type === 'accident_suspected' ? '#ef4444' : '#0284c7',
                  color: '#ffffff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {activeAlert.event_type === 'accident_suspected' ? <ShieldAlert size={20} /> : <Ambulance size={20} />}
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '15px', fontWeight: 800, color: '#ffffff' }}>
                    {activeAlert.event_type === 'accident_suspected' ? '🚨 REAL-TIME ACCIDENT SUSPECTED' : '🚑 EMERGENCY AMBULANCE DETECTED'}
                  </span>
                  <span
                    style={{
                      backgroundColor: 'rgba(255, 255, 255, 0.2)',
                      padding: '2px 8px',
                      borderRadius: '10px',
                      fontSize: '11px',
                      fontWeight: 700,
                      color: '#ffffff',
                    }}
                  >
                    CONFIDENCE: {(activeAlert.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '2px' }}>
                  Location: <strong>{activeAlert.junction_id}</strong> ({activeAlert.approach_id || 'Northbound'}) • Track #{activeAlert.track_id} ({activeAlert.vehicle_class})
                </div>
              </div>
            </div>

            <button
              onClick={() => setActiveAlert(null)}
              style={{
                backgroundColor: 'transparent',
                border: '1px solid #475569',
                color: '#94a3b8',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '11px',
                cursor: 'pointer',
              }}
            >
              Minimize
            </button>
          </div>

          {/* Details & Nearest Authority Dispatch Box */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '14px', marginBottom: '14px' }}>
            {/* Left: Incident Details & Auto-Signal Action */}
            <div
              style={{
                backgroundColor: '#0c1424',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #1e2d45',
              }}
            >
              <div style={{ fontSize: '12px', color: '#e2e8f0', marginBottom: '8px' }}>
                {activeAlert.details?.description || 'Vehicle anomaly detected by Edge YOLOv8 + ByteTrack tracker.'}
              </div>

              {activeAlert.auto_signal_action && (
                <div
                  style={{
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    border: '1px solid rgba(52, 211, 153, 0.3)',
                    color: '#34d399',
                    fontSize: '11.5px',
                    fontWeight: 700,
                    padding: '6px 10px',
                    borderRadius: '6px',
                  }}
                >
                  🛡️ AUTOMATED SIGNAL ACTION: {activeAlert.auto_signal_action.replace(/_/g, ' ')}
                </div>
              )}
            </div>

            {/* Right: Resolved Nearest Authority Contact */}
            <div
              style={{
                backgroundColor: '#0c1424',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #1e2d45',
              }}
            >
              <div style={{ fontSize: '11px', fontWeight: 700, color: '#38bdf8', marginBottom: '6px' }}>
                📍 RESOLVED NEAREST EMERGENCY UNITS:
              </div>

              {primaryAuth && (
                <div style={{ fontSize: '12px', color: '#f8fafc', marginBottom: '4px' }}>
                  🚔 <strong>Police:</strong> {primaryAuth.station_name}
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                    Distance: <strong>{primaryAuth.distance_km} km</strong> (ETA: <strong>{primaryAuth.estimated_arrival_minutes} min</strong>) • 📞 {primaryAuth.contact_number}
                  </div>
                </div>
              )}

              {medicalAuth && (
                <div style={{ fontSize: '12px', color: '#f8fafc', marginTop: '6px' }}>
                  🚑 <strong>Medical:</strong> {medicalAuth.station_name}
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                    Distance: <strong>{medicalAuth.distance_km} km</strong> (ETA: <strong>{medicalAuth.estimated_arrival_minutes} min</strong>) • 📞 {medicalAuth.contact_number}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 1-Click Action Buttons */}
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={() => handleAcknowledgeAndDispatch(activeAlert.event_id, 'DISPATCH_NEAREST_PATROL_AND_AMBULANCE')}
              disabled={isDispatching}
              style={{
                flex: 1,
                backgroundColor: '#059669',
                color: '#ffffff',
                border: 'none',
                padding: '10px 16px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 800,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                boxShadow: '0 0 14px rgba(16, 185, 129, 0.4)',
              }}
            >
              <PhoneCall size={16} /> 1-CLICK DISPATCH NEAREST UNITS & LOG AUDIT
            </button>

            <button
              onClick={() => handleAcknowledgeAndDispatch(activeAlert.event_id, 'ACKNOWLEDGE_MONITOR_ONLY')}
              disabled={isDispatching}
              style={{
                backgroundColor: '#1e293b',
                color: '#f8fafc',
                border: '1px solid #334155',
                padding: '10px 16px',
                borderRadius: '8px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Acknowledge Only
            </button>
          </div>
        </div>
      )}

      {/* Action Feedback Banner */}
      {feedback && (
        <div
          style={{
            backgroundColor: feedback.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : feedback.type === 'info' ? 'rgba(2, 132, 199, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            border: `1px solid ${feedback.type === 'success' ? '#10b981' : feedback.type === 'info' ? '#38bdf8' : '#ef4444'}`,
            color: feedback.type === 'success' ? '#34d399' : feedback.type === 'info' ? '#38bdf8' : '#f87171',
            borderRadius: '8px',
            padding: '10px 14px',
            marginBottom: '14px',
            fontSize: '12px',
          }}
        >
          {feedback.text}
        </div>
      )}

      {/* Simulator Test Bar & Incident Log Drawer Toggle */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#0c1424',
          border: '1px solid #1e2d45',
          borderRadius: '10px',
          padding: '10px 16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={16} style={{ color: '#38bdf8' }} />
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc' }}>
            Edge Incident Detection & Authority Dispatch Console
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Simulator buttons for presentation demo */}
          <button
            onClick={handleSimulateEdgeAccident}
            disabled={isSimulating}
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              color: '#f87171',
              padding: '5px 10px',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Zap size={12} /> Simulate Accident Event
          </button>

          <button
            onClick={handleSimulateEdgeAmbulance}
            disabled={isSimulating}
            style={{
              backgroundColor: 'rgba(56, 189, 248, 0.15)',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              color: '#38bdf8',
              padding: '5px 10px',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Ambulance size={12} /> Simulate Ambulance Alert
          </button>

          {/* Toggle Log Drawer */}
          <button
            onClick={() => setShowLogDrawer(!showLogDrawer)}
            style={{
              backgroundColor: '#162238',
              border: '1px solid #233554',
              color: '#94a3b8',
              padding: '5px 10px',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            Incident Audit Log ({events.length}) {showLogDrawer ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
        </div>
      </div>

      {/* Incident Log Drawer Table */}
      {showLogDrawer && (
        <div
          style={{
            backgroundColor: '#070d18',
            border: '1px solid #1e293b',
            borderTop: 'none',
            borderRadius: '0 0 10px 10px',
            padding: '14px',
            maxHeight: '260px',
            overflowY: 'auto',
          }}
        >
          {events.length === 0 ? (
            <div style={{ fontSize: '12px', color: '#64748b', textAlign: 'center', padding: '10px' }}>
              No safety events recorded in audit log.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {events.map((evt) => (
                <div
                  key={evt.event_id}
                  style={{
                    backgroundColor: '#0c1424',
                    border: '1px solid #1e2d45',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '12px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span
                      style={{
                        backgroundColor: evt.event_type === 'accident_suspected' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                        color: evt.event_type === 'accident_suspected' ? '#ef4444' : '#38bdf8',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: 700,
                      }}
                    >
                      {evt.event_type.toUpperCase().replace(/_/g, ' ')}
                    </span>
                    <span style={{ color: '#f8fafc', fontWeight: 600 }}>
                      {evt.junction_id}
                    </span>
                    <span style={{ color: '#94a3b8' }}>
                      Nearest: {evt.nearest_authorities?.primary?.station_name?.split('&')[0]} ({evt.nearest_authorities?.primary?.estimated_arrival_minutes}m)
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {evt.acknowledged ? (
                      <span style={{ color: '#34d399', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <CheckCircle2 size={13} /> Dispatched by {evt.acknowledged_by}
                      </span>
                    ) : (
                      <button
                        onClick={() => handleAcknowledgeAndDispatch(evt.event_id, 'DISPATCH_FROM_LOG')}
                        style={{
                          backgroundColor: '#0284c7',
                          color: '#ffffff',
                          border: 'none',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: 700,
                          cursor: 'pointer',
                        }}
                      >
                        1-Click Dispatch
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
