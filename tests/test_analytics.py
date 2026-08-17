"""
Unit & Integration Tests for GATI Analytics Module.
"""

from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from central.analytics import (
    CongestionForecaster,
    ApproachForecastResult,
    IncidentDetector,
    IncidentAlert,
    LiveRiskIndicator,
    LiveApproachRisk,
    AnalyticsEngine,
)
from edge.vision import ApproachQueueMetrics, TrackedVehicle


class TestCongestionForecaster(unittest.TestCase):
    """Test Holt's linear trend 10-30 min queue & count forecaster."""

    def test_increasing_trend_forecast(self):
        forecaster = CongestionForecaster(sample_interval_sec=3.0)

        # Ingest increasing queue series (5 -> 25 PCU over 20 steps)
        for step in range(20):
            pcu = 5.0 + step * 1.0
            forecaster.update_sample(
                approach_id="APP_NORTH",
                total_pcu=pcu,
                vehicle_count=int(pcu * 1.5),
                queue_length_meters=pcu * 6.0,
            )

        res = forecaster.forecast_approach("APP_NORTH", horizon_minutes=30)

        self.assertEqual(res.approach_id, "APP_NORTH")
        self.assertEqual(res.current_pcu, 24.0)
        self.assertGreater(res.forecast_10min_pcu, res.current_pcu)
        self.assertGreater(res.forecast_30min_pcu, res.forecast_10min_pcu)
        self.assertIn(res.trend_direction, ["INCREASING", "RAPID_INCREASE"])
        self.assertGreater(res.trend_slope_pcu_per_min, 0.0)

    def test_stable_forecast_on_few_samples(self):
        forecaster = CongestionForecaster()
        forecaster.update_sample("APP_SOUTH", total_pcu=10.0, vehicle_count=10, queue_length_meters=60.0)
        res = forecaster.forecast_approach("APP_SOUTH")
        self.assertEqual(res.trend_direction, "STABLE")
        self.assertEqual(res.forecast_10min_pcu, 10.0)


class TestIncidentDetector(unittest.TestCase):
    """Test stalled vehicle and gridlock detection from real displacement vectors."""

    def test_stalled_vehicle_detection(self):
        detector = IncidentDetector(stalled_threshold_sec=10.0, min_displacement_meters=1.5)
        t0 = 1000.0

        v_stalled = TrackedVehicle(track_id=101, vehicle_type="car", confidence=0.9, bbox=(200, 200, 240, 250))

        # Frame 1 at t0
        incidents_1 = detector.update_frame([v_stalled], timestamp=t0, approach_id="APP_NORTH")
        self.assertEqual(len(incidents_1), 0)

        # Frame 2 after 5s: still no movement -> not yet reached 10s threshold
        incidents_2 = detector.update_frame([v_stalled], timestamp=t0 + 5.0, approach_id="APP_NORTH")
        self.assertEqual(len(incidents_2), 0)

        # Frame 3 after 12s: stationary > 10s -> MUST flag incident
        incidents_3 = detector.update_frame([v_stalled], timestamp=t0 + 12.0, approach_id="APP_NORTH")
        self.assertEqual(len(incidents_3), 1)
        alert = incidents_3[0]
        self.assertEqual(alert.track_id, 101)
        self.assertEqual(alert.vehicle_type, "car")
        self.assertGreaterEqual(alert.stationary_duration_sec, 10.0)

    def test_vehicle_recovery_clears_incident(self):
        detector = IncidentDetector(stalled_threshold_sec=5.0, min_displacement_meters=1.5)
        t0 = 1000.0

        v1 = TrackedVehicle(track_id=102, vehicle_type="truck", confidence=0.95, bbox=(100, 100, 150, 200))
        detector.update_frame([v1], timestamp=t0)
        detector.update_frame([v1], timestamp=t0 + 6.0)
        self.assertEqual(len(detector.get_active_incidents()), 1)

        # Vehicle moves 100 pixels away (5 meters)
        v1_moved = TrackedVehicle(track_id=102, vehicle_type="truck", confidence=0.95, bbox=(100, 200, 150, 300))
        detector.update_frame([v1_moved], timestamp=t0 + 8.0)
        self.assertEqual(len(detector.get_active_incidents()), 0)


class TestLiveRiskIndicator(unittest.TestCase):
    """Test live approach risk computation from speed variance, hard braking, and near-misses."""

    def test_hard_braking_detection(self):
        risk_engine = LiveRiskIndicator()
        t0 = 1000.0

        # Frame 1: Vehicle moving at 40 km/h
        v1_fast = TrackedVehicle(track_id=1, vehicle_type="car", confidence=0.9, bbox=(100, 100, 140, 150), speed_kmh=40.0)
        risk_engine.analyze_approach_frame("APP_NORTH", [v1_fast], timestamp=t0)

        # Frame 2 after 0.5s: Decelerated abruptly to 10 km/h (delta = -30 km/h in 0.5s = -16.6 m/s^2)
        v1_slow = TrackedVehicle(track_id=1, vehicle_type="car", confidence=0.9, bbox=(100, 120, 140, 170), speed_kmh=10.0)
        risk_res = risk_engine.analyze_approach_frame("APP_NORTH", [v1_slow], timestamp=t0 + 0.5)

        self.assertGreater(risk_res.hard_braking_count, 0)
        self.assertGreater(risk_res.live_risk_score, 0.0)

    def test_near_miss_detection(self):
        risk_engine = LiveRiskIndicator(near_miss_distance_m=2.0)
        t0 = 1000.0

        # Two vehicles in extreme close proximity (10 pixels = 0.5m apart) with high speed difference
        v1 = TrackedVehicle(track_id=1, vehicle_type="car", confidence=0.9, bbox=(100, 100, 130, 140), speed_kmh=35.0)
        v2 = TrackedVehicle(track_id=2, vehicle_type="two_wheeler", confidence=0.9, bbox=(105, 105, 120, 130), speed_kmh=10.0)

        risk_res = risk_engine.analyze_approach_frame("APP_EAST", [v1, v2], timestamp=t0)
        self.assertGreater(risk_res.near_miss_count, 0)


class TestAnalyticsEngine(unittest.TestCase):
    """Test unified analytics engine orchestration."""

    def test_analytics_engine_batch_processing(self):
        engine = AnalyticsEngine()
        metrics = {
            "APP_NORTH": ApproachQueueMetrics(approach_id="APP_NORTH", total_pcu=12.0, queue_length_meters=72.0),
            "APP_SOUTH": ApproachQueueMetrics(approach_id="APP_SOUTH", total_pcu=6.0, queue_length_meters=36.0),
        }
        vehicles = [
            TrackedVehicle(track_id=1, vehicle_type="car", confidence=0.9, bbox=(100, 100, 140, 150), speed_kmh=25.0),
            TrackedVehicle(track_id=2, vehicle_type="bus", confidence=0.9, bbox=(200, 200, 260, 300), speed_kmh=20.0),
        ]

        batch_res = engine.process_telemetry_step(
            timestamp=1000.0,
            approach_metrics=metrics,
            tracked_vehicles=vehicles,
        )

        self.assertEqual(batch_res.timestamp, 1000.0)
        self.assertIn("APP_NORTH", batch_res.forecasts)
        self.assertIn("APP_SOUTH", batch_res.forecasts)
        self.assertIn("APP_NORTH", batch_res.approach_risks)


if __name__ == "__main__":
    unittest.main()
