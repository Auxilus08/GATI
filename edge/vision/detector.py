"""
GATI Edge YOLOv8 Detector and Approach-Based Spatial Queue Engine.

Designed for Indian urban junction geometry:
- Operates on full APPROACH regions (lane-free spatial tracking).
- Accommodates mixed traffic where vehicles weave, filter, and queue without lane discipline.
- Calculates approach-level counts by class, queue lengths, and speeds.
- Supports both PyTorch (.pt) and quantized ONNX Runtime (.onnx) backends.
"""

from dataclasses import dataclass, field
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import cv2
import numpy as np

from edge.vision import ApproachQueueMetrics, TrackedVehicle
from edge.vision.pcu_engine import PCUEngine
from edge.vision.taxonomy import IndianTrafficClass, IndianTrafficTaxonomy
from edge.vision.tracker import ByteTrackerManager, TrackState
from config.settings import PCUWeights

logger = logging.getLogger(__name__)


@dataclass
class ApproachROI:
    """Defines the spatial boundary and calibration for an approach."""
    approach_id: str
    name: str
    polygon: np.ndarray  # Shape (N, 2) array of (x, y) vertices
    stopline_point: Tuple[int, int]  # (x, y) coordinates of stopline anchor
    meters_per_pixel: float = 0.05
    max_queue_meters: float = 150.0


def point_in_polygon(point: Tuple[float, float], polygon: np.ndarray) -> bool:
    """Test if 2D point (x, y) lies inside polygon using cv2.pointPolygonTest."""
    return cv2.pointPolygonTest(polygon.astype(np.int32), (float(point[0]), float(point[1])), False) >= 0


