"""
GATI Video Processing Pipeline & Structured Telemetry Logger.

Processes live RTSP CCTV streams or recorded traffic video files:
- Runs YOLOv8 + ByteTrack on frames
- Attributes detections to Approach ROIs
- Calculates per-frame tracks and per-window approach metrics
- Emits structured telemetry logs (JSON & CSV) consumed by signal controllers and central servers
"""

import csv
import json
import logging
from pathlib import Path
import time
from typing import Callable, Dict, Generator, List, Optional, Tuple, Union
import cv2
import numpy as np

from edge.vision import ApproachQueueMetrics, TrackedVehicle
from edge.vision.detector import ApproachROI, YOLODetector
from config.settings import JunctionConfig, PCUWeights

logger = logging.getLogger("edge.video_pipeline")


class TrafficVideoPipeline:
    """
    End-to-end video inference and approach metrics aggregation pipeline.
    """

    def __init__(
        self,
        detector: YOLODetector,
        junction_config: Optional[JunctionConfig] = None,
        window_duration_sec: float = 3.0,
        fps_target: Optional[float] = None,
    ):
        self.detector = detector
        self.junction_config = junction_config
        self.window_duration_sec = window_duration_sec
        self.fps_target = fps_target

        # Window aggregation buffer
        self.current_window_start = time.time()
        self.window_samples: List[Dict[str, ApproachQueueMetrics]] = []
        self.window_vehicle_records: List[TrackedVehicle] = []

    def setup_approaches_from_junction_config(
        self,
        frame_width: int,
        frame_height: int,
        junction_config: JunctionConfig,
    ):
        """
        Auto-generate default geometric approach ROIs for a junction if custom polygons aren't specified.
        Divides the frame into standard directional quadrants (North, South, East, West).
        """
        w, h = frame_width, frame_height
        cx, cy = w // 2, h // 2

        quadrant_polygons = {
            "APP_NORTH": [(0, 0), (w, 0), (cx + 50, cy), (cx - 50, cy)],
            "APP_SOUTH": [(0, h), (w, h), (cx + 50, cy), (cx - 50, cy)],
            "APP_EAST": [(w, 0), (w, h), (cx, cy + 50), (cx, cy - 50)],
            "APP_WEST": [(0, 0), (0, h), (cx, cy + 50), (cx, cy - 50)],
        }

        stoplines = {
            "APP_NORTH": (cx, cy - 20),
            "APP_SOUTH": (cx, cy + 20),
            "APP_EAST": (cx + 20, cy),
            "APP_WEST": (cx - 20, cy),
        }

        for app in junction_config.approaches:
            poly = quadrant_polygons.get(app.id, [(0, 0), (w, 0), (w, h), (0, h)])
            stop = stoplines.get(app.id, (cx, cy))
            self.detector.register_approach(
                approach_id=app.id,
                name=app.name,
                polygon_points=poly,
                stopline_point=stop,
                meters_per_pixel=0.05,
            )

    def process_frame(
        self,
        frame: np.ndarray,
        frame_idx: int,
        timestamp: Optional[float] = None,
    ) -> Tuple[List[TrackedVehicle], Dict[str, ApproachQueueMetrics]]:
        """Process a single video frame."""
        ts = timestamp if timestamp is not None else time.time()
        tracked_vehicles, approach_metrics = self.detector.process_frame(frame, timestamp=ts)
        self.window_samples.append(approach_metrics)
        self.window_vehicle_records.extend(tracked_vehicles)
        return tracked_vehicles, approach_metrics

    def get_window_aggregation(
        self, window_end_timestamp: float
    ) -> Dict[str, Dict]:
        """
        Aggregate metrics collected over the time window (e.g. 3-second cycle).
        Returns structured dictionary per approach.
        """
        if not self.window_samples:
            return {}

        approach_aggregated: Dict[str, Dict] = {}
        all_approach_ids = set()
        for sample in self.window_samples:
            all_approach_ids.update(sample.keys())

        for app_id in all_approach_ids:
            samples = [s[app_id] for s in self.window_samples if app_id in s]
            if not samples:
                continue

            # Compute average PCU, max queue length, average speed
            avg_pcu = float(np.mean([s.total_pcu for s in samples]))
            max_queue = float(np.max([s.queue_length_meters for s in samples]))
            avg_speeds = [s.average_speed_kmh for s in samples if s.average_speed_kmh > 0]
            mean_speed = float(np.mean(avg_speeds)) if avg_speeds else 0.0
            emergency_detected = any(s.emergency_vehicle_detected for s in samples)
            total_emergency_count = sum(s.emergency_vehicle_count for s in samples)

            # Cumulative counts by class
            class_counts: Dict[str, int] = {}
            for s in samples:
                for cls_name, count in s.vehicle_counts.items():
                    class_counts[cls_name] = max(class_counts.get(cls_name, 0), count)

            approach_aggregated[app_id] = {
                "approach_id": app_id,
                "timestamp": round(window_end_timestamp, 2),
                "total_pcu": round(avg_pcu, 2),
                "queue_length_meters": round(max_queue, 1),
                "average_speed_kmh": round(mean_speed, 1),
                "vehicle_counts": class_counts,
                "emergency_vehicle_detected": emergency_detected,
                "emergency_vehicle_count": total_emergency_count,
            }

        # Reset window buffer
        self.window_samples.clear()
        self.window_vehicle_records.clear()
        self.current_window_start = window_end_timestamp

        return approach_aggregated

    def render_overlay(
        self,
        frame: np.ndarray,
        tracked_vehicles: List[TrackedVehicle],
        approach_metrics: Dict[str, ApproachQueueMetrics],
    ) -> np.ndarray:
        """
        Draw bounding boxes, track labels, speeds, and approach queue summaries on frame.
        """
        vis_frame = frame.copy()

        # 1. Draw Approach Polygons & Stoplines
        for app_id, app_roi in self.detector.approaches.items():
            cv2.polylines(vis_frame, [app_roi.polygon], isClosed=True, color=(100, 200, 100), thickness=2)
            cv2.circle(vis_frame, app_roi.stopline_point, radius=5, color=(0, 0, 255), thickness=-1)

        # 2. Draw Vehicle Bounding Boxes & Speeds
        class_colors = {
            "two_wheeler": (255, 150, 0),
            "auto_rickshaw": (0, 200, 255),
            "car": (0, 255, 0),
            "bus": (255, 0, 100),
            "truck": (0, 100, 255),
            "cycle": (200, 200, 0),
            "pedestrian": (255, 255, 255),
            "cart": (180, 100, 50),
            "emergency_vehicle": (0, 0, 255),
        }

        for v in tracked_vehicles:
            x1, y1, x2, y2 = v.bbox
            color = class_colors.get(v.vehicle_type, (200, 200, 200))
            if v.is_emergency:
                color = (0, 0, 255)

            cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 2)

            speed_text = f"{v.speed_kmh:.0f} km/h" if v.speed_kmh is not None else ""
            label = f"#{v.track_id} {v.vehicle_type} {speed_text}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(vis_frame, (x1, max(0, y1 - th - 6)), (x1 + tw + 4, y1), color, -1)
            cv2.putText(
                vis_frame,
                label,
                (x1 + 2, max(12, y1 - 3)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

        # 3. Draw On-Screen Metrics HUD (Top-Left)
        y_offset = 25
        cv2.rectangle(vis_frame, (10, 10), (320, 20 + len(approach_metrics) * 35), (20, 20, 20), -1)
        for app_id, metric in approach_metrics.items():
            hud_text = f"{app_id}: PCU={metric.total_pcu:.1f} | Q={metric.queue_length_meters:.0f}m | {metric.average_speed_kmh:.0f} km/h"
            cv2.putText(
                vis_frame,
                hud_text,
                (15, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 200),
                1,
                cv2.LINE_AA,
            )
            y_offset += 25

        return vis_frame


class StructuredTelemetryWriter:
    """
    Writes structured frame and window metrics to JSON and CSV logs.
    """

    def __init__(self, output_dir: Union[str, Path], junction_id: str = "NGP_J01_SITABULDI"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.junction_id = junction_id

        self.frames_json_path = self.output_dir / "vision_frames.jsonl"
        self.window_json_path = self.output_dir / "vision_windows.jsonl"
        self.window_csv_path = self.output_dir / "vision_windows.csv"

        self._init_csv()

    def _init_csv(self):
        """Initialize CSV header for window telemetry."""
        if not self.window_csv_path.exists():
            with open(self.window_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "junction_id",
                    "timestamp",
                    "approach_id",
                    "total_pcu",
                    "queue_length_meters",
                    "average_speed_kmh",
                    "count_two_wheeler",
                    "count_auto_rickshaw",
                    "count_car",
                    "count_bus",
                    "count_truck",
                    "count_cycle",
                    "count_pedestrian",
                    "count_cart",
                    "emergency_detected",
                    "emergency_count",
                ])

    def log_frame(
        self,
        frame_idx: int,
        timestamp: float,
        tracked_vehicles: List[TrackedVehicle],
        approach_metrics: Dict[str, ApproachQueueMetrics],
    ):
        """Log per-frame detections and tracks into JSONL."""
        frame_record = {
            "junction_id": self.junction_id,
            "frame_idx": frame_idx,
            "timestamp": round(timestamp, 3),
            "vehicle_count": len(tracked_vehicles),
            "vehicles": [
                {
                    "track_id": v.track_id,
                    "class": v.vehicle_type,
                    "confidence": v.confidence,
                    "bbox": list(v.bbox),
                    "speed_kmh": v.speed_kmh,
                    "is_emergency": v.is_emergency,
                }
                for v in tracked_vehicles
            ],
            "approaches": {
                app_id: {
                    "total_pcu": m.total_pcu,
                    "queue_length_m": m.queue_length_meters,
                    "avg_speed_kmh": m.average_speed_kmh,
                    "emergency": m.emergency_vehicle_detected,
                }
                for app_id, m in approach_metrics.items()
            },
        }

        with open(self.frames_json_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(frame_record) + "\n")

    def log_window(self, timestamp: float, window_metrics: Dict[str, Dict]):
        """Log aggregated time-window metrics into JSONL and CSV."""
        if not window_metrics:
            return

        window_record = {
            "junction_id": self.junction_id,
            "timestamp": round(timestamp, 3),
            "approaches": window_metrics,
        }

        # Write to JSONL
        with open(self.window_json_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(window_record) + "\n")

        # Write to CSV
        with open(self.window_csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for app_id, data in window_metrics.items():
                counts = data.get("vehicle_counts", {})
                writer.writerow([
                    self.junction_id,
                    data.get("timestamp", timestamp),
                    app_id,
                    data.get("total_pcu", 0.0),
                    data.get("queue_length_meters", 0.0),
                    data.get("average_speed_kmh", 0.0),
                    counts.get("two_wheeler", 0),
                    counts.get("auto_rickshaw", 0),
                    counts.get("car", 0),
                    counts.get("bus", 0),
                    counts.get("truck", 0),
                    counts.get("cycle", 0),
                    counts.get("pedestrian", 0),
                    counts.get("cart", 0),
                    data.get("emergency_vehicle_detected", False),
                    data.get("emergency_vehicle_count", 0),
                ])
