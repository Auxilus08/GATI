"""
Planar Homography & Perspective Distortion Correction for Traffic Cameras.

Transforms 2D CCTV camera pixel coordinates (u, v) into calibrated metric
ground-plane coordinates (x, y) in meters, eliminating perspective foreshortening
and camera tilt distortion at distance.
"""

from typing import List, Tuple, Optional
import numpy as np
import cv2


class PlanarHomographyTransformer:
    """
    Transforms camera pixels to metric ground-plane coordinates using 4-point homography.
    """

    def __init__(
        self,
        camera_source_points: Optional[List[Tuple[float, float]]] = None,
        ground_metric_points: Optional[List[Tuple[float, float]]] = None,
        default_meters_per_pixel: float = 0.05,
    ):
        """
        :param camera_source_points: 4 quadrilateral vertices in camera pixel space [(u0, v0), ... (u3, v3)]
        :param ground_metric_points: 4 corresponding vertices in real-world meters [(x0, y0), ... (x3, y3)]
        :param default_meters_per_pixel: Fallback linear scale if homography points are not provided
        """
        self.default_m_px = default_meters_per_pixel
        self.homography_matrix: Optional[np.ndarray] = None
        self.inv_homography_matrix: Optional[np.ndarray] = None

        if camera_source_points and ground_metric_points and len(camera_source_points) == 4 and len(ground_metric_points) == 4:
            self.calibrate(camera_source_points, ground_metric_points)

    def calibrate(
        self,
        camera_points: List[Tuple[float, float]],
        ground_metric_points: List[Tuple[float, float]],
    ) -> bool:
        """Compute the 3x3 homography matrix mapping image pixels to ground meters."""
        src = np.array(camera_points, dtype=np.float32)
        dst = np.array(ground_metric_points, dtype=np.float32)

        try:
            h_mat, status = cv2.findHomography(src, dst)
            if h_mat is not None:
                self.homography_matrix = h_mat
                self.inv_homography_matrix = np.linalg.inv(h_mat)
                return True
        except Exception:
            pass
        return False

    def pixel_to_ground_metric(self, px: float, py: float) -> Tuple[float, float]:
        """
        Transform a pixel point (u, v) to ground coordinate (x, y) in meters.
        """
        if self.homography_matrix is not None:
            pt = np.array([[[px, py]]], dtype=np.float32)
            transformed = cv2.perspectiveTransform(pt, self.homography_matrix)
            return float(transformed[0][0][0]), float(transformed[0][0][1])
        # Fallback linear approximation
        return float(px * self.default_m_px), float(py * self.default_m_px)

    def compute_distance_meters(
        self,
        pt1_px: Tuple[float, float],
        pt2_px: Tuple[float, float],
    ) -> float:
        """Compute Euclidean ground distance in meters between two camera pixel points."""
        x1, y1 = self.pixel_to_ground_metric(pt1_px[0], pt1_px[1])
        x2, y2 = self.pixel_to_ground_metric(pt2_px[0], pt2_px[1])
        return float(np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))

    def compute_queue_length_meters(
        self,
        vehicle_centroids_px: List[Tuple[float, float]],
        stopline_px: Tuple[float, float],
    ) -> float:
        """
        Compute queue length from stopline to furthest stopped vehicle using projective metric distance.
        """
        if not vehicle_centroids_px:
            return 0.0

        max_dist = 0.0
        for pt in vehicle_centroids_px:
            d = self.compute_distance_meters(pt, stopline_px)
            if d > max_dist:
                max_dist = d

        return round(max_dist, 1)
