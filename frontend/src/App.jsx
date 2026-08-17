import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
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

export default function App() {
  const [activeTab, setActiveTab] = useState('live'); // 'live' | 'command' | 'predictive'
  const [junctions, setJunctions] = useState([]);
  const [selectedJunctionId, setSelectedJunctionId] = useState('NGP_J01_SITABULDI');
  const [junctionDetail, setJunctionDetail] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [signalTiming, setSignalTiming] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  // 1. Load available junctions on mount
  useEffect(() => {
    fetchJunctionsList()
      .then((list) => {
        if (list && list.length > 0) {
          setJunctions(list);
          setSelectedJunctionId(list[0].junction_id);
        }
      })
      .catch((err) => console.warn('Failed to load junctions list', err));
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
      console.error('Error fetching junction data', e);
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
        onSelectJunction={(jid) => setSelectedJunctionId(jid)}
        isConnected={isConnected}
      />

      {/* Main 3-Panel Work Area */}
      <main className="main-content">
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
