"""
GATI Edge Model Quantization & ONNX / TensorRT Export Utility.

Converts standard YOLOv8 models (.pt) into optimized edge formats:
- ONNX with FP16 (Half precision) for edge NPUs / CPU SIMD engines.
- TensorRT engine export path for Nvidia Jetson Orin Nano / Xavier edge hardware.
- INT8 quantization preparation for extreme low-power embedded deployment.

Usage:
    python -m edge.vision.export_onnx --model yolov8n.pt --format onnx --half --imgsz 640
"""

import argparse
import logging
from pathlib import Path
import sys
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("edge.export")


def export_edge_model(
    model_path: str = "yolov8n.pt",
    output_format: str = "onnx",
    imgsz: int = 640,
    half: bool = True,
    dynamic: bool = False,
    simplify: bool = True,
    int8: bool = False,
    device: str = "cpu",
) -> Optional[str]:
    """
    Export YOLOv8 model for edge deployment on Jetson Orin Nano / Industrial Edge PC.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("ultralytics package is required for model export. Run: pip install ultralytics")
        return None

    model_file = Path(model_path)
    logger.info(f"Initiating edge export for model: {model_path}")
    logger.info(f"Target format: {output_format}, Half (FP16): {half}, Dynamic: {dynamic}, INT8: {int8}")

    try:
        model = YOLO(model_path)
        exported_path = model.export(
            format=output_format,
            imgsz=imgsz,
            half=half,
            dynamic=dynamic,
            simplify=simplify,
            int8=int8,
            device=device,
        )
        logger.info(f"Successfully exported model to: {exported_path}")
        return exported_path
    except Exception as e:
        logger.error(f"Failed to export model {model_path}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="GATI YOLOv8 Edge Quantization & Export Tool")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Path to input PyTorch model (.pt)")
    parser.add_argument("--format", type=str, default="onnx", choices=["onnx", "engine", "tflite", "openvino"], help="Target edge format")
    parser.add_argument("--imgsz", type=int, default=640, help="Input inference resolution (e.g. 640, 480)")
    parser.add_argument("--half", action="store_true", default=True, help="Enable FP16 half precision")
    parser.add_argument("--dynamic", action="store_true", default=False, help="Enable dynamic input shapes")
    parser.add_argument("--int8", action="store_true", default=False, help="Enable INT8 quantization")
    parser.add_argument("--device", type=str, default="cpu", help="Device for export (cpu, 0, cuda:0)")

    args = parser.parse_args()

    result = export_edge_model(
        model_path=args.model,
        output_format=args.format,
        imgsz=args.imgsz,
        half=args.half,
        dynamic=args.dynamic,
        int8=args.int8,
        device=args.device,
    )

    if result:
        print(f"\n[OK] Model successfully exported to: {result}")
        sys.exit(0)
    else:
        print(f"\n[ERROR] Model export failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
