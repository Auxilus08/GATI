"""
Unit & Integration Tests for Nearest Responsible Authority Resolver & Safety Events API.
"""

import pytest
from fastapi.testclient import TestClient

from central.api.main import app
from central.analytics.nearest_authority_resolver import StaticNagpurAuthorityResolver, authority_resolver


@pytest.fixture
def client():
    return TestClient(app)


def test_nearest_authority_resolver_sitabuldi():
    resolver = StaticNagpurAuthorityResolver()
    resolved = resolver.resolve_nearest_authorities("NGP_J01_SITABULDI")

    assert resolved.junction_id == "NGP_J01_SITABULDI"
    assert "Sitabuldi" in resolved.primary_authority.station_name
    assert resolved.primary_authority.distance_km <= 0.5
    assert resolved.primary_authority.estimated_arrival_minutes <= 2.0
    assert "GMCH" in resolved.medical_authority.station_name
    assert resolved.fire_authority is not None


def test_safety_event_ingestion_and_auto_signal_guard(client):
    payload = {
        "junction_id": "NGP_J01_SITABULDI",
        "event_type": "accident_suspected",
        "confidence": 0.94,
        "gps_coordinates": {"lat": 21.1458, "lng": 79.0882},
        "approach_id": "APP_NORTH",
        "track_id": 404,
        "vehicle_class": "car",
        "details": {"description": "Vehicle rollover and sudden deceleration detected"},
        "snapshot_jpeg_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    }

    # 1. Post safety event
    res = client.post("/api/v1/safety/events", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ACCEPTED"
    assert "event_id" in data
    assert "Sitabuldi" in data["nearest_authority"]
    assert data["auto_signal_action"] == "ALL_RED_HOLD_APPLIED_FOR_APPROACH_CLEARANCE"
    event_id = data["event_id"]

    # 2. Query safety events audit list
    list_res = client.get("/api/v1/safety/events?junction_id=NGP_J01_SITABULDI")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total_count"] >= 1
    target_event = next((e for e in list_data["events"] if e["event_id"] == event_id), None)
    assert target_event is not None
    assert target_event["status"] == "PENDING_OPERATOR_ACK"
    assert target_event["nearest_authorities"]["primary"]["contact_number"] is not None

    # 3. 1-Click Operator Acknowledge & Dispatch
    ack_res = client.post(
        f"/api/v1/safety/events/{event_id}/acknowledge",
        json={
            "operator_id": "ICCC_POLICE_CHIEF_MH31",
            "dispatch_action": "DISPATCH_PATROL_AND_108_AMBULANCE",
            "notes": "Emergency Bolero Interceptor #01 and GMCH ALS Ambulance dispatched",
        },
    )
    assert ack_res.status_code == 200
    ack_data = ack_res.json()
    assert ack_data["status"] == "SUCCESS"
    assert ack_data["acknowledged_by"] == "ICCC_POLICE_CHIEF_MH31"

    # 4. Verify updated audit status
    list_res2 = client.get("/api/v1/safety/events")
    updated_event = next(e for e in list_res2.json()["events"] if e["event_id"] == event_id)
    assert updated_event["status"] == "DISPATCHED_ACKNOWLEDGED"
    assert updated_event["acknowledged"] is True
