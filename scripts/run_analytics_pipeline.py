"""
GATI Analytics Pipeline Execution CLI.

Ingests real tracked video telemetry (frames & windows JSONL), runs:
1. 10-30 minute short-horizon congestion forecaster
2. Stalled vehicle & incident detection
3. Live approach risk calculation (speed variance, hard braking, near-misses)
and outputs structured JSONL/CSV analytics logs.

Usage:
    python scripts/run_analytics_pipeline.py --windows ./scratch/vision_output/vision_windows.jsonl --frames ./scratch/vision_output/vision_frames.jsonl --output-dir ./scratch/analytics_output
"""

import argparse
import csv
import json
import logging
from pathlib import Path
import sys
from typing import Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from central.analytics import AnalyticsEngine
from edge.vision import ApproachQueueMetrics, TrackedVehicle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gati.analytics.cli")


def run_analytics(
    windows_file: Path,
    frames_file: Optional[Path] = None,
    output_dir: Path = Path("./scratch/analytics_output"),
    stalled_threshold_sec: float = 20.0,
):
    """Run end-to-end analytics over tracked telemetry files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if not windows_file.exists():
        raise FileNotFoundError(f"Telemetry windows file not found: {windows_file}")

    # Load telemetry windows
    windows = []
    with open(windows_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                windows.append(json.loads(line.strip()))

    # Load frame-level vehicle tracks if available
    frame_vehicles_by_ts: Dict[float, List[TrackedVehicle]] = {}
    if frames_file and frames_file.exists():
        with open(frames_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line.strip())
                    ts = round(float(obj["timestamp"]), 2)
                    v_list = []
                    for vd in obj.get("vehicles", []):
                        v_list.append(
                            TrackedVehicle(
                                track_id=vd["track_id"],
                                vehicle_type=vd["class"],
                                confidence=vd.get("confidence", 0.9),
                                bbox=tuple(vd["bbox"]),
                                speed_kmh=vd.get("speed_kmh", 0.0),
                                is_emergency=vd.get("is_emergency", False),
                            )
                        )
                    frame_vehicles_by_ts[ts] = v_list

    engine = AnalyticsEngine(stalled_threshold_sec=stalled_threshold_sec)

    forecasts_out = output_dir / "analytics_forecasts.jsonl"
    incidents_out = output_dir / "analytics_incidents.jsonl"
    risk_out_json = output_dir / "analytics_live_risk.jsonl"
    risk_out_csv = output_dir / "analytics_live_risk.csv"

    # Initialize Risk CSV
    with open(risk_out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "approach_id",
            "live_risk_score",
            "risk_level",
            "speed_variance",
            "hard_braking_count",
            "near_miss_count",
            "average_speed_kmh",
            "active_vehicle_count",
            "contributing_factors",
        ])

    print("\n" + "=" * 78)
    print(" GATI REAL-DATA TRAFFIC ANALYTICS PIPELINE")
    print("=" * 78)

    processed_steps = 0
    all_incidents = []

    for win in windows:
        ts = float(win["timestamp"])
        approaches_raw = win.get("approaches", {})

        approach_metrics: Dict[str, ApproachQueueMetrics] = {}
        for app_id, data in approaches_raw.items():
            approach_metrics[app_id] = ApproachQueueMetrics(
                approach_id=app_id,
                total_pcu=float(data.get("total_pcu", 0.0)),
                queue_length_meters=float(data.get("queue_length_meters", 0.0)),
                average_speed_kmh=float(data.get("average_speed_kmh", 0.0)),
                vehicle_counts=data.get("vehicle_counts", {}),
                emergency_vehicle_detected=bool(data.get("emergency_vehicle_detected", False)),
                emergency_vehicle_count=int(data.get("emergency_vehicle_count", 0)),
            )

        # Match frame tracks closest to timestamp
        matched_ts = min(frame_vehicles_by_ts.keys(), key=lambda t: abs(t - ts)) if frame_vehicles_by_ts else None
        current_vehicles = frame_vehicles_by_ts.get(matched_ts, []) if matched_ts else []

        batch_result = engine.process_telemetry_step(
            timestamp=ts,
            approach_metrics=approach_metrics,
            tracked_vehicles=current_vehicles,
        )

        processed_steps += 1

        # Write forecasts
        with open(forecasts_out, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": ts,
                "forecasts": {k: v.__dict__ for k, v in batch_result.forecasts.items()},
            }) + "\n")

        # Write incidents
        if batch_result.active_incidents:
            all_incidents.extend(batch_result.active_incidents)
            with open(incidents_out, "a", encoding="utf-8") as f:
                for inc in batch_result.active_incidents:
                    f.write(json.dumps(inc.__dict__) + "\n")

        # Write approach risk JSON & CSV
        with open(risk_out_json, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": ts,
                "risks": {k: v.__dict__ for k, v in batch_result.approach_risks.items()},
            }) + "\n")

        with open(risk_out_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for app_id, r in batch_result.approach_risks.items():
                writer.writerow([
                    r.timestamp,
                    r.approach_id,
                    r.live_risk_score,
                    r.risk_level,
                    r.speed_variance,
                    r.hard_braking_count,
                    r.near_miss_count,
                    r.average_speed_kmh,
                    r.active_vehicle_count,
                    "; ".join(r.contributing_factors),
                ])

    print(f"\n[Analytics Summary after {processed_steps} time steps]:")
    for app_id, fc in batch_result.forecasts.items():
        rk = batch_result.approach_risks.get(app_id)
        risk_str = f"Risk={rk.live_risk_score}/100 ({rk.risk_level})" if rk else ""
        print(
            f"  Approach {app_id:12s} | "
            f"Current PCU: {fc.current_pcu:4.1f} | "
            f"10-min Forecast: {fc.forecast_10min_pcu:4.1f} PCU ({fc.forecast_10min_queue_m:5.1f}m) | "
            f"30-min Forecast: {fc.forecast_30min_pcu:4.1f} PCU | "
            f"Trend: {fc.trend_direction:<12s} | {risk_str}"
        )

    print("-" * 78)
    print(f" Detected Incidents:  {len(all_incidents)} incident(s) flagged.")
    for inc in all_incidents:
        print(f"   [!] Track #{inc.track_id} ({inc.vehicle_type}): {inc.description} | Severity: {inc.severity}")

    print("\n" + "=" * 78)
    print(f" Analytics reports successfully saved to: {output_dir.resolve()}")
    print(f"   1. Congestion Forecasts JSONL: {forecasts_out.name}")
    print(f"   2. Incident Alerts JSONL:      {incidents_out.name}")
    print(f"   3. Live Approach Risk JSONL:   {risk_out_json.name}")
    print(f"   4. Live Approach Risk CSV:     {risk_out_csv.name}")
    print("=" * 78 + "\n")


def main():
    parser = argparse.ArgumentParser(description="GATI Real-Data Traffic Analytics Pipeline")
    parser.add_argument("--windows", type=str, default="./scratch/vision_output/vision_windows.jsonl", help="Path to vision_windows.jsonl")
    parser.add_argument("--frames", type=str, default="./scratch/vision_output/vision_frames.jsonl", help="Path to vision_frames.jsonl")
    parser.add_argument("--output-dir", type=str, default="./scratch/analytics_output", help="Output directory")
    parser.add_argument("--stalled-sec", type=float, default=20.0, help="Stalled vehicle threshold (sec)")

    args = parser.parse_args()

    win_path = Path(args.windows)
    frames_path = Path(args.frames)

    if not win_path.exists():
        logger.warning(f"Telemetry file {win_path} not found. Running synthetic traffic video first...")
        from scripts.run_traffic_pipeline import main as run_vision_main
        run_vision_main()

    run_analytics(
        windows_file=win_path,
        frames_file=frames_path,
        output_dir=Path(args.output_dir),
        stalled_threshold_sec=args.stalled_sec,
    )


if __name__ == "__main__":
    main()