class YOLODetector:
    """
    YOLOv8 Edge Traffic Detector and Approach-Based Queue Estimator.
    """

    def __init__(
        self,
        model_path: Union[str, Path] = "yolov8n.pt",
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        device: str = "cpu",
        pcu_weights: Optional[PCUWeights] = None,
        use_onnx: bool = False,
    ):
        self.model_path = str(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.use_onnx = use_onnx or self.model_path.endswith(".onnx")
        self.pcu_engine = PCUEngine(pcu_weights or PCUWeights())
        self.tracker_manager = ByteTrackerManager()
        self.approaches: Dict[str, ApproachROI] = {}

        self.model = None
        self.onnx_session = None
        self._init_model()

    def _init_model(self):
        """Initialize YOLO model via Ultralytics or ONNX Runtime."""
        if self.use_onnx:
            try:
                import onnxruntime as ort
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if self.device != "cpu" else ["CPUExecutionProvider"]
                self.onnx_session = ort.InferenceSession(self.model_path, providers=providers)
                logger.info(f"Loaded ONNX model: {self.model_path} with providers: {self.onnx_session.get_providers()}")
            except ImportError:
                logger.warning("onnxruntime not installed. Falling back to standard Ultralytics YOLO loader.")
                self._init_ultralytics()
        else:
            self._init_ultralytics()

    def _init_ultralytics(self):
        """Initialize Ultralytics YOLOv8 instance."""
        from ultralytics import YOLO
        try:
            self.model = YOLO(self.model_path)
            logger.info(f"Loaded YOLOv8 model from {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model from {self.model_path}: {e}")
            raise

    def register_approach(
        self,
        approach_id: str,
        name: str,
        polygon_points: List[Tuple[int, int]],
        stopline_point: Tuple[int, int],
        meters_per_pixel: float = 0.05,
        max_queue_meters: float = 150.0,
    ):
        """Register an approach polygon for spatial attribution."""
        poly_arr = np.array(polygon_points, dtype=np.int32)
        self.approaches[approach_id] = ApproachROI(
            approach_id=approach_id,
            name=name,
            polygon=poly_arr,
            stopline_point=stopline_point,
            meters_per_pixel=meters_per_pixel,
            max_queue_meters=max_queue_meters,
        )

    def find_matching_approach(self, center_point: Tuple[float, float]) -> Optional[str]:
        """Find which approach polygon contains the vehicle centroid."""
        for app_id, app_roi in self.approaches.items():
            if point_in_polygon(center_point, app_roi.polygon):
                return app_id
        return None

    def process_frame(
        self,
        frame: np.ndarray,
        timestamp: float,
        run_tracking: bool = True,
    ) -> Tuple[List[TrackedVehicle], Dict[str, ApproachQueueMetrics]]:
        """
        Run inference on a single frame, track vehicles with ByteTrack,
        and calculate approach-level queue lengths, counts, and speeds.
        """
        h, w = frame.shape[:2]

        # Default fallback approach if none explicitly configured
        if not self.approaches:
            # Register a full-frame default approach
            self.register_approach(
                approach_id="APP_MAIN",
                name="Main Approach",
                polygon_points=[(0, 0), (w, 0), (w, h), (0, h)],
                stopline_point=(w // 2, h - 20),
                meters_per_pixel=0.05,
            )

        tracked_vehicles: List[TrackedVehicle] = []

        if self.model is not None:
            # Run tracking via Ultralytics ByteTrack integration
            if run_tracking:
                results = self.model.track(
                    source=frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    conf=self.conf_threshold,
                    iou=self.iou_threshold,
                    device=self.device,
                    verbose=False,
                )
            else:
                results = self.model(
                    source=frame,
                    conf=self.conf_threshold,
                    iou=self.iou_threshold,
                    device=self.device,
                    verbose=False,
                )

            res = results[0]
            boxes = res.boxes

            if boxes is not None and len(boxes) > 0:
                for idx in range(len(boxes)):
                    box = boxes[idx]
                    xyxy = box.xyxy[0].cpu().numpy().astype(int)
                    conf = float(box.conf[0].cpu().numpy())
                    cls_id = int(box.cls[0].cpu().numpy())
                    raw_cls_name = self.model.names.get(cls_id, "unknown")

                    track_id = int(box.id[0].cpu().numpy()) if (box.id is not None) else (idx + 1)

                    bbox_tuple = (int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3]))
                    cx = (bbox_tuple[0] + bbox_tuple[2]) / 2.0
                    cy = (bbox_tuple[1] + bbox_tuple[3]) / 2.0

                    # Map COCO detection to Indian Traffic Taxonomy
                    indian_class = IndianTrafficTaxonomy.map_coco_class(
                        coco_cls_name=raw_cls_name,
                        bbox=bbox_tuple,
                        confidence=conf,
                    )

                    # Only process valid road users
                    if indian_class == IndianTrafficClass.UNKNOWN:
                        continue

                    # Spatial approach matching
                    app_id = self.find_matching_approach((cx, cy))
                    m_px = self.approaches[app_id].meters_per_pixel if app_id else 0.05

                    # Update persistent ByteTrack tracking and speed
                    track_state = self.tracker_manager.update_track(
                        track_id=track_id,
                        vehicle_type=indian_class.value,
                        confidence=conf,
                        bbox=bbox_tuple,
                        timestamp=timestamp,
                        approach_id=app_id,
                        meters_per_pixel=m_px,
                    )

                    tracked_vehicles.append(
                        TrackedVehicle(
                            track_id=track_id,
                            vehicle_type=indian_class.value,
                            confidence=round(conf, 2),
                            bbox=bbox_tuple,
                            speed_kmh=track_state.smoothed_speed_kmh,
                            is_emergency=(indian_class == IndianTrafficClass.EMERGENCY_VEHICLE),
                        )
                    )

        self.tracker_manager.purge_lost_tracks(timestamp)

        # Compute per-approach metrics
        approach_metrics = self.compute_approach_metrics(tracked_vehicles)
        return tracked_vehicles, approach_metrics

    def compute_approach_metrics(
        self, tracked_vehicles: List[TrackedVehicle]
    ) -> Dict[str, ApproachQueueMetrics]:
        """
        Aggregates metrics for each approach:
        - Class counts
        - Total PCU
        - Queue length in meters (spatial extent of stopped/slow traffic along approach)
        - Average approach velocity
        """
        # Group tracked vehicles by approach
        approach_groups: Dict[str, List[TrackedVehicle]] = {
            app_id: [] for app_id in self.approaches.keys()
        }

        for v in tracked_vehicles:
            # Look up approach from track manager
            tstate = self.tracker_manager.tracks.get(v.track_id)
            if tstate and tstate.approach_id and tstate.approach_id in approach_groups:
                approach_groups[tstate.approach_id].append(v)
            else:
                # Assign to closest approach by center point
                cx = (v.bbox[0] + v.bbox[2]) / 2.0
                cy = (v.bbox[1] + v.bbox[3]) / 2.0
                app_id = self.find_matching_approach((cx, cy))
                if app_id and app_id in approach_groups:
                    approach_groups[app_id].append(v)
                elif self.approaches:
                    # Fallback to first approach
                    first_app = next(iter(self.approaches.keys()))
                    approach_groups[first_app].append(v)

        result: Dict[str, ApproachQueueMetrics] = {}

        for app_id, v_list in approach_groups.items():
            app_roi = self.approaches[app_id]
            speeds = [v.speed_kmh for v in v_list if v.speed_kmh is not None]
            avg_speed = float(np.mean(speeds)) if speeds else 0.0

            # Base counts & PCU from PCUEngine
            metric = self.pcu_engine.calculate_approach_metrics(
                approach_id=app_id,
                tracked_vehicles=v_list,
                avg_speed_kmh=avg_speed,
            )

            # Spatial Queue Length Calculation:
            # Measure physical distance from stopline to the furthest stationary/slow vehicle (< 10 km/h)
            stop_x, stop_y = app_roi.stopline_point
            max_queue_dist_m = 0.0

            queued_vehicles = [
                v for v in v_list
                if (v.speed_kmh is not None and v.speed_kmh < 10.0)
            ]

            if queued_vehicles:
                for qv in queued_vehicles:
                    vcx = (qv.bbox[0] + qv.bbox[2]) / 2.0
                    vcy = (qv.bbox[1] + qv.bbox[3]) / 2.0
                    dist_px = math.sqrt((vcx - stop_x) ** 2 + (vcy - stop_y) ** 2)
                    dist_m = dist_px * app_roi.meters_per_pixel
                    if dist_m > max_queue_dist_m:
                        max_queue_dist_m = dist_m

                # Smoothly blend spatial queue with PCU density estimate (e.g. 6m per PCU in jam)
                pcu_queue_m = metric.total_pcu * 6.0
                effective_queue_m = max(max_queue_dist_m, pcu_queue_m * 0.7)
                metric.queue_length_meters = round(min(effective_queue_m, app_roi.max_queue_meters), 1)
            else:
                metric.queue_length_meters = 0.0

            result[app_id] = metric

        return result
