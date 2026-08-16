/**
 * API service layer for communicating with the GATI FastAPI central backend.
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

export async function fetchCitySummary() {
  const res = await fetch(`${API_BASE_URL}/analytics/city-summary`);
  if (!res.ok) throw new Error('Failed to fetch city summary');
  return res.json();
}

export async function fetchJunctionsList() {
  const res = await fetch(`${API_BASE_URL}/junctions/`);
  if (!res.ok) throw new Error('Failed to fetch junctions');
  return res.json();
}

export async function fetchLatestTelemetry() {
  const res = await fetch(`${API_BASE_URL}/telemetry/latest`);
  if (!res.ok) throw new Error('Failed to fetch latest telemetry');
  return res.json();
}

export async function fetchCorridors() {
  const res = await fetch(`${API_BASE_URL}/corridors/`);
  if (!res.ok) throw new Error('Failed to fetch corridors');
  return res.json();
}

export async function submitEmergencyOverride(overrideData) {
  const res = await fetch(`${API_BASE_URL}/junctions/override/emergency`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(overrideData),
  });
  if (!res.ok) throw new Error('Failed to issue override');
  return res.json();
}

export async function planGreenWave(planData) {
  const res = await fetch(`${API_BASE_URL}/corridors/green-wave/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(planData),
  });
  if (!res.ok) throw new Error('Failed to compute green wave');
  return res.json();
}
