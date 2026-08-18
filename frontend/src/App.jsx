import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import CityTrafficMap from './components/CityTrafficMap';
import SafetyAlertToastAndPanel from './components/SafetyAlertToastAndPanel';
import LiveJunctionView from './components/LiveJunctionView';
import CommandView from './components/CommandView';
import PredictiveRiskView from './components/PredictiveRiskView';
import {
  fetchJunctionsList,
  fetchJunctionDetail,
  fetchSignalTiming,
  fetchComparison,
  fetchLatestTelemetry,
  createTelemetryWebSocket,
  createAlertsWebSocket,
} from './services/api';

const DEFAULT_JUNCTIONS = [
  { junction_id: 'NGP_J01_SITABULDI', name: 'Sitabuldi Interchange' },
  { junction_id: 'NGP_J02_VARIETIES_SQ', name: 'Varieties Square' },
  { junction_id: 'NGP_J03_RAHATE_COLONY', name: 'Rahate Colony Square' },
  { junction_id: 'NGP_J04_AJNI_SQ', name: 'Ajni Square' },
  { junction_id: 'NGP_J05_CHHATRAPATI_SQ', name: 'Chhatrapati Square' },
];

const DEFAULT_DETAIL = {
  junction_id: 'NGP_J01_SITABULDI',
  name: 'Sitabuldi Interchange',
  corridor_id: 'CORR_WARDHA_RD',
  approaches: [
    { id: 'APP_NORTH', name: 'Wardha Road (from RBI Square)', direction: 'Northbound', lanes: 3 },
    { id: 'APP_SOUTH', name: 'Wardha Road (towards Rahate Colony)', direction: 'Southbound', lanes: 3 },
    { id: 'APP_EAST', name: 'Central Avenue (from Railway Station)', direction: 'Eastbound', lanes: 2 },
    { id: 'APP_WEST', name: 'Maharajbagh Road', direction: 'Westbound', lanes: 2 },
  ],
  phases: [
    { phase_id: 1, name: 'Wardha Road North-South Through', active_approaches: ['APP_NORTH', 'APP_SOUTH'] },
    { phase_id: 2, name: 'Central Avenue - Maharajbagh East-West', active_approaches: ['APP_EAST', 'APP_WEST'] },
    { phase_id: 3, name: 'Sitabuldi Right Turn Phasing', active_approaches: ['APP_NORTH', 'APP_EAST'] },
  ],
};

const DEFAULT_TIMING = {
  junction_id: 'NGP_J01_SITABULDI',
  current: { phase_id: 1, elapsed_green_sec: 18.0, signal_state: 'GREEN' },
  recommended: {
    recommended_phase_id: 1,
    current_phase_id: 1,
    decision_reason: 'MAX_PRESSURE_HOLD',
    elapsed_green_sec: 18.0,
    pressures: { 1: 18.4, 2: 7.2, 3: 4.1 },
  },
  override_active: false,
};

const DEFAULT_COMPARISON = {
  junction_id: 'NGP_J01_SITABULDI',
  fixed_avg_wait_sec: 42.5,
  mp_avg_wait_sec: 29.4,
  wait_time_reduction_pct: 30.8,
  fixed_peak_queue_m: 112.0,
  mp_peak_queue_m: 68.0,
  queue_reduction_pct: 31.9,
  estimated_fuel_saved_liters: 0.96,
  co2_reduction_kg: 2.22,
};

