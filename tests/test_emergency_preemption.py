"""
Unit & Integration Tests for Emergency Vehicle Preemption (EVP) and Green Corridors.
"""

import pytest
import time
from fastapi.testclient import TestClient

from central.api.main import app
from central.coordinator.emergency_corridor_manager import EmergencyCorridorManager, emergency_manager


@pytest.fixture
def client():
    return TestClient(app)


def test_emergency_corridor_manager_dispatch():
    manager = EmergencyCorridorManager()
    plan = manager.dispatch_emergency_vehicle(
        route_key="AMBULANCE_AIIMS_CORRIDOR",
        call_sign="108_AMB_TEST_01",
        vehicle_type="AMBULANCE",
        custom_speed_kmh=60.0,
    )

    assert plan.is_active is True
    assert plan.vehicle_type == "AMBULANCE"
    assert len(plan.junction_sequence) == 5
    assert "NGP_J01_SITABULDI" in plan.schedules
    assert "NGP_J05_CHHATRAPATI_SQ" in plan.schedules

    # Origin starts at 0s lock start
    assert plan.schedules["NGP_J01_SITABULDI"]["lock_start_rel_sec"] == 0.0
    # Downstream has progressive offset
    assert plan.schedules["NGP_J02_VARIETIES_SQ"]["lock_start_rel_sec"] > 0.0

    # Test override check
    override = manager.get_junction_emergency_override("NGP_J01_SITABULDI")
    assert override is not None
    assert override["is_emergency_preempted"] is True
    assert override["call_sign"] == "108_AMB_TEST_01"

    # Test clear
    cleared = manager.clear_emergency_dispatch(plan.dispatch_id)
    assert cleared is True
    assert plan.is_active is False


def test_emergency_routes_endpoint(client):
    res = client.get("/api/v1/emergency/routes")
    assert res.status_code == 200
    data = res.json()
    assert "routes" in data
    assert len(data["routes"]) >= 2
    route_keys = [r["route_key"] for r in data["routes"]]
    assert "AMBULANCE_AIIMS_CORRIDOR" in route_keys
    assert "FIRE_SITABULDI_MARKET" in route_keys


def test_emergency_dispatch_and_clear_api(client):
    # 1. Dispatch ambulance
    payload = {
        "route_key": "AMBULANCE_AIIMS_CORRIDOR",
        "call_sign": "108_MH31_EMERGENCY",
        "vehicle_type": "AMBULANCE",
        "dispatched_by": "ICCC_TEST_OPERATOR",
        "target_speed_kmh": 55.0,
    }
    dispatch_res = client.post("/api/v1/emergency/dispatch", json=payload)
    assert dispatch_res.status_code == 200
    dispatch_data = dispatch_res.json()
    assert dispatch_data["status"] == "ENGAGED"
    assert "dispatch_id" in dispatch_data
    dispatch_id = dispatch_data["dispatch_id"]

    # 2. Check active list
    active_res = client.get("/api/v1/emergency/active")
    assert active_res.status_code == 200
    active_data = active_res.json()
    assert active_data["active_count"] >= 1
    found = any(c["dispatch_id"] == dispatch_id for c in active_data["active_corridors"])
    assert found is True

    # 3. Clear emergency
    clear_res = client.post(f"/api/v1/emergency/clear/{dispatch_id}")
    assert clear_res.status_code == 200
    clear_data = clear_res.json()
    assert clear_data["status"] == "CLEARED"
