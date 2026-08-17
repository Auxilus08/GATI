"""
GATI Traffic Vision Pipeline Execution CLI.

Processes a traffic video / RTSP feed using YOLOv8 and ByteTrack,
computes approach-based vehicle counts, queue lengths, and speeds,
and outputs structured JSON/CSV telemetry logs.

Usage:
    # Run against an existing video file
    python scripts/run_traffic_pipeline.py --video path/to/traffic.mp4 --output-dir ./scratch/vision_output

    # Generate synthetic Nagpur junction video and run pipeline
    python scripts/run_traffic_pipeline.py --generate-sample --frames 90 --output-dir ./scratch/vision_output --save-video
"""

import argparse
import logging
from pathlib import Path
import sys
import time
from typing import Optional
import cv2
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import load_junction_config, load_global_settings
from edge.vision import (
    YOLODetector,
    TrafficVideoPipeline,
    StructuredTelemetryWriter,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gati.vision.cli")


def generate_synthetic_traffic_video(output_path: Path, num_frames: int = 90, fps: int = 15) -> Path:
    """
    Generates a realistic test video of an Indian urban intersection with
    cars, buses, auto-rickshaws, and two-wheelers moving towards a junction stopline.
    """
    w, h = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

    logger.info(f"Generating synthetic traffic test video: {output_path} ({num_frames} frames @ {fps} fps)")

    # Define synthetic vehicles with trajectories
    vehicles = [
        {"type": "bus", "color": (50, 100, 220), "size": (50, 90), "pos": [260, 50], "speed": 2.5, "stopped": False},
        {"type": "car", "color": (180, 180, 180), "size": (35, 55), "pos": [330, 80], "speed": 3.2, "stopped": False},
        {"type": "auto_rickshaw", "color": (0, 215, 255), "size": (28, 40), "pos": [280, 180], "speed": 2.0, "stopped": False},
        {"type": "two_wheeler", "color": (255, 120, 0), "size": (18, 30), "pos": [340, 220], "speed": 3.8, "stopped": False},
        {"type": "car", "color": (100, 200, 100), "size": (35, 55), "pos": [320, 310], "speed": 0.5, "stopped": True},
        {"type": "two_wheeler", "color": (200, 100, 200), "size": (18, 30), "pos": [270, 320], "speed": 0.3, "stopped": True},
    ]

    for f in range(num_frames):
        frame = np.ones((h, w, 3), dtype=np.uint8) * 60  # Asphalt grey road

        # Draw road markings (Nagpur Sitabuldi approach)
        cv2.rectangle(frame, (220, 0), (420, h), (75, 75, 75), -1)  # 3-lane carriageway
        cv2.line(frame, (220, 0), (220, h), (255, 255, 255), 2)     # Road curb left
        cv2.line(frame, (420, 0), (420, h), (255, 255, 255), 2)     # Road curb right

        # Stopline
        cv2.line(frame, (220, 380), (420, 380), (255, 255, 255), 4)

        # Faint dashed lane dividers (Indian road style)
        for y in range(0, h, 40):
            cv2.line(frame, (285, y), (285, y + 20), (200, 200, 200), 1)
            cv2.line(frame, (355, y), (355, y + 20), (200, 200, 200), 1)

        # Draw pedestrian crossing
        for px in range(225, 415, 25):
            cv2.rectangle(frame, (px, 390), (px + 15, 410), (240, 240, 240), -1)

        # Update and render vehicles
        for v in vehicles:
            vx, vy = v["pos"]
            vw, vh = v["size"]

            # Vehicle body
            cv2.rectangle(frame, (int(vx), int(vy)), (int(vx + vw), int(vy + vh)), v["color"], -1)
            cv2.rectangle(frame, (int(vx), int(vy)), (int(vx + vw), int(vy + vh)), (0, 0, 0), 1)

            # Windshield / Roof detail
            cv2.rectangle(frame, (int(vx + 4), int(vy + 6)), (int(vx + vw - 4), int(vy + 18)), (30, 30, 30), -1)

            # Move vehicle down towards stopline
            if not v["stopped"] or vy < 300:
                v["pos"][1] += v["speed"]
                # Slight lateral weaving typical in Indian traffic
                v["pos"][0] += np.sin(f * 0.1) * 0.4
                if v["pos"][1] >= 310:
                    v["stopped"] = True

        out.write(frame)

    out.release()
    logger.info("Synthetic video generated successfully.")
    return output_path


def run_pipeline(
    video_source: str,
    junction_id: str = "NGP_J01_SITABULDI",
    model_path: str = "yolov8n.pt",
    output_dir: str = "./scratch/vision_output",
    save_annotated_video: bool = False,
    window_sec: float = 3.0,
    max_frames: Optional[int] = None,
):
    """Run detection and tracking pipeline over video source."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Load junction geometry & settings
    try:
        j_config = load_junction_config(junction_id)
        logger.info(f"Loaded config for junction: {j_config.name} ({j_config.junction_id})")
    except Exception as e:
        logger.warning(f"Could not load junction config for {junction_id}: {e}. Using defaults.")
        j_config = None

    global_settings = load_global_settings()

    # Initialize YOLOv8 Detector & Tracker
    logger.info(f"Initializing YOLOv8 detector with model '{model_path}'...")
    detector = YOLODetector(
        model_path=model_path,
        conf_threshold=0.25,
        pcu_weights=global_settings.pcu_weights,
    )

    pipeline = TrafficVideoPipeline(
        detector=detector,
        junction_config=j_config,
        window_duration_sec=window_sec,
    )

    writer = StructuredTelemetryWriter(output_dir=out_path, junction_id=junction_id)

    # Open video capture
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        logger.error(f"Failed to open video source: {video_source}")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0

    logger.info(f"Video stream opened: {width}x{height} @ {fps:.1f} FPS")

    if j_config:
        pipeline.setup_approaches_from_junction_config(width, height, j_config)

    # Video Writer for annotated output
    video_writer = None
    if save_annotated_video:
        annotated_file = out_path / "annotated_traffic_output.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(str(annotated_file), fourcc, fps, (width, height))
        logger.info(f"Saving annotated video to: {annotated_file}")

    frame_idx = 0
    sim_start_time = time.time()
    last_window_time = sim_start_time

    print("\n" + "=" * 75)
    print(f" GATI Edge Vision Pipeline Active | Junction: {junction_id}")
    print("=" * 75)

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            if max_frames and frame_idx > max_frames:
                break

            current_timestamp = sim_start_time + (frame_idx / fps)

            # Process frame
            tracked_vehicles, approach_metrics = pipeline.process_frame(
                frame, frame_idx=frame_idx, timestamp=current_timestamp
            )

            # Log frame detections
            writer.log_frame(
                frame_idx=frame_idx,
                timestamp=current_timestamp,
                tracked_vehicles=tracked_vehicles,
                approach_metrics=approach_metrics,
            )

            # Check time-window aggregation
            if (current_timestamp - last_window_time) >= window_sec:
                window_data = pipeline.get_window_aggregation(current_timestamp)
                writer.log_window(timestamp=current_timestamp, window_metrics=window_data)
                last_window_time = current_timestamp

                # Print summary table
                print(f"\n[Telemetry Window @ T+{current_timestamp - sim_start_time:.1f}s]")
                for app_id, data in window_data.items():
                    print(
                        f"  -> Approach {app_id:12s} | "
                        f"PCU: {data['total_pcu']:4.1f} | "
                        f"Queue: {data['queue_length_meters']:5.1f}m | "
                        f"Avg Speed: {data['average_speed_kmh']:4.1f} km/h | "
                        f"Counts: {data['vehicle_counts']}"
                    )

            # Annotate and write output video
            if video_writer:
                vis_frame = pipeline.render_overlay(frame, tracked_vehicles, approach_metrics)
                video_writer.write(vis_frame)

    finally:
        cap.release()
        if video_writer:
            video_writer.release()

    # Flush final window
    final_window = pipeline.get_window_aggregation(sim_start_time + (frame_idx / fps))
    if final_window:
        writer.log_window(timestamp=sim_start_time + (frame_idx / fps), window_metrics=final_window)

    print("\n" + "=" * 75)
    print(f" Processing complete. Processed {frame_idx} frames.")
    print(f" Structured telemetry saved in: {out_path.resolve()}")
    print(f"   1. Frame Tracks JSONL:  {writer.frames_json_path.name}")
    print(f"   2. Window Metrics JSONL: {writer.window_json_path.name}")
    print(f"   3. Tabular Window CSV:   {writer.window_csv_path.name}")
    print("=" * 75 + "\n")


def main():
    parser = argparse.ArgumentParser(description="GATI Edge Detection & Tracking Runner")
    parser.add_argument("--video", type=str, default=None, help="Path to video file or RTSP stream")
    parser.add_argument("--generate-sample", action="store_true", help="Generate synthetic test video")
    parser.add_argument("--junction", type=str, default="NGP_J01_SITABULDI", help="Junction ID")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="YOLO model path (.pt or .onnx)")
    parser.add_argument("--output-dir", type=str, default="./scratch/vision_output", help="Output directory")
    parser.add_argument("--save-video", action="store_true", help="Save annotated output video")
    parser.add_argument("--window-sec", type=float, default=3.0, help="Telemetry window duration (sec)")
    parser.add_argument("--frames", type=int, default=60, help="Max frames to process")

    args = parser.parse_args()

    video_input = args.video
    if not video_input or args.generate_sample:
        sample_path = Path(args.output_dir) / "synthetic_traffic_sample.mp4"
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        generate_synthetic_traffic_video(sample_path, num_frames=args.frames, fps=15)
        video_input = str(sample_path)

    run_pipeline(
        video_source=video_input,
        junction_id=args.junction,
        model_path=args.model,
        output_dir=args.output_dir,
        save_annotated_video=args.save_video,
        window_sec=args.window_sec,
        max_frames=args.frames,
    )


if __name__ == "__main__":
    main()
