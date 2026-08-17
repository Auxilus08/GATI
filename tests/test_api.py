"""
Integration Tests for GATI Central API.

Uses FastAPI's TestClient (synchronous HTTPX wrapper) to test:
- Root / health endpoints
- Telemetry ingestion → state update
- Junction list, state, signal-timing
- Override LOCK → status → RELEASE → audit
- Analytics: city-summary, forecast, incidents, risk, comparison
- Multi-junction: second junction works by data alone (no code change)
"""

import json
import sys
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from central.api.main import app

client = TestClient(app, raise_server_exceptions=True)

# ─── Shared fixture payloads ───────────────────────────────────────────────

JUNCTION_1 = "NGP_J01_SITABULDI"
JUNCTION_2 = "NGP_J02_VARIETIES_SQ"  # Second junction — no code change needed

def _make_telemetry(junction_id: str, pcu_north: float = 12.0, pcu_south: float = 8.0) -> dict:
    return {
        "junction_id": junction_id,
        "timestamp": time.time(),
        "active_phase_id": 1,
        "signal_state": "GREEN",
        "pressures": {1: pcu_north, 2: pcu_south},
        "approaches": {
            "APP_NORTH": {
                "total_pcu": pcu_north,
                "vehicle_counts": {"car": 5, "two_wheeler": 8, "auto_rickshaw": 2},
                "queue_length_m": pcu_north * 6.0,
                "avg_speed_kmh": 22.0,
                "emergency": False,
            },
            "APP_SOUTH": {
                "total_pcu": pcu_south,
                "vehicle_counts": {"car": 3, "two_wheeler": 5},
                "queue_length_m": pcu_south * 6.0,
                "avg_speed_kmh": 28.0,
                "emergency": False,
            },
        },
        "emergency_active": False,
        "elapsed_green_sec": 10.0,
    }


# ─── Tests ─────────────────────────────────────────────────────────────────

class TestMetaEndpoints(unittest.TestCase):
    def test_root(self):
        r = client.get("/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["platform"], "GATI")
        self.assertIn("configured_junctions", data)
        self.assertIn("active_junctions", data)

    def test_health(self):
        r = client.get("/health")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("uptime_sec", data)

    def test_api_health(self):
        r = client.get("/api/v1/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")


class TestTelemetryIngestion(unittest.TestCase):
    def test_single_report_ingestion(self):
        payload = _make_telemetry(JUNCTION_1, pcu_north=15.0, pcu_south=9.0)
        r = client.post("/api/v1/telemetry/report", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["junction_id"], JUNCTION_1)
        self.assertIn("risk", data)
        self.assertIn("recommended_phase", data)

    def test_state_updated_after_report(self):
        payload = _make_telemetry(JUNCTION_1, pcu_north=20.0)
        client.post("/api/v1/telemetry/report", json=payload)
        r = client.get(f"/api/v1/telemetry/latest/{JUNCTION_1}")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["junction_id"], JUNCTION_1)
        self.assertIn("APP_NORTH", data["approaches"])
        self.assertAlmostEqual(data["approaches"]["APP_NORTH"]["total_pcu"], 20.0, places=1)

    def test_batch_ingestion(self):
        reports = [
            _make_telemetry(JUNCTION_1, pcu_north=10.0 + i)
            for i in range(3)
        ]
        r = client.post("/api/v1/telemetry/batch", json=reports)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["processed"], 3)

    def test_all_latest(self):
        client.post("/api/v1/telemetry/report", json=_make_telemetry(JUNCTION_1))
        r = client.get("/api/v1/telemetry/latest")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn(JUNCTION_1, data)


class TestMultiJunctionExtensibility(unittest.TestCase):
    """
    Proof point: second junction works with data alone — no code change.
    JUNCTION_2 has no YAML (uses auto-generated stub), which proves
    the store handles unknown junctions gracefully.
    """
    def test_second_junction_ingested_without_code_change(self):
        payload = _make_telemetry(JUNCTION_2, pcu_north=6.0, pcu_south=4.0)
        r = client.post("/api/v1/telemetry/report", json=payload)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["junction_id"], JUNCTION_2)

    def test_both_junctions_in_latest(self):
        client.post("/api/v1/telemetry/report", json=_make_telemetry(JUNCTION_1))
        client.post("/api/v1/telemetry/report", json=_make_telemetry(JUNCTION_2))
        r = client.get("/api/v1/telemetry/latest")
        data = r.json()
        self.assertIn(JUNCTION_1, data)
        self.assertIn(JUNCTION_2, data)


