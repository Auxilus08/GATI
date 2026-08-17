"""
Unit & Integration Tests for GATI Signal Controller & Comparison Harness.
"""

from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from edge.controller import (
    MaxPressureController,
    ControllerDecision,
    OverrideManager,
    OverrideEvent,
    SignalComparisonHarness,
    SignalControllerState,
    SignalPhaseState,
)
from edge.vision import ApproachQueueMetrics
from config.settings import (
    JunctionConfig,
    ApproachConfig,
    PhaseConfig,
    MaxPressureConfig,
    SignalGuardrails,
)


def create_test_junction() -> JunctionConfig:
    return JunctionConfig(
        junction_id="TEST_JUNC_01",
        name="Test Interchange",
        approaches=[
            ApproachConfig(id="APP_N", name="North", direction="North", camera_source="rtsp://dummy1"),
            ApproachConfig(id="APP_S", name="South", direction="South", camera_source="rtsp://dummy2"),
            ApproachConfig(id="APP_E", name="East", direction="East", camera_source="rtsp://dummy3"),
            ApproachConfig(id="APP_W", name="West", direction="West", camera_source="rtsp://dummy4"),
        ],
        phases=[
            PhaseConfig(phase_id=1, name="North-South Through", active_approaches=["APP_N", "APP_S"]),
            PhaseConfig(phase_id=2, name="East-West Through", active_approaches=["APP_E", "APP_W"]),
        ],
    )


class TestMaxPressureController(unittest.TestCase):
    """Test Max-Pressure optimization and guardrail safety."""

    def setUp(self):
        self.j_config = create_test_junction()
        self.guardrails = SignalGuardrails(min_green_seconds=10.0, max_green_seconds=40.0)
        self.mp_config = MaxPressureConfig(pressure_smoothing_alpha=0.5)
        self.controller = MaxPressureController(
            junction_config=self.j_config,
            mp_config=self.mp_config,
            guardrails=self.guardrails,
        )

    def test_phase_selection_under_queue_pressure(self):
        # East-West has heavy queue, North-South has light queue
        metrics = {
            "APP_N": ApproachQueueMetrics(approach_id="APP_N", total_pcu=2.0),
            "APP_S": ApproachQueueMetrics(approach_id="APP_S", total_pcu=3.0),
            "APP_E": ApproachQueueMetrics(approach_id="APP_E", total_pcu=18.0),
            "APP_W": ApproachQueueMetrics(approach_id="APP_W", total_pcu=16.0),
        }

        decision = self.controller.evaluate_decision(
            approach_metrics=metrics,
            current_phase_id=1,
            elapsed_green_sec=15.0,  # Past min green (10s)
        )

        self.assertEqual(decision.recommended_phase_id, 2)
        self.assertTrue(decision.is_switch)
        self.assertEqual(decision.decision_reason, "MAX_PRESSURE_SWITCH")

    def test_min_green_guardrail_hold(self):
        # Even if Phase 2 has overwhelming pressure, hold Phase 1 if elapsed < min_green (10s)
        metrics = {
            "APP_N": ApproachQueueMetrics(approach_id="APP_N", total_pcu=1.0),
            "APP_S": ApproachQueueMetrics(approach_id="APP_S", total_pcu=1.0),
            "APP_E": ApproachQueueMetrics(approach_id="APP_E", total_pcu=50.0),
            "APP_W": ApproachQueueMetrics(approach_id="APP_W", total_pcu=50.0),
        }

        decision = self.controller.evaluate_decision(
            approach_metrics=metrics,
            current_phase_id=1,
            elapsed_green_sec=4.0,  # Below min green 10.0s
        )

        self.assertEqual(decision.recommended_phase_id, 1)
        self.assertFalse(decision.is_switch)
        self.assertEqual(decision.decision_reason, "MIN_GREEN_HOLD")

    def test_max_green_guardrail_switch(self):
        # When max green is exceeded (40s), force a switch even if current phase still has queue
        metrics = {
            "APP_N": ApproachQueueMetrics(approach_id="APP_N", total_pcu=20.0),
            "APP_S": ApproachQueueMetrics(approach_id="APP_S", total_pcu=20.0),
            "APP_E": ApproachQueueMetrics(approach_id="APP_E", total_pcu=10.0),
            "APP_W": ApproachQueueMetrics(approach_id="APP_W", total_pcu=10.0),
        }

        decision = self.controller.evaluate_decision(
            approach_metrics=metrics,
            current_phase_id=1,
            elapsed_green_sec=45.0,  # Exceeds max green 40.0s
        )

        self.assertEqual(decision.recommended_phase_id, 2)
        self.assertTrue(decision.is_switch)
        self.assertEqual(decision.decision_reason, "MAX_GREEN_EXCEEDED")

    def test_low_detection_confidence_hold(self):
        # Degraded vision (fog / heavy rain / occlusion) with low confidence score (< 0.40)
        # Should hold current state safely rather than make chaotic switching decisions
        metrics = {
            "APP_N": ApproachQueueMetrics(approach_id="APP_N", total_pcu=5.0, confidence_score=0.25),
            "APP_S": ApproachQueueMetrics(approach_id="APP_S", total_pcu=5.0, confidence_score=0.30),
            "APP_E": ApproachQueueMetrics(approach_id="APP_E", total_pcu=40.0, confidence_score=0.20),
            "APP_W": ApproachQueueMetrics(approach_id="APP_W", total_pcu=40.0, confidence_score=0.35),
        }

        decision = self.controller.evaluate_decision(
            approach_metrics=metrics,
            current_phase_id=1,
            elapsed_green_sec=20.0,
        )

        self.assertEqual(decision.recommended_phase_id, 1)
        self.assertFalse(decision.is_switch)
        self.assertIn("LOW_CONFIDENCE_HOLD", decision.decision_reason)

    def test_all_approaches_gridlock_fallback(self):
        # When all approaches are totally saturated (> 25 PCU), MaxPressure falls back to fixed time
        metrics = {
            "APP_N": ApproachQueueMetrics(approach_id="APP_N", total_pcu=30.0),
            "APP_S": ApproachQueueMetrics(approach_id="APP_S", total_pcu=32.0),
            "APP_E": ApproachQueueMetrics(approach_id="APP_E", total_pcu=35.0),
            "APP_W": ApproachQueueMetrics(approach_id="APP_W", total_pcu=28.0),
        }

        # If elapsed time reached 30s fixed interval, smoothly advance to next cycle phase
        decision = self.controller.evaluate_decision(
            approach_metrics=metrics,
            current_phase_id=1,
            elapsed_green_sec=32.0,
        )

        self.assertEqual(decision.recommended_phase_id, 2)
        self.assertTrue(decision.is_switch)
        self.assertEqual(decision.decision_reason, "GRIDLOCK_FALLBACK_FIXED_TIME")



