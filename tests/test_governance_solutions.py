"""
Tests verifying the Non-Technical, Governance & Operational solutions:
1. VIP Motorcade Green Wave Multi-Junction Scheduler
2. Religious Procession / Informal Road Blockage Anomaly Detector
3. Field Constable Mobile Quick-Action Override Endpoint
4. Municipal ESG Carbon & Citizen Fuel Savings Reporter
"""

import unittest
from pathlib import Path
import sys
import time
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from central.coordinator.vip_corridor_manager import VIPCorridorManager
from central.analytics.informal_occupancy_detector import InformalOccupancyDetector
from central.analytics.governance_reporter import MunicipalGovernanceReporter
from central.api.main import app


class TestVIPCorridorProgression(unittest.TestCase):
    """Tests VIP motorcade sequential green wave offset calculation."""

    def test_vip_convoy_scheduling_across_corridor(self):
        mgr = VIPCorridorManager()
        junctions = ["NGP_J01_SITABULDI", "NGP_J02_VARIETIES_SQ", "NGP_J03_RAHATE_COLONY"]
        distances = {
            "NGP_J01_SITABULDI->NGP_J02_VARIETIES_SQ": 450.0,
            "NGP_J02_VARIETIES_SQ->NGP_J03_RAHATE_COLONY": 600.0,
        }
        phases = {"NGP_J01_SITABULDI": 1, "NGP_J02_VARIETIES_SQ": 1, "NGP_J03_RAHATE_COLONY": 1}

        plan = mgr.create_convoy_progression_plan(
            corridor_id="CORR_WARDHA_RD",
            junction_sequence=junctions,
            inter_junction_distances_m=distances,
            arterial_phase_id_map=phases,
            target_speed_kmh=40.0,
            operator_id="POLICE_COMMISSIONER_401",
        )

        self.assertTrue(plan.convoy_active)
        self.assertEqual(len(plan.junction_schedules), 3)

        # Sitabuldi should lock immediately (start 0.0s)
        self.assertEqual(plan.junction_schedules["NGP_J01_SITABULDI"]["lock_start_rel_sec"], 0.0)

        # Varieties Square should lock with forward travel time offset (~40.5s)
        self.assertGreater(plan.junction_schedules["NGP_J02_VARIETIES_SQ"]["lock_start_rel_sec"], 20.0)

        # Test active override directive at elapsed 5s
        directive = mgr.get_junction_override_directive(
            plan_id=plan.plan_id,
            junction_id="NGP_J01_SITABULDI",
            current_time=plan.created_timestamp + 5.0,
        )
        self.assertIsNotNone(directive)
        self.assertEqual(directive["action"], "LOCK")
        self.assertEqual(directive["phase_id"], 1)


class TestInformalOccupancyDetector(unittest.TestCase):
    """Tests detection of religious procession and street market crowd blockages."""

    def test_procession_stagnant_occupancy_trigger(self):
        detector = InformalOccupancyDetector(min_stagnant_duration_sec=60.0, max_speed_kmh_threshold=2.0)
        t0 = time.time()

        # Step 1: Initial detection at t0
        event1 = detector.evaluate_approach(
            junction_id="NGP_J01",
            approach_id="APP_NORTH",
            total_pcu=25.0,
            average_speed_kmh=1.2,
            current_time=t0,
        )
        self.assertIsNone(event1)  # Duration too short yet

        # Step 2: 70 seconds later with continuous blockage
        event2 = detector.evaluate_approach(
            junction_id="NGP_J01",
            approach_id="APP_NORTH",
            total_pcu=28.0,
            average_speed_kmh=0.8,
            current_time=t0 + 70.0,
        )
        self.assertIsNotNone(event2)
        self.assertEqual(event2.recommended_action, "REALLOCATE_GREEN_TO_CROSS_STREETS")
        self.assertEqual(event2.occupancy_type, "PROCESSION_OR_MARKET_BLOCKAGE")


class TestFieldConstableOverrideAPI(unittest.TestCase):
    """Tests frontline mobile quick-action endpoint."""

    def setUp(self):
        self.client = TestClient(app)

    def test_constable_one_tap_queue_flush(self):
        payload = {
            "junction_id": "NGP_J01_SITABULDI",
            "action_type": "FLUSH_HEAVY_QUEUE",
            "officer_badge_id": "CONSTABLE_MH31_8821",
            "target_phase_id": 1,
            "duration_seconds": 45,
        }
        res = self.client.post("/api/v1/field/quick-action", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "LOCKED")
        self.assertEqual(data["locked_phase_id"], 1)

    def test_constable_restore_autonomous_ai(self):
        payload = {
            "junction_id": "NGP_J01_SITABULDI",
            "action_type": "RESTORE_AUTONOMOUS",
            "officer_badge_id": "CONSTABLE_MH31_8821",
        }
        res = self.client.post("/api/v1/field/quick-action", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "AUTONOMOUS_RESTORED")


class TestMunicipalGovernanceReporter(unittest.TestCase):
    """Tests municipal ESG environmental & financial report synthesis."""

    def test_city_esg_report_calculation(self):
        reporter = MunicipalGovernanceReporter(city_name="Nagpur", fuel_price_inr_per_liter=105.0)

        comparisons = {
            "NGP_J01": {"estimated_fuel_saved_liters": 1.2, "co2_reduction_kg": 2.8, "wait_time_reduction_pct": 32.0},
            "NGP_J02": {"estimated_fuel_saved_liters": 0.8, "co2_reduction_kg": 1.9, "wait_time_reduction_pct": 28.5},
        }
        logs = [
            {"operator_id": "COP_1", "duration_sec": 60},
            {"operator_id": "COP_2", "duration_sec": 120},
        ]

        report = reporter.generate_city_esg_report(comparisons, logs)
        self.assertEqual(report.city_name, "Nagpur")
        self.assertEqual(report.total_monitored_junctions, 2)
        self.assertEqual(report.daily_fuel_saved_liters, 32.0)  # (1.2 + 0.8) * 16 hrs = 32.0 L
        self.assertEqual(report.daily_citizen_rupees_saved, 3360.0)  # 32 * 105
        self.assertEqual(report.override_compliance_pct, 100.0)


if __name__ == "__main__":
    unittest.main()
