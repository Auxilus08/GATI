import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
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
  Building,
  Hospital,
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
  const [feedback, setFeedback] = useState(null);

  const loadEvents = async () => {
    try {
      const res = await fetchSafetyEvents(null, 15);
      if (res?.events) {
        setEvents(res.events);
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
        notes: `Emergency response dispatched via 1-Click ICCC console for ${activeAlert?.junction_id || junctionId}`,
      });

      setFeedback({
        type: 'success',
        text: `DISPATCH CONFIRMED: Nearest units notified. Audit log permanently stamped (Operator: ICCC_OPERATOR_CHIEF_MH31).`,
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
    <div
      className="card"
      style={{
        padding: '14px 16px',
        marginBottom: 0,
        backgroundColor: '#0a101d',
        border: activeAlert ? '1.5px solid #ef4444' : '1px solid #1e293b',
        borderRadius: '12px',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        boxShadow: activeAlert ? '0 0 20px rgba(239, 68, 68, 0.25)' : 'none',
        transition: 'all 0.3s ease',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldAlert size={16} style={{ color: activeAlert ? '#ef4444' : '#38bdf8' }} />
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc' }}>
            Incident & Nearest Authority Dispatch
          </span>
          <span
            style={{
              backgroundColor: 'rgba(56, 189, 248, 0.15)',
              color: '#38bdf8',
              fontSize: '10px',
              fontWeight: 700,
              padding: '1px 6px',
              borderRadius: '4px',
            }}
          >
            AUTO-DISPATCH
          </span>
        </div>

        {/* Quick Simulation Triggers for Presentation Demo */}
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={handleSimulateEdgeAccident}
            disabled={isSimulating}
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.18)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              color: '#fca5a5',
              padding: '3px 8px',
              borderRadius: '5px',
              fontSize: '10px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
            }}
          >
            <Zap size={11} /> ⚡ Accident
          </button>
          <button
            onClick={handleSimulateEdgeAmbulance}
            disabled={isSimulating}
            style={{
              backgroundColor: 'rgba(56, 189, 248, 0.18)',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              color: '#38bdf8',
              padding: '3px 8px',
              borderRadius: '5px',
              fontSize: '10px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
            }}
          >
            <Ambulance size={11} /> 🚑 Ambulance
          </button>
        </div>
      </div>

      {/* Action Feedback Banner */}
      {feedback && (
        <div
          style={{
            backgroundColor: feedback.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(2, 132, 199, 0.15)',
            border: `1px solid ${feedback.type === 'success' ? '#10b981' : '#38bdf8'}`,
            color: feedback.type === 'success' ? '#34d399' : '#38bdf8',
            borderRadius: '6px',
            padding: '6px 10px',
            marginBottom: '8px',
            fontSize: '11px',
          }}
        >
          {feedback.text}
        </div>
      )}

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: '160px', overflowY: 'auto' }}>
        {activeAlert ? (
          /* Active Emergency Pop-Up Alert */
          <div
            style={{
              backgroundColor: '#111928',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              borderRadius: '8px',
              padding: '12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span
                  style={{
                    backgroundColor: activeAlert.event_type === 'accident_suspected' ? '#ef4444' : '#0284c7',
                    color: '#ffffff',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: '10px',
                    fontWeight: 800,
                  }}
                >
                  {activeAlert.event_type === 'accident_suspected' ? '🚨 ACCIDENT DETECTED' : '🚑 AMBULANCE DETECTED'}
                </span>
                <span style={{ fontSize: '11px', color: '#f8fafc', fontWeight: 700 }}>
                  {activeAlert.junction_id} ({(activeAlert.confidence * 100).toFixed(0)}% Conf)
                </span>
              </div>

              <button
                onClick={() => setActiveAlert(null)}
                style={{
                  backgroundColor: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  fontSize: '11px',
                  cursor: 'pointer',
                }}
              >
                Dismiss
              </button>
            </div>

            {/* Nearest Authority Info */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px' }}>
              {primaryAuth && (
                <div style={{ backgroundColor: '#070d18', padding: '6px 8px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                  <div style={{ color: '#38bdf8', fontWeight: 700 }}>🚔 Nearest Police:</div>
                  <div style={{ color: '#f8fafc', fontWeight: 600 }}>{primaryAuth.station_name.split('&')[0]}</div>
                  <div style={{ color: '#94a3b8', fontSize: '10px' }}>
                    {primaryAuth.distance_km} km ({primaryAuth.estimated_arrival_minutes} min ETA)
                  </div>
                </div>
              )}

              {medicalAuth && (
                <div style={{ backgroundColor: '#070d18', padding: '6px 8px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                  <div style={{ color: '#34d399', fontWeight: 700 }}>🚑 Nearest Hospital:</div>
                  <div style={{ color: '#f8fafc', fontWeight: 600 }}>{medicalAuth.station_name.split('(')[0]}</div>
                  <div style={{ color: '#94a3b8', fontSize: '10px' }}>
                    {medicalAuth.distance_km} km ({medicalAuth.estimated_arrival_minutes} min ETA)
                  </div>
                </div>
              )}
            </div>

            {/* 1-Click Action */}
            <button
              onClick={() => handleAcknowledgeAndDispatch(activeAlert.event_id, 'DISPATCH_NEAREST_PATROL_AND_AMBULANCE')}
              disabled={isDispatching}
              style={{
                backgroundColor: '#059669',
                color: '#ffffff',
                border: 'none',
                padding: '8px 12px',
                borderRadius: '6px',
                fontSize: '11.5px',
                fontWeight: 800,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                boxShadow: '0 0 10px rgba(16, 185, 129, 0.4)',
              }}
            >
              <PhoneCall size={13} /> 1-CLICK DISPATCH NEAREST UNITS
            </button>
          </div>
        ) : (
          /* Incident Log List (When no popup is active) */
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {events.length === 0 ? (
              <div style={{ fontSize: '11px', color: '#64748b', textAlign: 'center', padding: '24px 0' }}>
                <CheckCircle2 size={18} style={{ color: '#34d399', margin: '0 auto 4px auto' }} />
                <span>All intersections normal • Zero active emergency incidents.</span>
              </div>
            ) : (
              events.slice(0, 3).map((evt) => (
                <div
                  key={evt.event_id}
                  style={{
                    backgroundColor: '#070d18',
                    border: '1px solid #1e293b',
                    borderRadius: '6px',
                    padding: '6px 10px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '11px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span
                      style={{
                        backgroundColor: evt.event_type === 'accident_suspected' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                        color: evt.event_type === 'accident_suspected' ? '#ef4444' : '#38bdf8',
                        padding: '1px 5px',
                        borderRadius: '3px',
                        fontSize: '9px',
                        fontWeight: 700,
                      }}
                    >
                      {evt.event_type.toUpperCase().replace(/_/g, ' ')}
                    </span>
                    <span style={{ color: '#f8fafc', fontWeight: 600 }}>{evt.junction_id}</span>
                    <span style={{ color: '#64748b', fontSize: '10px' }}>
                      ({evt.nearest_authorities?.primary?.station_name?.split(' ')[0]} {evt.nearest_authorities?.primary?.estimated_arrival_minutes}m)
                    </span>
                  </div>

                  <div>
                    {evt.acknowledged ? (
                      <span style={{ color: '#34d399', fontSize: '10px', display: 'flex', alignItems: 'center', gap: '3px' }}>
                        <CheckCircle2 size={11} /> Dispatched
                      </span>
                    ) : (
                      <button
                        onClick={() => handleAcknowledgeAndDispatch(evt.event_id, 'DISPATCH_FROM_LOG')}
                        style={{
                          backgroundColor: '#0284c7',
                          color: '#ffffff',
                          border: 'none',
                          padding: '2px 6px',
                          borderRadius: '3px',
                          fontSize: '10px',
                          fontWeight: 700,
                          cursor: 'pointer',
                        }}
                      >
                        Dispatch
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
