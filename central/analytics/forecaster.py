"""
Short-Horizon Traffic Congestion Forecaster (10-30 Minutes Ahead).

Uses Double Exponential Smoothing (Holt's Linear Trend with Damped Extrapolation)
to forecast approach vehicle counts, queue lengths, and PCU pressure 10-30 minutes ahead.

Strictly driven by real tracked telemetry time-series without relying on
unvalidated deep LSTM architectures or synthetic historical data.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class ApproachForecastResult:
    approach_id: str
    current_pcu: float
    current_count: int
    current_queue_meters: float
    forecast_10min_pcu: float
    forecast_15min_pcu: float
    forecast_30min_pcu: float
    forecast_10min_queue_m: float
    forecast_30min_queue_m: float
    trend_direction: str  # "RAPID_INCREASE", "INCREASING", "STABLE", "DECREASING", "RAPID_DECREASE"
    trend_slope_pcu_per_min: float
    forecast_trajectory_pcu: List[float]


class CongestionForecaster:
    """
    Predicts near-future (10-30 min) queue lengths, counts, and PCU pressures.
    """

    def __init__(
        self,
        alpha: float = 0.35,  # Level smoothing factor
        beta: float = 0.15,   # Trend smoothing factor
        damping_phi: float = 0.95,  # Trend damping factor to prevent runaway extrapolation
        sample_interval_sec: float = 3.0,
        max_history_len: int = 120,  # ~6-10 minutes rolling buffer
    ):
        self.alpha = alpha
        self.beta = beta
        self.phi = damping_phi
        self.sample_interval_sec = sample_interval_sec
        self.max_history_len = max_history_len

        self.pcu_history: Dict[str, List[float]] = {}
        self.count_history: Dict[str, List[int]] = {}
        self.queue_history: Dict[str, List[float]] = {}

    def update_sample(
        self,
        approach_id: str,
        total_pcu: float,
        vehicle_count: int,
        queue_length_meters: float,
    ):
        """Append new telemetry reading to rolling history."""
        if approach_id not in self.pcu_history:
            self.pcu_history[approach_id] = []
            self.count_history[approach_id] = []
            self.queue_history[approach_id] = []

        self.pcu_history[approach_id].append(float(total_pcu))
        self.count_history[approach_id].append(int(vehicle_count))
        self.queue_history[approach_id].append(float(queue_length_meters))

        if len(self.pcu_history[approach_id]) > self.max_history_len:
            self.pcu_history[approach_id].pop(0)
            self.count_history[approach_id].pop(0)
            self.queue_history[approach_id].pop(0)

    def compute_holt_trend(self, series: List[float]) -> Tuple[float, float]:
        """Compute current smoothed level (L) and trend (T) using Holt's Linear method."""
        if len(series) < 2:
            val = series[-1] if series else 0.0
            return val, 0.0

        level = series[0]
        trend = series[1] - series[0]

        for val in series[1:]:
            last_level = level
            level = self.alpha * val + (1.0 - self.alpha) * (level + self.phi * trend)
            trend = self.beta * (level - last_level) + (1.0 - self.beta) * self.phi * trend

        return level, trend

    def forecast_approach(
        self,
        approach_id: str,
        horizon_minutes: int = 30,
    ) -> ApproachForecastResult:
        """
        Generate multi-horizon forecast (10, 15, 30 min) for an approach.
        """
        pcu_series = self.pcu_history.get(approach_id, [])
        count_series = self.count_history.get(approach_id, [])
        queue_series = self.queue_history.get(approach_id, [])

        curr_pcu = pcu_series[-1] if pcu_series else 0.0
        curr_count = count_series[-1] if count_series else 0
        curr_queue = queue_series[-1] if queue_series else 0.0

        if len(pcu_series) < 3:
            # Insufficient samples: baseline persistence forecast
            return ApproachForecastResult(
                approach_id=approach_id,
                current_pcu=round(curr_pcu, 2),
                current_count=curr_count,
                current_queue_meters=round(curr_queue, 1),
                forecast_10min_pcu=round(curr_pcu, 2),
                forecast_15min_pcu=round(curr_pcu, 2),
                forecast_30min_pcu=round(curr_pcu, 2),
                forecast_10min_queue_m=round(curr_queue, 1),
                forecast_30min_queue_m=round(curr_queue, 1),
                trend_direction="STABLE",
                trend_slope_pcu_per_min=0.0,
                forecast_trajectory_pcu=[round(curr_pcu, 2)] * 6,
            )

        level, trend = self.compute_holt_trend(pcu_series)

        # Steps per minute: 60s / 3s = 20 steps per minute
        steps_per_min = 60.0 / self.sample_interval_sec

        # Trend slope per minute
        trend_per_min = trend * steps_per_min

        # Generate trajectory at 5-minute increments (5, 10, 15, 20, 25, 30 min)
        # Apply gentle minute-level damping (phi=0.98 per minute) to project future traffic
        trajectory: List[float] = []
        phi_min = 0.98
        for m in range(5, horizon_minutes + 1, 5):
            damped_sum = sum(phi_min ** i for i in range(1, m + 1))
            pred = max(0.0, level + damped_sum * trend_per_min)
            trajectory.append(round(pred, 2))

        f_10min_pcu = trajectory[1] if len(trajectory) > 1 else round(curr_pcu, 2)
        f_15min_pcu = trajectory[2] if len(trajectory) > 2 else round(curr_pcu, 2)
        f_30min_pcu = trajectory[-1] if trajectory else round(curr_pcu, 2)

        # Queue length approximation (~6.0m per PCU under congestion)
        f_10min_queue_m = round(f_10min_pcu * 6.0, 1)
        f_30min_queue_m = round(f_30min_pcu * 6.0, 1)

        # Classify trend direction
        if trend_per_min > 1.5:
            trend_dir = "RAPID_INCREASE"
        elif trend_per_min > 0.3:
            trend_dir = "INCREASING"
        elif trend_per_min < -1.5:
            trend_dir = "RAPID_DECREASE"
        elif trend_per_min < -0.3:
            trend_dir = "DECREASING"
        else:
            trend_dir = "STABLE"

        return ApproachForecastResult(
            approach_id=approach_id,
            current_pcu=round(curr_pcu, 2),
            current_count=curr_count,
            current_queue_meters=round(curr_queue, 1),
            forecast_10min_pcu=f_10min_pcu,
            forecast_15min_pcu=f_15min_pcu,
            forecast_30min_pcu=f_30min_pcu,
            forecast_10min_queue_m=f_10min_queue_m,
            forecast_30min_queue_m=f_30min_queue_m,
            trend_direction=trend_dir,
            trend_slope_pcu_per_min=round(trend_per_min, 2),
            forecast_trajectory_pcu=trajectory,
        )


# Backward-compatible alias
QueueForecaster = CongestionForecaster
