"""
GATI Signal Controller Performance Benchmark & Before/After Evidence CLI.

Compares Fixed-Time Pre-Timed Signal vs GATI Adaptive Max-Pressure
using real telemetry logged from video detection.

Usage:
    python scripts/compare_signal_performance.py --windows ./scratch/vision_output/vision_windows.jsonl --junction NGP_J01_SITABULDI --output-dir ./scratch/comparison_output
"""

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import load_junction_config, load_global_settings
from edge.controller.comparison_harness import SignalComparisonHarness

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gati.comparison.cli")


def load_telemetry_windows(filepath: Path) -> List[dict]:
    """Load JSONL telemetry windows recorded from traffic video."""
    windows = []
    if not filepath.exists():
        raise FileNotFoundError(f"Telemetry log file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                windows.append(json.loads(line_str))
    return windows


def main():
    parser = argparse.ArgumentParser(description="GATI Fixed-Time vs Max-Pressure Performance Comparison")
    parser.add_argument("--windows", type=str, default="./scratch/vision_output/vision_windows.jsonl", help="Path to vision_windows.jsonl")
    parser.add_argument("--junction", type=str, default="NGP_J01_SITABULDI", help="Junction ID (e.g. NGP_J01_SITABULDI)")
    parser.add_argument("--output-dir", type=str, default="./scratch/comparison_output", help="Output directory for reports")

    args = parser.parse_args()

    win_path = Path(args.windows)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Junction Config
    j_config = load_junction_config(args.junction)
    settings = load_global_settings()

    # 2. Load Telemetry Data
    if not win_path.exists():
        logger.warning(f"Telemetry log {win_path} not found. Generating synthetic comparison data...")
        # Create realistic sample windows if none present
        from scripts.run_traffic_pipeline import generate_synthetic_traffic_video, run_pipeline
        sample_vid = out_dir / "temp_traffic.mp4"
        generate_synthetic_traffic_video(sample_vid, num_frames=60, fps=15)
        run_pipeline(
            video_source=str(sample_vid),
            junction_id=args.junction,
            output_dir=str(out_dir),
            max_frames=60,
        )
        win_path = out_dir / "vision_windows.jsonl"

    windows = load_telemetry_windows(win_path)
    logger.info(f"Loaded {len(windows)} telemetry time-windows for comparison.")

    # 3. Run Comparison
    harness = SignalComparisonHarness(
        junction_config=j_config,
        guardrails=settings.signal_guardrails,
        mp_config=settings.max_pressure,
    )

    summary, timeseries = harness.run_comparison_from_windows(windows)
    harness.save_comparison_reports(summary, timeseries, output_dir=out_dir)

    # 4. Print Executive Pitch Table
    print("\n" + "=" * 78)
    print(f" GATI SIGNAL CONTROL PERFORMANCE REPORT | Junction: {j_config.name}")
    print("=" * 78)
    print(f" Analyzed Timesteps:  {summary.total_timesteps} ({summary.duration_sec:.0f} seconds)")
    print("-" * 78)
    print(f" {'METRIC':<32} | {'FIXED-TIME':<18} | {'GATI MAX-PRESSURE':<18} | {'DELTA':<8}")
    print("-" * 78)
    print(f" {'Average Vehicular Wait Time':<32} | {summary.fixed_avg_wait_sec:6.1f} sec        | {summary.mp_avg_wait_sec:6.1f} sec          | -{summary.wait_time_reduction_pct:.1f}%")
    print(f" {'Average Queue Length':<32} | {summary.fixed_avg_queue_m:6.1f} m          | {summary.mp_avg_queue_m:6.1f} m            | -{summary.queue_reduction_pct:.1f}%")
    print(f" {'Peak Queue Spillback':<32} | {summary.fixed_peak_queue_m:6.1f} m          | {summary.mp_peak_queue_m:6.1f} m            | -{max(0.0, summary.fixed_peak_queue_m - summary.mp_peak_queue_m):.1f}m")
    print(f" {'Total Vehicular Delay':<32} | {summary.fixed_total_delay_pcu_sec:6.0f} PCU-sec    | {summary.mp_total_delay_pcu_sec:6.0f} PCU-sec      | -{summary.total_delay_saved_pcu_sec:.0f}")
    print("-" * 78)
    print(f" ESTIMATED ENVIRONMENTAL IMPACT:")
    print(f"   -> Fuel Wastage Avoided:   {summary.estimated_fuel_saved_liters:.2f} liters")
    print(f"   -> Carbon (CO2) Reduced:   {summary.co2_reduction_kg:.2f} kg CO2")
    print("=" * 78)
    print(f" Reports saved: {out_dir / 'comparison_summary.json'} & {out_dir / 'comparison_timeseries.csv'}\n")


if __name__ == "__main__":
    main()
