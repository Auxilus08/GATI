"""
Traffic Queue & Congestion Forecaster.
Uses Double Exponential Smoothing (Holt's Linear Trend) to predict near-future (5-15 min) PCU queues.
Transparent, deterministic baseline that works without requiring massive deep neural training pipelines.
"""
from typing import List, Dict
import numpy as np


class QueueForecaster:
    """Short-term PCU queue predictor using Holt's Linear Exponential Smoothing."""

    def __init__(self, alpha: float = 0.3, beta: float = 0.1):
        self.alpha = alpha  # Level smoothing factor
        self.beta = beta    # Trend smoothing factor
        self.history: Dict[str, List[float]] = {}  # approach_id -> historical PCU series

    def update(self, approach_id: str, pcu_value: float):
        """Append new reading to history (capped at last 120 readings / ~6-10 minutes)."""
        if approach_id not in self.history:
            self.history[approach_id] = []
        self.history[approach_id].append(float(pcu_value))
        if len(self.history[approach_id]) > 120:
            self.history[approach_id].pop(0)

    def forecast(self, approach_id: str, steps_ahead: int = 5) -> List[float]:
        """
        Generate forecast for the next N steps (e.g. 5 steps = ~25 seconds ahead).
        """
        series = self.history.get(approach_id, [])
        if len(series) < 3:
            # Fallback to last known value or zero
            val = series[-1] if series else 0.0
            return [round(val, 2)] * steps_ahead

        # Initialize level (L) and trend (T)
        level = series[0]
        trend = series[1] - series[0]

        for val in series[1:]:
            last_level = level
            level = self.alpha * val + (1 - self.alpha) * (level + trend)
            trend = self.beta * (level - last_level) + (1 - self.beta) * trend

        # Extrapolate
        predictions = []
        for m in range(1, steps_ahead + 1):
            pred = max(0.0, level + m * trend)
            predictions.append(round(pred, 2))

        return predictions