export default function App() {
  const [activeTab, setActiveTab] = useState('live'); // 'live' | 'command' | 'predictive'
  const [junctions, setJunctions] = useState(DEFAULT_JUNCTIONS);
  const [selectedJunctionId, setSelectedJunctionId] = useState('NGP_J01_SITABULDI');
  const [junctionDetail, setJunctionDetail] = useState(DEFAULT_DETAIL);
  const [telemetry, setTelemetry] = useState(null);
  const [signalTiming, setSignalTiming] = useState(DEFAULT_TIMING);
  const [comparisonData, setComparisonData] = useState(DEFAULT_COMPARISON);
  const [isConnected, setIsConnected] = useState(false);
  const handleJunctionSelect = useCallback((junctionId) => {
    setSelectedJunctionId(junctionId);
  }, []);

  // 1. Load available junctions on mount
  useEffect(() => {
    fetchJunctionsList()
      .then((list) => {
        if (list && list.length > 0) {
          setJunctions(list);
          setIsConnected(true);
        }
      })
      .catch((err) => {
        console.warn('Backend API connecting in background...', err);
      });
  }, []);

  // 2. Load detail, signal timing, and telemetry for the selected junction
  const loadJunctionData = useCallback(async (jid) => {
    if (!jid) return;
    try {
      const [detailRes, timingRes, allTelRes, compRes] = await Promise.all([
        fetchJunctionDetail(jid).catch(() => null),
        fetchSignalTiming(jid).catch(() => null),
        fetchLatestTelemetry().catch(() => ({})),
        fetchComparison(jid).catch(() => null),
      ]);

      if (detailRes?.config) setJunctionDetail(detailRes.config);
      if (timingRes) setSignalTiming(timingRes);
      if (allTelRes && allTelRes[jid]) setTelemetry(allTelRes[jid]);
      if (compRes) setComparisonData(compRes);
      setIsConnected(true);
    } catch (e) {
      console.warn('Refreshing junction data...', e);
    }
  }, []);

  useEffect(() => {
    loadJunctionData(selectedJunctionId);
  }, [selectedJunctionId, loadJunctionData]);

  // 3. Setup WebSocket streams for real-time live push & fallback polling
  useEffect(() => {
    // Connect to global or per-junction telemetry stream
    const wsClient = createTelemetryWebSocket((msg) => {
      setIsConnected(true);
      if (msg.type === 'TELEMETRY_UPDATE' && msg.junction_id === selectedJunctionId) {
        setTelemetry((prev) => ({
          ...prev,
          timestamp: msg.timestamp,
          signal: msg.signal,
          approaches: msg.approaches,
          risk: msg.risk,
          analytics: msg.analytics,
          emergency_active: msg.emergency_active,
        }));
        if (msg.signal) {
          setSignalTiming((prev) => ({
            ...prev,
            recommended: {
              ...prev?.recommended,
              phase_id: msg.signal.recommended_phase_id,
              decision_reason: msg.signal.decision_reason,
              elapsed_green_sec: msg.signal.elapsed_green_sec,
              pressures: msg.signal.pressures,
            },
            current: {
              ...prev?.current,
              phase_id: msg.signal.current_phase_id,
            },
            override_active: msg.signal.override_active,
          }));
        }
      }
    }, selectedJunctionId);

    // Fallback polling every 3 seconds to guarantee freshness
    const pollInterval = setInterval(() => {
      loadJunctionData(selectedJunctionId);
    }, 3000);

    return () => {
      wsClient.close();
      clearInterval(pollInterval);
    };
  }, [selectedJunctionId, loadJunctionData]);

  return (
    <div className="app-container">
      {/* Top Navigation Bar with 3-Panel Tabs & Dynamic Junction Switcher */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        junctions={junctions}
        selectedJunctionId={selectedJunctionId}
        onSelectJunction={handleJunctionSelect}
        isConnected={isConnected}
      />

      {/* Main Work Area with City Traffic Map and Panels */}
      <main className="main-content">
        {/* Top 2-Column Row: Real City Traffic Map (Left) + Edge Incident & Authority Dispatch Console (Right) */}
        <div className="dashboard-overview">
          <CityTrafficMap
            junctions={junctions}
            selectedJunctionId={selectedJunctionId}
            onSelectJunction={handleJunctionSelect}
          />

          <SafetyAlertToastAndPanel
            junctionId={selectedJunctionId}
            onEventAction={() => loadJunctionData(selectedJunctionId)}
          />
        </div>

        {/* Panel 1: Live Junction View */}
        {activeTab === 'live' && (
          <LiveJunctionView
            junction={junctionDetail}
            telemetry={telemetry}
            signalTiming={signalTiming}
          />
        )}

        {/* Panel 2: Command View */}
        {activeTab === 'command' && (
          <CommandView
            junction={junctionDetail}
            telemetry={telemetry}
            signalTiming={signalTiming}
            comparisonData={comparisonData}
            onRefresh={() => loadJunctionData(selectedJunctionId)}
          />
        )}

        {/* Panel 3: Predictive / Risk View */}
        {activeTab === 'predictive' && (
          <PredictiveRiskView
            junction={junctionDetail}
          />
        )}
      </main>
    </div>
  );
}