class TestJunctionEndpoints(unittest.TestCase):
    def setUp(self):
        # Ensure junction has data
        client.post("/api/v1/telemetry/report", json=_make_telemetry(JUNCTION_1))

    def test_list_junctions(self):
        r = client.get("/api/v1/junctions/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsInstance(data, list)
        # At least the two configured Nagpur junctions should appear
        jids = [j["junction_id"] for j in data]
        self.assertIn(JUNCTION_1, jids)

    def test_get_junction_detail(self):
        r = client.get(f"/api/v1/junctions/{JUNCTION_1}")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("config", data)
        self.assertIn("live_state", data)

    def test_get_junction_state(self):
        r = client.get(f"/api/v1/junctions/{JUNCTION_1}/state")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("signal", data)
        self.assertIn("approaches", data)
        self.assertIn("risk_score", data)

    def test_signal_timing(self):
        r = client.get(f"/api/v1/junctions/{JUNCTION_1}/signal-timing")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("current", data)
        self.assertIn("recommended", data)
        self.assertIn("is_switch_recommended", data)

    def test_unknown_junction_returns_404(self):
        r = client.get("/api/v1/junctions/NONEXISTENT_J99/state")
        self.assertEqual(r.status_code, 404)


class TestOverrideEndpoints(unittest.TestCase):
    def setUp(self):
        client.post("/api/v1/telemetry/report", json=_make_telemetry(JUNCTION_1))

    def test_lock_and_status(self):
        lock_payload = {
            "action": "LOCK",
            "phase_id": 2,
            "duration_seconds": 45.0,
            "reason": "Test VIP override",
            "operator_id": "TEST_OPERATOR",
        }
        r = client.post(f"/api/v1/junctions/{JUNCTION_1}/override", json=lock_payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "LOCK_ENGAGED")
        self.assertEqual(data["phase_id"], 2)

        # Check status
        r2 = client.get(f"/api/v1/junctions/{JUNCTION_1}/override/status")
        self.assertEqual(r2.status_code, 200)
        status = r2.json()
        self.assertTrue(status["override_active"])
        self.assertEqual(status["phase_id"], 2)
        self.assertGreater(status["remaining_sec"], 0)

    def test_lock_then_release(self):
        lock_payload = {"action": "LOCK", "phase_id": 1, "duration_seconds": 60.0,
                        "reason": "Test lock", "operator_id": "OP_01"}
        client.post(f"/api/v1/junctions/{JUNCTION_1}/override", json=lock_payload)

        release_payload = {"action": "RELEASE", "reason": "Test release", "operator_id": "OP_01"}
        r = client.post(f"/api/v1/junctions/{JUNCTION_1}/override", json=release_payload)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "OVERRIDE_RELEASED")

        # Status should show no active override
        r2 = client.get(f"/api/v1/junctions/{JUNCTION_1}/override/status")
        self.assertFalse(r2.json()["override_active"])

    def test_audit_trail_populated(self):
        lock_payload = {"action": "LOCK", "phase_id": 3, "duration_seconds": 30.0,
                        "reason": "Audit test", "operator_id": "OP_AUDIT"}
        client.post(f"/api/v1/junctions/{JUNCTION_1}/override", json=lock_payload)
        r = client.get(f"/api/v1/junctions/{JUNCTION_1}/override/audit")
        self.assertEqual(r.status_code, 200)
        audit = r.json()
        self.assertIn("audit_records", audit)
        self.assertGreater(len(audit["audit_records"]), 0)
        last = audit["audit_records"][-1]
        self.assertEqual(last["operator_id"], "OP_AUDIT")
        self.assertEqual(last["action"], "LOCK")

    def test_lock_without_phase_id_returns_422(self):
        r = client.post(f"/api/v1/junctions/{JUNCTION_1}/override",
                        json={"action": "LOCK", "operator_id": "OP"})
        self.assertEqual(r.status_code, 422)


class TestAnalyticsEndpoints(unittest.TestCase):
    def setUp(self):
        # Ingest multiple samples so forecaster has data
        for i in range(6):
            client.post("/api/v1/telemetry/report",
                        json=_make_telemetry(JUNCTION_1, pcu_north=10.0 + i, pcu_south=5.0 + i))

    def test_city_summary(self):
        r = client.get("/api/v1/analytics/city-summary")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("active_junctions", data)
        self.assertIn("total_city_pcu", data)
        self.assertIn("system_health", data)

    def test_forecast(self):
        r = client.get(f"/api/v1/analytics/{JUNCTION_1}/forecast")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("forecasts", data)
        self.assertIn("APP_NORTH", data["forecasts"])
        fc = data["forecasts"]["APP_NORTH"]
        self.assertIn("forecast_10min_pcu", fc)
        self.assertIn("trend_direction", fc)

    def test_incidents(self):
        r = client.get(f"/api/v1/analytics/{JUNCTION_1}/incidents")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("active_incident_count", data)
        self.assertIsInstance(data["active_incidents"], list)

    def test_risk(self):
        r = client.get(f"/api/v1/analytics/{JUNCTION_1}/risk")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("junction_risk_score", data)
        self.assertIn("approach_risks", data)

    def test_comparison(self):
        r = client.get(f"/api/v1/analytics/{JUNCTION_1}/comparison")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        # Should have enough samples now
        self.assertIn("improvement", data)
        self.assertIn("wait_time_reduction_pct", data["improvement"])


class TestCorridorEndpoints(unittest.TestCase):
    def test_list_corridors(self):
        r = client.get("/api/v1/corridors/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsInstance(data, list)

    def test_green_wave_plan(self):
        # Only runs if CORR_WARDHA_RD corridor is configured
        r = client.get("/api/v1/corridors/")
        corridors = r.json()
        if not corridors:
            self.skipTest("No corridors configured")
        corridor_id = corridors[0]["corridor_id"]
        r2 = client.post("/api/v1/corridors/green-wave/plan", json={
            "corridor_id": corridor_id,
            "start_junction_id": corridors[0]["junction_sequence"][0],
            "target_speed_kmh": 35.0,
        })
        self.assertEqual(r2.status_code, 200)
        self.assertIn("junction_offsets_seconds", r2.json())


if __name__ == "__main__":
    unittest.main(verbosity=2)
