"""
Tests verifying the solutions to the Judge Critique and Technical Vulnerabilities:
1. Planar Homography Perspective Metric Correction
2. NTCIP 1202 Signal Actuation & Conflict Monitor Unit (CMU) Safety Guard
3. Edge Hardware Thermal & Watchdog Health Monitoring
4. Max-Pressure Downstream Backpressure Spillback Resistance
"""

import unittest
from pathlib import Path
import sys
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from edge.vision.homography import PlanarHomographyTransformer
from edge.controller.ntcip_interface import NTCIPControllerInterface, ConflictMonitorUnit
from edge.telemetry.hardware_health import EdgeHardwareHealthMonitor
from edge.controller.max_pressure import MaxPressureController
from edge.vision import ApproachQueueMetrics
from config.settings import (
    JunctionConfig,
    ApproachConfig,
    PhaseConfig,
    MaxPressureConfig,
    SignalGuardrails,
)


class TestPlanarHomography(unittest.TestCase):
    """Tests 2D perspective foreshortening and metric ground plane transformation."""

    def test_homography_calibration_and_metric_distance(self):
        # 4 camera pixel points (trapezoid due to perspective foreshortening)
        cam_points = [(100.0, 400.0), (540.0, 400.0), (420.0, 150.0), (220.0, 150.0)]
        # Corresponding real-world metric rectangle (10m wide by 30m long approach lane)
        ground_metric_points = [(0.0, 0.0), (10.0, 0.0), (10.0, 30.0), (0.0, 30.0)]

        transformer = PlanarHomographyTransformer(cam_points, ground_metric_points)
        self.assertIsNotNone(transformer.homography_matrix)

        # Transform stopline center (320, 400) -> should be near (5.0, 0.0) meters
        gx, gy = transformer.pixel_to_ground_metric(320.0, 400.0)
        self.assertAlmostEqual(gx, 5.0, delta=0.5)
        self.assertAlmostEqual(gy, 0.0, delta=0.5)

        # Test distance calculation between stopline and furthest vehicle
        dist = transformer.compute_distance_meters((320.0, 400.0), (320.0, 150.0))
        self.assertAlmostEqual(dist, 30.0, delta=2.0)


class TestNTCIPControllerInterface(unittest.TestCase):
    """Tests physical NTCIP 1202 relay commands and Conflict Monitor Unit (CMU) guards."""

    def test_ntcip_relay_state_generation(self):
        conflicts = [(1, 2), (1, 3)]
        adapter = NTCIPControllerInterface(
            junction_id="TEST_J01",
            conflicting_phase_pairs=conflicts,
            ntcip_station_address=2,
        )

        # Phase 1 GREEN on 3-phase junction
        relay_state = adapter.generate_ntcip_phase_command(
            active_phase_id=1,
            signal_state="GREEN",
            all_phase_ids=[1, 2, 3],
        )

        # Bit 0 should be green (1 << 0 = 1), Bits 1 and 2 should be red (1 << 1 | 1 << 2 = 6)
        self.assertEqual(relay_state.green_relay_mask, 1)
        self.assertEqual(relay_state.red_relay_mask, 6)
        self.assertEqual(relay_state.amber_relay_mask, 0)
        self.assertEqual(len(relay_state.raw_ntcip_frame), 7)
        self.assertEqual(relay_state.raw_ntcip_frame[0], 0x7E)

    def test_cmu_blocks_hazardous_conflicting_greens(self):
        cmu = ConflictMonitorUnit(conflicting_phase_pairs=[(1, 2), (1, 3)])

        # Independent non-conflicting phases (e.g. 2 and 3 if configured)
        self.assertTrue(cmu.validate_green_safety([2]))

        # Hazardous simultaneous greens: Phase 1 and Phase 2
        is_safe = cmu.validate_green_safety([1, 2])
        self.assertFalse(is_safe)


class TestHardwareHealthMonitor(unittest.TestCase):
    """Tests roadside cabinet thermal monitoring and power budget."""

    def test_edge_thermal_and_watchdog_telemetry(self):
        monitor = EdgeHardwareHealthMonitor(thermal_warning_threshold_c=75.0)
        snapshot = monitor.get_hardware_snapshot(last_inference_ms=15.4)

        self.assertLess(snapshot.soc_temperature_c, 75.0)
        self.assertFalse(snapshot.thermal_throttling)
        self.assertLessEqual(snapshot.power_draw_watts, 15.0)  # Low 10W TDP budget
        self.assertGreater(snapshot.watchdog_heartbeat, 0.0)


class TestMaxPressureDownstreamResistance(unittest.TestCase):
    """Tests multi-junction network backpressure penalty preventing downstream spillback."""

    def test_downstream_queue_reduces_upstream_green_pressure(self):
        junc = JunctionConfig(
            junction_id="JUNC_UPSTREAM",
            name="Upstream Junction",
            approaches=[
                ApproachConfig(id="APP_MAIN", name="Main", direction="North", camera_source="rtsp://dummy", downstream_junction_id="JUNC_DOWNSTREAM"),
                ApproachConfig(id="APP_SIDE", name="Side", direction="East", camera_source="rtsp://dummy"),
            ],
            phases=[
                PhaseConfig(phase_id=1, name="Main Phase", active_approaches=["APP_MAIN"]),
                PhaseConfig(phase_id=2, name="Side Phase", active_approaches=["APP_SIDE"]),
            ],
        )

        controller = MaxPressureController(junc, MaxPressureConfig(pressure_smoothing_alpha=1.0))

        # Scenario A: Downstream junction is clear (0 PCU)
        metrics = {
            "APP_MAIN": ApproachQueueMetrics(approach_id="APP_MAIN", total_pcu=20.0),
            "APP_SIDE": ApproachQueueMetrics(approach_id="APP_SIDE", total_pcu=10.0),
        }
        pressures_clear = controller.compute_phase_pressures(
            metrics,
            downstream_metrics={"JUNC_DOWNSTREAM": 0.0},
        )
        self.assertEqual(pressures_clear[1], 20.0)

        # Scenario B: Downstream junction is severely blocked with spillback (50 PCU queue)
        # Pressure = Upstream - 0.3 * Downstream = 20 - 0.3 * 50 = 5.0
        pressures_spillback = controller.compute_phase_pressures(
            metrics,
            downstream_metrics={"JUNC_DOWNSTREAM": 50.0},
        )
        self.assertEqual(pressures_spillback[1], 5.0)
        self.assertLess(pressures_spillback[1], pressures_clear[1])


if __name__ == "__main__":
    unittest.main()
