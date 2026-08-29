from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

COURT_LENGTH = 28.0
COURT_WIDTH = 15.0
BASKET_OFFSET = 1.575
COURT_CENTER_Y = COURT_WIDTH / 2
THREE_POINT_RADIUS = 6.75
CORNER_LINE_LATERAL = COURT_CENTER_Y - 0.9
CORNER_INTERSECTION = math.sqrt(THREE_POINT_RADIUS**2 - CORNER_LINE_LATERAL**2)
FREE_THROW_LINE_LEFT = 5.8
FREE_THROW_LINE_RIGHT = COURT_LENGTH - FREE_THROW_LINE_LEFT

# The published court pose model uses this fixed 18-point FIBA layout.
FIBA_KEYPOINTS = np.asarray([
    (0, 0), (0, 0.91), (0, 5.18), (0, 10.0), (0, 14.1), (0, 15.0),
    (14.0, 15.0), (14.0, 0),
    (5.79, 5.18), (5.79, 10.0),
    (28.0, 15.0), (28.0, 14.1), (28.0, 10.0), (28.0, 5.18), (28.0, 0.91), (28.0, 0),
    (22.21, 5.18), (22.21, 10.0),
], dtype=np.float32)


@dataclass
class CourtProjection:
    matrix: np.ndarray
    confidence: float
    keypoints: int
    reprojection_error: float


@dataclass
class ShotClassification:
    shot_type: str | None
    confidence: float
    court_x: float | None
    court_y: float | None
    reason: str


def projection_from_pose_result(result: Any) -> CourtProjection | None:
    keypoints = getattr(result, "keypoints", None)
    if keypoints is None or keypoints.xy is None or len(keypoints.xy) == 0:
        return None
    image_points = keypoints.xy[0].detach().cpu().numpy().astype(np.float32)
    if len(image_points) != len(FIBA_KEYPOINTS):
        return None
    if keypoints.conf is not None:
        confidences = keypoints.conf[0].detach().cpu().numpy()
    else:
        confidences = np.ones(len(image_points), dtype=np.float32)
    detected = (confidences >= 0.25) & (image_points[:, 0] > 0) & (image_points[:, 1] > 0)
    groups = [
        np.arange(18),
        np.asarray([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
        np.asarray([6, 7, 10, 11, 12, 13, 14, 15, 16, 17]),
    ]
    candidates: list[CourtProjection] = []
    for group in groups:
        indices = group[detected[group]]
        if len(indices) < 4:
            continue
        source = image_points[indices]
        target = FIBA_KEYPOINTS[indices]
        matrix, inliers = cv2.findHomography(source, target, cv2.RANSAC, 5.0)
        if matrix is None:
            continue
        projected = cv2.perspectiveTransform(source.reshape(-1, 1, 2), matrix).reshape(-1, 2)
        errors = np.linalg.norm(projected - target, axis=1)
        inlier_mask = inliers.ravel().astype(bool) if inliers is not None else np.ones(len(indices), dtype=bool)
        if int(inlier_mask.sum()) < 4:
            continue
        inlier_ratio = float(inlier_mask.mean())
        mean_confidence = float(confidences[indices][inlier_mask].mean())
        reprojection_error = float(errors[inlier_mask].mean())
        coverage = min(1.0, int(inlier_mask.sum()) / 8)
        confidence = mean_confidence * coverage * inlier_ratio * math.exp(-reprojection_error / 1.5)
        candidates.append(CourtProjection(matrix, min(1.0, confidence), int(inlier_mask.sum()), reprojection_error))
    if not candidates:
        return None
    best = max(candidates, key=lambda item: item.confidence)
    return best if best.confidence >= 0.35 else None


def transform_point(point: tuple[float, float], projection: CourtProjection) -> tuple[float, float] | None:
    source = np.asarray([[point]], dtype=np.float32)
    x, y = cv2.perspectiveTransform(source, projection.matrix).reshape(2)
    if not (-0.5 <= x <= COURT_LENGTH + 0.5 and -0.5 <= y <= COURT_WIDTH + 0.5):
        return None
    return float(x), float(y)


def classify_fiba_shot(point: tuple[float, float], projection_confidence: float) -> ShotClassification:
    x, y = point
    left_basket = (BASKET_OFFSET, COURT_CENTER_Y)
    right_basket = (COURT_LENGTH - BASKET_OFFSET, COURT_CENTER_Y)
    left_distance = math.dist(point, left_basket)
    right_distance = math.dist(point, right_basket)
    attacks_left = left_distance <= right_distance
    basket_x = left_basket[0] if attacks_left else right_basket[0]
    longitudinal = x - basket_x if attacks_left else basket_x - x
    lateral = abs(y - COURT_CENTER_Y)

    free_throw_x = FREE_THROW_LINE_LEFT if attacks_left else FREE_THROW_LINE_RIGHT
    free_throw_distance = abs(x - free_throw_x)
    if free_throw_distance <= 0.45 and lateral <= 2.45:
        confidence = projection_confidence * max(0.0, 1 - free_throw_distance / 0.6)
        if confidence >= 0.62:
            return ShotClassification("freeThrow", min(0.92, confidence), x, y, "release point is on the FIBA free-throw line")

    radius = math.hypot(longitudinal, lateral)
    in_corner_region = longitudinal <= CORNER_INTERSECTION
    boundary_distance = abs(lateral - CORNER_LINE_LATERAL) if in_corner_region else abs(radius - THREE_POINT_RADIUS)
    if boundary_distance < 0.25:
        return ShotClassification(None, projection_confidence * 0.5, x, y, "release point is too close to the three-point boundary")

    is_three = lateral >= CORNER_LINE_LATERAL if in_corner_region else radius >= THREE_POINT_RADIUS
    confidence = projection_confidence * min(1.0, 0.65 + boundary_distance / 1.5)
    if confidence < 0.55:
        return ShotClassification(None, confidence, x, y, "court projection confidence is insufficient")
    return ShotClassification("threePoint" if is_three else "twoPoint", min(0.95, confidence), x, y, "classified from the FIBA release-point geometry")
