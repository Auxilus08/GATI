import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Zap,
  Activity,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Navigation,
  Clock,
  Radio,
  Flame,
  Hospital,
} from 'lucide-react';
import {
  dispatchEmergencyCorridor,
  fetchActiveEmergencies,
  clearEmergencyCorridor,
} from '../services/api';

export default function EmergencyCorridorConsole({ onEmergencyTriggered }) {
  const [activeEmergencies, setActiveEmergencies] = useState([]);
  const [isDispatching, setIsDispatching] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState(null);

  // Poll active emergencies
  const loadActiveEmergencies = async () => {
    try {
      const res = await fetchActiveEmergencies();
      if (res?.active_corridors) {
        setActiveEmergencies(res.active_corridors);
      }
    } catch (e) {
      console.warn('Checking active emergency corridors...', e);
    }
  };

  useEffect(() => {
    loadActiveEmergencies();
    const interval = setInterval(loadActiveEmergencies, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleDispatch = async (routeKey, vehicleType, callSign) => {
    setIsDispatching(true);
    setFeedbackMessage(null);
    try {
      const res = await dispatchEmergencyCorridor({
        route_key: routeKey,
        call_sign: callSign,
        vehicle_type: vehicleType,
        dispatched_by: 'EMERGENCY_ICCC_OPERATOR_108',
        target_speed_kmh: vehicleType === 'AMBULANCE' ? 55.0 : 50.0,
      });

      setFeedbackMessage({
        type: 'success',
        text: `🚨 ${vehicleType === 'AMBULANCE' ? '108 AMBULANCE' : 'FIRE BRIGADE'} GREEN CORRIDOR ENGAGED! Signals forced GREEN across 5 Wardha Road junctions.`,
      });

      await loadActiveEmergencies();
      if (onEmergencyTriggered) onEmergencyTriggered();
    } catch (err) {
      setFeedbackMessage({
        type: 'error',
        text: err.message || 'Failed to dispatch emergency green corridor',
      });
    } finally {
      setIsDispatching(false);
    }
  };

  const handleClear = async (dispatchId) => {
    try {
      await clearEmergencyCorridor(dispatchId);
      setFeedbackMessage({
        type: 'info',
        text: '✅ Emergency Corridor Completed. Reverted signals back to Smart Adaptive Max-Pressure.',
      });
      await loadActiveEmergencies();
      if (onEmergencyTriggered) onEmergencyTriggered();
    } catch (err) {
      setFeedbackMessage({
        type: 'error',
        text: err.message || 'Failed to clear emergency corridor',
      });
    }
  };

  const hasActive = activeEmergencies.length > 0;
  const activeDispatch = activeEmergencies[0];

  return (
    <div
      className="card"
      style={{
        backgroundColor: '#0c1424',
        border: hasActive ? '1.5px solid #ef4444' : '1px solid #1e2d45',
        borderRadius: '14px',
        padding: '20px 24px',
        marginBottom: '24px',
        boxShadow: hasActive ? '0 0 24px rgba(239, 68, 68, 0.3)' : '0 8px 32px rgba(0, 0, 0, 0.45)',
        transition: 'all 0.3s ease',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              backgroundColor: hasActive ? '#ef4444' : 'rgba(239, 68, 68, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: hasActive ? '#ffffff' : '#ef4444',
              animation: hasActive ? 'pulse 1s infinite alternate' : 'none',
            }}
          >
            <ShieldAlert size={18} />
          </div>
          <div>
            <h2 style={{ fontSize: '17px', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
              Emergency Vehicle Preemption (EVP) & Green Corridors
            </h2>
            <p style={{ fontSize: '12px', color: '#94a3b8', margin: '2px 0 0 0' }}>
              Sub-6s automatic green corridor clearance for Ambulances and Fire Brigades with IRC SP:41 safety interlocks.
            </p>
          </div>
        </div>

        {/* Live Status Badge */}
        <div>
          {hasActive ? (
            <span
              style={{
                backgroundColor: '#ef4444',
                color: '#ffffff',
                padding: '6px 14px',
                borderRadius: '20px',
                fontSize: '12px',
                fontWeight: 800,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                boxShadow: '0 0 14px rgba(239, 68, 68, 0.6)',
              }}
            >
              <span className="pulse-dot" style={{ backgroundColor: '#ffffff' }} />
              🚨 GREEN CORRIDOR ACTIVE
            </span>
          ) : (
            <span
              style={{
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                color: '#34d399',
                border: '1px solid rgba(52, 211, 153, 0.3)',
                padding: '5px 12px',
                borderRadius: '20px',
                fontSize: '11px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <CheckCircle2 size={13} />
              STANDBY • READY TO DISPATCH
            </span>
          )}
        </div>
      </div>

      {/* 1-Tap Emergency Dispatch Triggers */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '16px' }}>
        {/* Ambulance Dispatch Button */}
        <button
          onClick={() => handleDispatch('AMBULANCE_AIIMS_CORRIDOR', 'AMBULANCE', '108_AMBULANCE_MH31_9021')}
          disabled={isDispatching}
          style={{
            backgroundColor: '#131d2e',
            border: '1.5px solid #0284c7',
            borderRadius: '10px',
            padding: '14px 18px',
            cursor: 'pointer',
            textAlign: 'left',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#162844')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#131d2e')}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '8px',
                backgroundColor: 'rgba(2, 132, 199, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#38bdf8',
              }}
            >
              <Hospital size={22} />
            </div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc' }}>
                🚑 Dispatch 108 Medical Ambulance
              </div>
              <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                Sitabuldi ➔ Rahate (GMCH) ➔ AIIMS Nagpur (55 km/h)
              </div>
            </div>
          </div>
          <span
            style={{
              backgroundColor: '#0284c7',
              color: '#ffffff',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 700,
            }}
          >
            ACTIVATE
          </span>
        </button>

        {/* Fire Brigade Dispatch Button */}
        <button
          onClick={() => handleDispatch('FIRE_SITABULDI_MARKET', 'FIRE_BRIGADE', 'NMC_FIRE_ENGINE_04')}
          disabled={isDispatching}
          style={{
            backgroundColor: '#131d2e',
            border: '1.5px solid #ea580c',
            borderRadius: '10px',
            padding: '14px 18px',
            cursor: 'pointer',
            textAlign: 'left',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            transition: 'all 0.2s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#291b15')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#131d2e')}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '8px',
                backgroundColor: 'rgba(234, 88, 12, 0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fb923c',
              }}
            >
              <Flame size={22} />
            </div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc' }}>
                🚒 Dispatch Fire & Rescue Brigade
              </div>
              <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                Central Station ➔ Sitabuldi Commercial Market (50 km/h)
              </div>
            </div>
          </div>
          <span
            style={{
              backgroundColor: '#ea580c',
              color: '#ffffff',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '11px',
              fontWeight: 700,
            }}
          >
            ACTIVATE
          </span>
        </button>
      </div>

      {/* Active Corridor Live HUD Banner (When engaged) */}
      {hasActive && activeDispatch && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '10px',
            padding: '14px 18px',
            marginBottom: '14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Radio size={16} className="text-red" style={{ animation: 'pulse 1s infinite' }} />
              <div>
                <span style={{ fontSize: '13px', fontWeight: 700, color: '#fca5a5' }}>
                  ACTIVE VEHICLE: {activeDispatch.call_sign} ({activeDispatch.vehicle_type})
                </span>
                <div style={{ fontSize: '11px', color: '#cbd5e1' }}>
                  Route: {activeDispatch.corridor_name} ➔ {activeDispatch.destination}
                </div>
              </div>
            </div>

            <button
              onClick={() => handleClear(activeDispatch.dispatch_id)}
              style={{
                backgroundColor: '#ef4444',
                color: '#ffffff',
                border: 'none',
                padding: '6px 14px',
                borderRadius: '6px',
                fontSize: '11px',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <RotateCcw size={12} /> CLEAR CORRIDOR & REVERT SIGNALS
            </button>
          </div>

          {/* 5-Junction Sequential Preemption Wave Indicator */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              gap: '8px',
              backgroundColor: '#070d18',
              padding: '10px',
              borderRadius: '8px',
            }}
          >
            {['Sitabuldi', 'Varieties Sq', 'Rahate GMCH', 'Ajni Sq', 'Chhatrapati AIIMS'].map((jName, idx) => (
              <div
                key={jName}
                style={{
                  backgroundColor: 'rgba(16, 185, 129, 0.15)',
                  border: '1px solid #10b981',
                  borderRadius: '6px',
                  padding: '8px',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: '11px', fontWeight: 700, color: '#34d399' }}>
                  🟢 GREEN Wave
                </div>
                <div style={{ fontSize: '10px', color: '#f8fafc', marginTop: '2px' }}>
                  {jName}
                </div>
                <div style={{ fontSize: '9px', color: '#94a3b8', marginTop: '2px' }}>
                  Queue Flushed (0s delay)
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Feedback Message */}
      {feedbackMessage && (
        <div
          style={{
            fontSize: '12px',
            padding: '8px 12px',
            borderRadius: '6px',
            backgroundColor: feedbackMessage.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(2, 132, 199, 0.15)',
            color: feedbackMessage.type === 'success' ? '#34d399' : '#38bdf8',
            border: `1px solid ${feedbackMessage.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(2, 132, 199, 0.3)'}`,
          }}
        >
          {feedbackMessage.text}
        </div>
      )}
    </div>
  );
}
