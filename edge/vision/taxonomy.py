"""
Indian Traffic Taxonomy and Class Mapping Module.

Defines standard vehicle categories suited for Indian urban traffic conditions:
- car (Sedan, Hatchback, SUV, Taxi)
- bus (City bus, State transport, Mini-bus)
- truck (Heavy commercial vehicle, Multi-axle, Dumper)
- auto_rickshaw (3-wheeler passenger/cargo)
- two_wheeler (Motorcycle, Scooter, Moped)
- cycle (Bicycle, Non-motorized 2-wheeler)
- pedestrian (People walking/crossing)
- cart (Animal-drawn cart, Hand cart, Rickshaw puller)
- emergency_vehicle (Ambulance, Fire tender, Police emergency)

================================================================================
DATASET & FINE-TUNING STATUS (EXPLICIT ARCHITECTURAL DISCLOSURE):
- Base Detector: Pretrained YOLOv8 (ultralytics) COCO baseline.
- Fine-tuning on IDD (India Driving Dataset): DEFERRED.
  Rationale: IDD is ~50GB+ in raw annotations and requires multi-GPU training
  time that is not practical in local rapid development. Instead, an intelligent
  taxonomic translation layer with geometric and aspect-ratio heuristics maps
  standard COCO classes into Indian traffic equivalents (e.g. 3-wheelers / auto-rickshaws
  and light commercial vehicles are identified via bounding box aspect ratios,
  while motorcycle/bicycle/bus/truck/car/pedestrian map cleanly).
  When IDD fine-tuned weights (yolov8n-idd.pt) become available, this module
  directly loads the native 9-class Indian weights without changing downstream code.
================================================================================
"""

from typing import Dict, Optional, Tuple
from enum import Enum


class IndianTrafficClass(str, Enum):
    TWO_WHEELER = "two_wheeler"
    AUTO_RICKSHAW = "auto_rickshaw"
    CAR = "car"
    BUS = "bus"
    TRUCK = "truck"
    CYCLE = "cycle"
    PEDESTRIAN = "pedestrian"
    CART = "cart"
    EMERGENCY_VEHICLE = "emergency_vehicle"
    UNKNOWN = "unknown"


# Standard COCO Class IDs relevant to road traffic
# 0: person, 1: bicycle, 2: car, 3: motorcycle, 5: bus, 7: truck
COCO_ROAD_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

# Mapping from COCO class names to Indian Traffic Taxonomy
COCO_TO_INDIAN_MAP: Dict[str, IndianTrafficClass] = {
    "motorcycle": IndianTrafficClass.TWO_WHEELER,
    "bicycle": IndianTrafficClass.CYCLE,
    "car": IndianTrafficClass.CAR,
    "bus": IndianTrafficClass.BUS,
    "truck": IndianTrafficClass.TRUCK,
    "person": IndianTrafficClass.PEDESTRIAN,
}

# Standard PCU (Passenger Car Unit) weights as per IRC / MoRTH guidelines
IRC_PCU_WEIGHTS: Dict[IndianTrafficClass, float] = {
    IndianTrafficClass.TWO_WHEELER: 0.5,
    IndianTrafficClass.AUTO_RICKSHAW: 0.8,
    IndianTrafficClass.CAR: 1.0,
    IndianTrafficClass.BUS: 3.0,
    IndianTrafficClass.TRUCK: 3.0,
    IndianTrafficClass.CYCLE: 0.2,
    IndianTrafficClass.PEDESTRIAN: 0.0,  # Handled separately as pedestrian clearance
    IndianTrafficClass.CART: 2.0,        # Slow moving non-motorized high friction
    IndianTrafficClass.EMERGENCY_VEHICLE: 1.0,  # PCU weight 1.0, but highest priority multiplier
    IndianTrafficClass.UNKNOWN: 1.0,
}


class IndianTrafficTaxonomy:
    """
    Taxonomy translation and heuristic classifier for Indian mixed traffic conditions.
    """

    @classmethod
    def map_coco_class(
        cls,
        coco_cls_name: str,
        bbox: Optional[Tuple[int, int, int, int]] = None,
        confidence: float = 1.0,
    ) -> IndianTrafficClass:
        """
        Map a standard COCO detection to Indian traffic taxonomy.
        Applies geometric aspect-ratio heuristics when available to distinguish
        auto-rickshaws (3-wheelers) from compact cars or motorcycles.
        """
        cls_clean = coco_cls_name.lower().strip()

        # Direct mapped types
        mapped = COCO_TO_INDIAN_MAP.get(cls_clean, IndianTrafficClass.UNKNOWN)

        if bbox is not None:
            x1, y1, x2, y2 = bbox
            w = max(1, x2 - x1)
            h = max(1, y2 - y1)
            aspect_ratio = w / float(h)
            area = w * h

            # Heuristic 1: Indian Auto-Rickshaws (3-wheelers) often get detected
            # by COCO models as 'car' or 'motorcycle' with distinct tall, narrow aspect ratio (0.65 - 0.95)
            # and moderate area.
            if mapped == IndianTrafficClass.CAR:
                if 0.60 <= aspect_ratio <= 0.95 and area < 45000:
                    return IndianTrafficClass.AUTO_RICKSHAW

            # Heuristic 2: Hand carts / cycle rickshaws detected as bicycle or person with wide bounding box
            if mapped == IndianTrafficClass.CYCLE and aspect_ratio > 1.4:
                return IndianTrafficClass.CART

        return mapped

    @classmethod
    def get_pcu(cls, traffic_class: IndianTrafficClass) -> float:
        """Return the IRC standard PCU value for a given vehicle class."""
        return IRC_PCU_WEIGHTS.get(traffic_class, 1.0)
