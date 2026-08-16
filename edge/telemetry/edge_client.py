"""
GATI Edge Telemetry Client.
Transmits structured JSON telemetry (< 5 KB/s) from junction edge nodes to the central ICCC API.
Includes offline buffer to cache metrics during transient 4G/WAN network drops.
"""
import time
import json
from typing import Dict, Any, List
import requests


class EdgeTelemetryClient:
    """Lightweight telemetry transmitter with offline buffering."""

    def __init__(self, junction_id: str, central_url: str = "http://127.0.0.1:8000"):
        self.junction_id = junction_id
        self.central_url = central_url.rstrip("/")
        self.endpoint = f"{self.central_url}/api/v1/telemetry/report"
        self.buffer: List[Dict[str, Any]] = []
        self.max_buffer_size = 500  # Stores ~25 minutes of telemetry during network drops

    def build_telemetry_packet(
        self,
        active_phase_id: int,
        state: str,
        pressures: Dict[int, float],
        approach_metrics: Dict[str, Any],
        emergency_active: bool = False,
    ) -> Dict[str, Any]:
        """Construct compact, schema-compliant JSON telemetry."""
        return {
            "junction_id": self.junction_id,
            "timestamp": time.time(),
            "active_phase_id": active_phase_id,
            "signal_state": state,
            "pressures": pressures,
            "approaches": {
                k: {
                    "total_pcu": v.total_pcu if hasattr(v, "total_pcu") else v.get("total_pcu", 0),
                    "vehicle_counts": v.vehicle_counts if hasattr(v, "vehicle_counts") else v.get("vehicle_counts", {}),
                    "queue_length_m": v.queue_length_meters if hasattr(v, "queue_length_meters") else v.get("queue_length_meters", 0),
                    "avg_speed_kmh": v.average_speed_kmh if hasattr(v, "average_speed_kmh") else v.get("average_speed_kmh", 0),
                    "emergency": v.emergency_vehicle_detected if hasattr(v, "emergency_vehicle_detected") else v.get("emergency_vehicle_detected", False),
                }
                for k, v in approach_metrics.items()
            },
            "emergency_active": emergency_active,
        }

    def send_telemetry(self, packet: Dict[str, Any]) -> bool:
        """Transmit packet to central server, buffering if transmission fails."""
        try:
            # Try flushing buffer first if any exists
            if self.buffer:
                batch = self.buffer + [packet]
                resp = requests.post(f"{self.central_url}/api/v1/telemetry/batch", json=batch, timeout=2.0)
                if resp.status_code == 200:
                    self.buffer.clear()
                    return True

            resp = requests.post(self.endpoint, json=packet, timeout=2.0)
            if resp.status_code == 200:
                return True
            else:
                self._buffer_packet(packet)
                return False
        except Exception:
            self._buffer_packet(packet)
            return False

    def _buffer_packet(self, packet: Dict[str, Any]):
        if len(self.buffer) < self.max_buffer_size:
            self.buffer.append(packet)
