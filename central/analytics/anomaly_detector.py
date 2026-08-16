"""
Traffic Anomaly & Bottleneck Detector.
Detects sudden traffic surges, abnormal queue growth, and spillback risks using statistical Z-scores.
"""
from typing import Dict, List, Optional, Any
import numpy as np


class AnomalyDetector:
    """Detects statistical traffic anomalies and bottleneck conditions."""

    def __init__(self, zscore_threshold: float = 2.5, min_samples: int = 15):
        self.zscore_threshold = zscore_threshold
        self.min_samples = min_samples
        self.history: Dict[str, List[float]] = {}

    def check_anomaly(self, approach_id: str, current_pcu: float) -> Dict[str, Any]:
        """
        Calculates rolling mean and standard deviation to identify anomalous PCU surges.
        """
        if approach_id not in self.history:
            self.history[approach_id] = []

        history_vals = self.history[approach_id]
        is_anomaly = False
        z_score = 0.0
        severity = "NORMAL"

        if len(history_vals) >= self.min_samples:
            mean = np.mean(history_vals)
            std = np.std(history_vals)
            if std > 0.1:
                z_score = float((current_pcu - mean) / std)
                if z_score >= self.zscore_threshold:
                    is_anomaly = True
                    severity = "CRITICAL" if z_score > 3.5 else "WARNING"

        # Update history
        history_vals.append(float(current_pcu))
        if len(history_vals) > 200:
            history_vals.pop(0)

        return {
            "approach_id": approach_id,
            "current_pcu": current_pcu,
            "is_anomaly": is_anomaly,
            "z_score": round(z_score, 2),
            "severity": severity,
        }