class TestOperatorOverride(unittest.TestCase):
    """Test human operator override locks, releases, and audit logs."""

    def test_operator_override_lock_and_release(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            audit_path = Path(tmp_dir) / "audit.jsonl"
            override_mgr = OverrideManager(junction_id="TEST_JUNC", audit_log_path=audit_path)

            j_config = create_test_junction()
            controller = MaxPressureController(
                junction_config=j_config,
                mp_config=MaxPressureConfig(),
                override_manager=override_mgr,
            )

            metrics = {
                "APP_N": ApproachQueueMetrics(approach_id="APP_N", total_pcu=50.0),
                "APP_S": ApproachQueueMetrics(approach_id="APP_S", total_pcu=50.0),
                "APP_E": ApproachQueueMetrics(approach_id="APP_E", total_pcu=0.0),
                "APP_W": ApproachQueueMetrics(approach_id="APP_W", total_pcu=0.0),
            }

            # 1. Operator locks Phase 2 (e.g. VIP convoy)
            override_mgr.lock_phase(phase_id=2, operator_id="POLICE_OFFICER_42", reason="VIP Convoy Clearance", duration_sec=60.0)

            # Controller MUST recommend Phase 2 despite heavy Phase 1 queue
            decision = controller.evaluate_decision(
                approach_metrics=metrics,
                current_phase_id=1,
                elapsed_green_sec=25.0,
            )

            self.assertEqual(decision.recommended_phase_id, 2)
            self.assertTrue(decision.override_active)
            self.assertEqual(decision.operator_id, "POLICE_OFFICER_42")

            # 2. Release lock
            override_mgr.release_override(operator_id="POLICE_OFFICER_42", reason="Convoy cleared")

            # Now controller should resume autonomous Max-Pressure (Phase 1 has 100 PCU)
            decision2 = controller.evaluate_decision(
                approach_metrics=metrics,
                current_phase_id=2,
                elapsed_green_sec=25.0,
            )

            self.assertEqual(decision2.recommended_phase_id, 1)
            self.assertFalse(decision2.override_active)

            # 3. Check audit log file persistence
            self.assertTrue(audit_path.exists())
            with open(audit_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                self.assertEqual(len(lines), 2)  # LOCK and RELEASE


class TestComparisonHarness(unittest.TestCase):
    """Test before/after comparison harness calculations."""

    def test_harness_computes_wait_reduction(self):
        j_config = create_test_junction()
        guardrails = SignalGuardrails(min_green_seconds=5.0, max_green_seconds=30.0)
        harness = SignalComparisonHarness(
            junction_config=j_config,
            guardrails=guardrails,
            fixed_cycle_splits={1: 40.0, 2: 40.0},
        )

        # Create telemetry windows where Phase 2 is heavily loaded while Phase 1 has zero traffic
        # Fixed time wastes 40s on empty Phase 1, while Max-Pressure switches after 5s min-green
        sample_windows = []
        for i in range(25):
            sample_windows.append({
                "timestamp": 1000.0 + i * 3.0,
                "approaches": {
                    "APP_N": {"total_pcu": 0.5, "average_speed_kmh": 25.0},
                    "APP_S": {"total_pcu": 0.5, "average_speed_kmh": 25.0},
                    "APP_E": {"total_pcu": 25.0, "average_speed_kmh": 5.0},
                    "APP_W": {"total_pcu": 25.0, "average_speed_kmh": 5.0},
                },
            })

        summary, timeseries = harness.run_comparison_from_windows(sample_windows)

        self.assertEqual(summary.total_timesteps, 25)
        self.assertGreater(summary.fixed_total_delay_pcu_sec, 0)
        self.assertGreater(summary.mp_total_delay_pcu_sec, 0)
        self.assertGreater(summary.wait_time_reduction_pct, 0.0)
        self.assertLess(summary.mp_avg_wait_sec, summary.fixed_avg_wait_sec)

        with tempfile.TemporaryDirectory() as tmp_dir:
            harness.save_comparison_reports(summary, timeseries, tmp_dir)
            self.assertTrue((Path(tmp_dir) / "comparison_summary.json").exists())
            self.assertTrue((Path(tmp_dir) / "comparison_timeseries.csv").exists())


if __name__ == "__main__":
    unittest.main()
