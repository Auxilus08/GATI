"""
Unit & Integration Tests for Accident Black-Spot Intelligence & Preventive Interceptions.
"""

import pytest
from fastapi.testclient import TestClient

from central.api.main import app
from central.analytics.blackspot_analyzer import BlackspotAndRiskAnalyzer, blackspot_analyzer


@pytest.fixture
def client():
    return TestClient(app)


def test_blackspot_analyzer_core():
    analyzer = BlackspotAndRiskAnalyzer()
    blackspots = analyzer.get_all_blackspots()
    assert len(blackspots) >= 5

    critical = [b for b in blackspots if b["severity_level"] == "CRITICAL_BLACKSPOT"]
    assert len(critical) >= 2

    # Check Sitabuldi blackspot
    sitabuldi_bs = next(b for b in blackspots if b["junction_id"] == "NGP_J01_SITABULDI")
    assert sitabuldi_bs["risk_score"] > 80.0
    assert sitabuldi_bs["near_miss_count_30d"] > 0
    assert "AUTO_RAMP_METERING_ACTIVE" in sitabuldi_bs["active_intervention"]


def test_risky_behavior_interception():
    analyzer = BlackspotAndRiskAnalyzer()
    event = analyzer.record_risky_behavior(
        junction_id="NGP_J01_SITABULDI",
        behavior_type="RED_LIGHT_RUNNER_PREDICTED",
        vehicle_class="car",
        track_id=999,
        speed_kmh=58.2,
        severity="CRITICAL",
        description="Speeding vehicle detected heading towards stopline during amber-red transition",
        preventive_action="ALL_RED_HOLD_EXTENDED_2_5S",
    )

    assert event.track_id == 999
    assert event.severity == "CRITICAL"

    events = analyzer.get_risky_behaviors(junction_id="NGP_J01_SITABULDI")
    assert len(events) >= 1
    assert events[0]["behavior_type"] == "RED_LIGHT_RUNNER_PREDICTED"


def test_blackspots_api_endpoints(client):
    # 1. Test blackspots list
    bs_res = client.get("/api/v1/analytics/blackspots")
    assert bs_res.status_code == 200
    data = bs_res.json()
    assert "blackspots" in data
    assert data["total_blackspots"] >= 5
    assert data["critical_count"] >= 2

    # 2. Test risky behaviors feed
    risk_res = client.get("/api/v1/analytics/NGP_J01_SITABULDI/risky-behaviors")
    assert risk_res.status_code == 200
    risk_data = risk_res.json()
    assert "risky_events" in risk_data
    assert len(risk_data["risky_events"]) >= 1

    # 3. Test trigger preventive guard action
    guard_res = client.post("/api/v1/analytics/NGP_J01_SITABULDI/trigger-preventive-guard")
    assert guard_res.status_code == 200
    guard_data = guard_res.json()
    assert guard_data["status"] == "PREVENTIVE_ACTION_EXECUTED"
    assert "All-Red Clearance Extended" in guard_data["action"]
