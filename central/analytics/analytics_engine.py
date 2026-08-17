"""
GATI Analytics Engine Orchestrator.

Combines all three real-data-driven analytics pipelines:
1. CongestionForecaster (10-30 min queue & count forecasting)
2. IncidentDetector (Real-time stalled vehicle & gridlock detection)
3. LiveRiskIndicator (Speed variance, hard braking & near-miss surrogate safety)
"""

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from central.analytics.forecaster import CongestionForecaster, ApproachForecastResult
from central.analytics.incident_detector import IncidentDetector, IncidentAlert
from central.analytics.live_risk_indicator import LiveRiskIndicator, LiveApproachRisk
from edge.vision import ApproachQueueMetrics, TrackedVehicle

logger = logging.getLogger("central.analytics_engine")


@dataclass
class AnalyticsBatchResult:
    timestamp: float
    forecasts: Dict[str, ApproachForecastResult]
    active_incidents: List[IncidentAlert]
    approach_risks: Dict[str, LiveApproachRisk]


class AnalyticsEngine:
    """
    Unified analytics processor consuming real detection/tracking telemetry streams.
    """

    def __init__(
        self,
        stalled_threshold_sec: float = 20.0,
        sample_interval_sec: float = 3.0,
        meters_per_pixel: float = 0.05,
    ):
        self.forecaster = CongestionForecaster(sample_interval_sec=sample_interval_sec)
        self.incident_detector = IncidentDetector(
            stalled_threshold_sec=stalled_threshold_sec,
            meters_per_pixel=meters_per_pixel,
        )
        self.risk_indicator = LiveRiskIndicator(meters_per_pixel=meters_per_pixel)

    def process_telemetry_step(
        self,
        timestamp: float,
        approach_metrics: Dict[str, ApproachQueueMetrics],
        tracked_vehicles: Optional[List[TrackedVehicle]] = None,
        vehicle_approach_map: Optional[Dict[str, List[TrackedVehicle]]] = None,
    ) -> AnalyticsBatchResult:
        """
        Process a single telemetry time step across all approaches.
        """
        vehicles = tracked_vehicles or []
        app_v_map = vehicle_approach_map or {}

        # 1. Update Short-Horizon Congestion Forecaster
        forecasts: Dict[str, ApproachForecastResult] = {}
        for app_id, metric in approach_metrics.items():
            total_count = sum(metric.vehicle_counts.values()) if metric.vehicle_counts else 0
            self.forecaster.update_sample(
                approach_id=app_id,
                total_pcu=metric.total_pcu,
                vehicle_count=total_count,
                queue_length_meters=metric.queue_length_meters,
            )
            forecasts[app_id] = self.forecaster.forecast_approach(app_id, horizon_minutes=30)

        # 2. Update Incident & Stalled Vehicle Detector
        self.incident_detector.update_frame(
            tracked_vehicles=vehicles,
            timestamp=timestamp,
        )
        active_incidents = self.incident_detector.get_active_incidents()

        # 3. Update Live Risk Indicator per Approach
        approach_risks: Dict[str, LiveApproachRisk] = {}
        for app_id in approach_metrics.keys():
            app_vehicles = app_v_map.get(app_id, vehicles)
            approach_risks[app_id] = self.risk_indicator.analyze_approach_frame(
                approach_id=app_id,
                tracked_vehicles=app_vehicles,
                timestamp=timestamp,
            )

        return AnalyticsBatchResult(
            timestamp=timestamp,
            forecasts=forecasts,
            active_incidents=active_incidents,
            approach_risks=approach_risks,
        )
