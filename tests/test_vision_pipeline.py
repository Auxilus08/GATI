"""
Unit & Integration Tests for GATI Edge Vision Detection & Tracking Module.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from edge.vision.taxonomy import (
    IndianTrafficClass,
    IndianTrafficTaxonomy,
    IRC_PCU_WEIGHTS,
)
from edge.vision.tracker import (
    ByteTrackerManager,
    TrackPoint,
    VelocityEstimator,
)
from edge.vision.detector import (
    ApproachROI,
    YOLODetector,
    point_in_polygon,
)
from edge.vision.video_pipeline import (
    StructuredTelemetryWriter,
    TrafficVideoPipeline,
)
from edge.vision import ApproachQueueMetrics, TrackedVehicle
from edge.vision.pcu_engine import PCUEngine
from config.settings import PCUWeights


class TestIndianTaxonomy(unittest.TestCase):
    """Test taxonomic mapping from COCO to Indian Traffic standards."""

    def test_direct_coco_mapping(self):
        self.assertEqual(IndianTrafficTaxonomy.map_coco_class("motorcycle"), IndianTrafficClass.TWO_WHEELER)
        self.assertEqual(IndianTrafficTaxonomy.map_coco_class("bicycle"), IndianTrafficClass.CYCLE)
        self.assertEqual(IndianTrafficTaxonomy.map_coco_class("car"), IndianTrafficClass.CAR)
        self.assertEqual(IndianTrafficTaxonomy.map_coco_class("bus"), IndianTrafficClass.BUS)
        self.assertEqual(IndianTrafficTaxonomy.map_coco_class("truck"), IndianTrafficClass.TRUCK)
        self.assertEqual(IndianTrafficTaxonomy.map_coco_class("person"), IndianTrafficClass.PEDESTRIAN)

    def test_auto_rickshaw_heuristic(self):
        # Auto-rickshaws have a taller aspect ratio than standard cars (width < height)
        # Bounding box: x1=100, y1=100, x2=170, y2=200 -> w=70, h=100 -> aspect ratio = 0.70
        bbox_auto = (100, 100, 170, 200)
        mapped = IndianTrafficTaxonomy.map_coco_class("car", bbox=bbox_auto)
        self.assertEqual(mapped, IndianTrafficClass.AUTO_RICKSHAW)

    def test_cart_heuristic(self):
        # Cart detected as bicycle with wide bounding box
        bbox_cart = (50, 50, 250, 120)  # w=200, h=70 -> aspect_ratio = 2.85
        mapped = IndianTrafficTaxonomy.map_coco_class("bicycle", bbox=bbox_cart)
        self.assertEqual(mapped, IndianTrafficClass.CART)

    def test_pcu_weights(self):
        self.assertEqual(IndianTrafficTaxonomy.get_pcu(IndianTrafficClass.TWO_WHEELER), 0.5)
        self.assertEqual(IndianTrafficTaxonomy.get_pcu(IndianTrafficClass.AUTO_RICKSHAW), 0.8)
        self.assertEqual(IndianTrafficTaxonomy.get_pcu(IndianTrafficClass.CAR), 1.0)
        self.assertEqual(IndianTrafficTaxonomy.get_pcu(IndianTrafficClass.BUS), 3.0)
        self.assertEqual(IndianTrafficTaxonomy.get_pcu(IndianTrafficClass.TRUCK), 3.0)


class TestVelocityEstimatorAndTracker(unittest.TestCase):
    """Test ByteTrack tracking manager and speed estimation."""

    def test_speed_calculation(self):
        tracker = ByteTrackerManager(meters_per_pixel=0.05)
        t0 = 1000.0

        # Frame 1 at t0
        tstate1 = tracker.update_track(
            track_id=1,
            vehicle_type="car",
            confidence=0.9,
            bbox=(100, 100, 140, 160),
            timestamp=t0,
        )
        self.assertEqual(tstate1.track_id, 1)

        # Frame 2 at t0 + 0.5s: moved 50 pixels down (50 * 0.05 = 2.5 meters in 0.5s = 5 m/s = 18 km/h)
        tstate2 = tracker.update_track(
            track_id=1,
            vehicle_type="car",
            confidence=0.9,
            bbox=(100, 150, 140, 210),
            timestamp=t0 + 0.5,
        )

        self.assertAlmostEqual(tstate2.current_speed_kmh, 18.0, delta=2.0)
        self.assertFalse(tstate2.is_stationary)

    def test_stationary_detection(self):
        tracker = ByteTrackerManager(meters_per_pixel=0.05)
        t0 = 1000.0

        # Frame 1
        tracker.update_track(
            track_id=2,
            vehicle_type="bus",
            confidence=0.95,
            bbox=(200, 200, 250, 300),
            timestamp=t0,
        )
        # Frame 2 after 1s: virtually no movement (1 pixel)
        tstate = tracker.update_track(
            track_id=2,
            vehicle_type="bus",
            confidence=0.95,
            bbox=(200, 201, 250, 301),
            timestamp=t0 + 1.0,
        )

        self.assertTrue(tstate.is_stationary)
        self.assertLess(tstate.current_speed_kmh, 1.0)


class TestApproachROIAndQueue(unittest.TestCase):
    """Test approach polygon containment and queue estimation."""

    def test_point_in_polygon(self):
        poly = np.array([(0, 0), (200, 0), (200, 200), (0, 200)], dtype=np.int32)
        self.assertTrue(point_in_polygon((100, 100), poly))
        self.assertFalse(point_in_polygon((300, 300), poly))

    def test_approach_queue_calculation(self):
        detector = YOLODetector.__new__(YOLODetector)
        detector.pcu_engine = PCUEngine(PCUWeights())
        detector.tracker_manager = ByteTrackerManager()
        detector.approaches = {}

        # Register approach
        detector.register_approach(
            approach_id="APP_NORTH",
            name="North Approach",
            polygon_points=[(0, 0), (640, 0), (640, 480), (0, 480)],
            stopline_point=(320, 400),
            meters_per_pixel=0.05,
        )

        # Create stopped vehicles
        v1 = TrackedVehicle(track_id=1, vehicle_type="car", confidence=0.9, bbox=(300, 300, 340, 350), speed_kmh=0.0)
        v2 = TrackedVehicle(track_id=2, vehicle_type="bus", confidence=0.85, bbox=(300, 200, 360, 280), speed_kmh=0.0)
        v3 = TrackedVehicle(track_id=3, vehicle_type="two_wheeler", confidence=0.8, bbox=(280, 350, 300, 380), speed_kmh=0.0)

        metrics = detector.compute_approach_metrics([v1, v2, v3])
        app_metric = metrics["APP_NORTH"]

        # Counts: 1 car (1.0 PCU), 1 bus (3.0 PCU), 1 two_wheeler (0.5 PCU) = 4.5 PCU
        self.assertEqual(app_metric.total_pcu, 4.5)
        self.assertEqual(app_metric.vehicle_counts["car"], 1)
        self.assertEqual(app_metric.vehicle_counts["bus"], 1)
        self.assertEqual(app_metric.vehicle_counts["two_wheeler"], 1)
        self.assertGreater(app_metric.queue_length_meters, 0)


class TestStructuredLogging(unittest.TestCase):
    """Test structured JSON and CSV telemetry logger."""

    def test_writer_creates_valid_logs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            writer = StructuredTelemetryWriter(output_dir=tmp_dir, junction_id="TEST_JUNCTION")

            vehicles = [
                TrackedVehicle(track_id=1, vehicle_type="car", confidence=0.92, bbox=(10, 10, 50, 50), speed_kmh=24.0),
                TrackedVehicle(track_id=2, vehicle_type="auto_rickshaw", confidence=0.88, bbox=(60, 60, 90, 100), speed_kmh=18.0),
            ]

            metrics = {
                "APP_NORTH": ApproachQueueMetrics(
                    approach_id="APP_NORTH",
                    vehicle_counts={"car": 1, "auto_rickshaw": 1},
                    total_pcu=1.8,
                    queue_length_meters=15.0,
                    average_speed_kmh=21.0,
                )
            }

            # Log frame
            writer.log_frame(frame_idx=1, timestamp=1723800000.0, tracked_vehicles=vehicles, approach_metrics=metrics)

            # Log window
            window_data = {
                "APP_NORTH": {
                    "approach_id": "APP_NORTH",
                    "timestamp": 1723800003.0,
                    "total_pcu": 1.8,
                    "queue_length_meters": 15.0,
                    "average_speed_kmh": 21.0,
                    "vehicle_counts": {"car": 1, "auto_rickshaw": 1},
                    "emergency_vehicle_detected": False,
                    "emergency_vehicle_count": 0,
                }
            }
            writer.log_window(timestamp=1723800003.0, window_metrics=window_data)

            # Verify files
            self.assertTrue(writer.frames_json_path.exists())
            self.assertTrue(writer.window_json_path.exists())
            self.assertTrue(writer.window_csv_path.exists())

            with open(writer.frames_json_path, "r", encoding="utf-8") as f:
                line = f.readline()
                frame_obj = json.loads(line)
                self.assertEqual(frame_obj["junction_id"], "TEST_JUNCTION")
                self.assertEqual(len(frame_obj["vehicles"]), 2)

            with open(writer.window_json_path, "r", encoding="utf-8") as f:
                line = f.readline()
                win_obj = json.loads(line)
                self.assertIn("APP_NORTH", win_obj["approaches"])


if __name__ == "__main__":
    unittest.main()
