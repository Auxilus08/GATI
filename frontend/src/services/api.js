/**
 * GATI Dashboard API & WebSocket Service Layer.
 * Direct bridge to FastAPI backend endpoints.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000/api/v1';

/* ─── Junctions & Geometry ─────────────────────────────────────────── */

export async function fetchJunctionsList() {
  const res = await fetch(`${API_BASE_URL}/junctions/`);
  if (!res.ok) throw new Error('Failed to fetch junctions list');
  return res.json();
}

export async function fetchJunctionDetail(junctionId) {
  const res = await fetch(`${API_BASE_URL}/junctions/${junctionId}`);
  if (!res.ok) throw new Error(`Failed to fetch junction ${junctionId} detail`);
  return res.json();
}

export async function fetchJunctionState(junctionId) {
  const res = await fetch(`${API_BASE_URL}/junctions/${junctionId}/state`);
  if (!res.ok) throw new Error(`Failed to fetch live state for ${junctionId}`);
  return res.json();
}

export async function fetchLatestTelemetry() {
  const res = await fetch(`${API_BASE_URL}/telemetry/latest`);
  if (!res.ok) throw new Error('Failed to fetch latest telemetry');
  return res.json();
}

/* ─── Signal Timing & Governance Override ───────────────────────────── */

export async function fetchSignalTiming(junctionId) {
  const res = await fetch(`${API_BASE_URL}/junctions/${junctionId}/signal-timing`);
  if (!res.ok) throw new Error(`Failed to fetch signal timing for ${junctionId}`);
  return res.json();
}

export async function issueOverride(junctionId, { action, phase_id, duration_seconds, reason, operator_id }) {
  const res = await fetch(`${API_BASE_URL}/junctions/${junctionId}/override`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: action || 'LOCK',
      phase_id: phase_id ? Number(phase_id) : undefined,
      duration_seconds: duration_seconds ? Number(duration_seconds) : 60,
      reason: reason || 'Manual traffic police intervention',
      operator_id: operator_id || 'ICCC_OPERATOR_01',
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to issue override');
  }
  return res.json();
}

export async function fetchOverrideStatus(junctionId) {
  const res = await fetch(`${API_BASE_URL}/junctions/${junctionId}/override/status`);
  if (!res.ok) throw new Error(`Failed to fetch override status for ${junctionId}`);
  return res.json();
}

export async function fetchOverrideAudit(junctionId, limit = 20) {
  const res = await fetch(`${API_BASE_URL}/junctions/${junctionId}/override/audit?limit=${limit}`);
  if (!res.ok) throw new Error(`Failed to fetch override audit for ${junctionId}`);
  return res.json();
}

/* ─── Analytics, Forecasting & Risk ─────────────────────────────────── */

export async function fetchCitySummary() {
  const res = await fetch(`${API_BASE_URL}/analytics/city-summary`);
  if (!res.ok) throw new Error('Failed to fetch city summary');
  return res.json();
}

export async function fetchForecast(junctionId) {
  const res = await fetch(`${API_BASE_URL}/analytics/${junctionId}/forecast`);
  if (!res.ok) throw new Error(`Failed to fetch forecast for ${junctionId}`);
  return res.json();
}

export async function fetchIncidents(junctionId) {
  const res = await fetch(`${API_BASE_URL}/analytics/${junctionId}/incidents`);
  if (!res.ok) throw new Error(`Failed to fetch incidents for ${junctionId}`);
  return res.json();
}

export async function fetchLiveRisk(junctionId) {
  const res = await fetch(`${API_BASE_URL}/analytics/${junctionId}/risk`);
  if (!res.ok) throw new Error(`Failed to fetch risk metrics for ${junctionId}`);
  return res.json();
}

export async function fetchComparison(junctionId) {
  const res = await fetch(`${API_BASE_URL}/analytics/${junctionId}/comparison`);
  if (!res.ok) throw new Error(`Failed to fetch performance comparison for ${junctionId}`);
  return res.json();
}

/* ─── Corridors ─────────────────────────────────────────────────────── */

export async function fetchCorridors() {
  const res = await fetch(`${API_BASE_URL}/corridors/`);
  if (!res.ok) throw new Error('Failed to fetch corridors');
  return res.json();
}

/* ─── WebSocket Streams ─────────────────────────────────────────────── */

export function createTelemetryWebSocket(onMessage, junctionId = null) {
  const url = junctionId
    ? `${WS_BASE_URL}/telemetry/ws/${junctionId}`
    : `${WS_BASE_URL}/telemetry/ws`;

  let ws = null;
  let retryTimer = null;
  let isClosed = false;

  const connect = () => {
    try {
      ws = new WebSocket(url);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (e) {
          console.error('[WS Parse Error]', e);
        }
      };
      ws.onerror = (err) => {
        console.warn('[WS Error]', err);
      };
      ws.onclose = () => {
        if (!isClosed) {
          retryTimer = setTimeout(connect, 3000);
        }
      };
    } catch (err) {
      console.warn('[WS Connection Error]', err);
      retryTimer = setTimeout(connect, 3000);
    }
  };

  connect();

  return {
    close: () => {
      isClosed = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (ws) ws.close();
    },
  };
}

export function createAlertsWebSocket(onAlert) {
  const url = `${WS_BASE_URL}/analytics/ws/alerts`;
  let ws = null;
  let retryTimer = null;
  let isClosed = false;

  const connect = () => {
    try {
      ws = new WebSocket(url);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onAlert(data);
        } catch (e) {
          console.error('[WS Alerts Parse Error]', e);
        }
      };
      ws.onclose = () => {
        if (!isClosed) {
          retryTimer = setTimeout(connect, 4000);
        }
      };
    } catch (err) {
      retryTimer = setTimeout(connect, 4000);
    }
  };

  connect();

  return {
    close: () => {
      isClosed = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (ws) ws.close();
    },
  };
}

/* ─── Governance, Field Mobile & VIP Corridors ─────────────────────── */

export async function executeFieldQuickAction({
  junction_id,
  action_type = 'FLUSH_HEAVY_QUEUE',
  officer_badge_id = 'CONSTABLE_MH31_8821',
  target_phase_id = 1,
  duration_seconds = 45,
}) {
  const res = await fetch(`${API_BASE_URL}/field/quick-action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      junction_id,
      action_type,
      officer_badge_id,
      target_phase_id: Number(target_phase_id),
      duration_seconds: Number(duration_seconds),
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to execute field action');
  }
  return res.json();
}

