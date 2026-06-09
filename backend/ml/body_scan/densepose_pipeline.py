"""DensePose body scanning pipeline.

Converts 2D camera/webcam image into UV body surface map and body measurements.
Primary: Facebook DensePose RCNN (detectron2).
Fallback: Mediapipe Pose for keypoint-based measurement estimation.
"""
from __future__ import annotations

import io
import logging
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from config.settings import settings

logger = logging.getLogger(__name__)

# DensePose body part indices for measurement regions
TORSO_PARTS = {1, 2, 3, 4}
LEG_PARTS = {14, 15, 16, 17}
HEAD_PART = 24


class BodyScanPipeline:
    """Body scanning: image -> UV map -> measurements -> avatar mesh."""

    def __init__(self) -> None:
        self._densepose_predictor = None
        self._mediapipe_pose = None
        self._use_densepose = False
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            self._init_densepose()
        except Exception as e:
            logger.info("DensePose unavailable (%s), initializing Mediapipe Pose fallback", e)
            self._init_mediapipe()

    def _init_densepose(self) -> None:
        from detectron2.config import get_cfg
        from detectron2.engine import DefaultPredictor
        from detectron2.projects.densepose import add_densepose_config

        cfg = get_cfg()
        add_densepose_config(cfg)
        model_dir = settings.MODELS_DIR / "densepose"
        cfg_path = model_dir / "config.yaml"
        weights_path = model_dir / "model_final.pth"
        if not cfg_path.exists() or not weights_path.exists():
            raise FileNotFoundError(f"DensePose model files not found in {model_dir}")
        cfg.merge_from_file(str(cfg_path))
        cfg.MODEL.WEIGHTS = str(weights_path)
        cfg.MODEL.DEVICE = settings.effective_device
        self._densepose_predictor = DefaultPredictor(cfg)
        self._use_densepose = True
        logger.info("DensePose predictor loaded on %s", settings.effective_device)

    def _init_mediapipe(self) -> None:
        import mediapipe as mp
        self._mediapipe_pose = mp.solutions.pose.Pose(
            static_image_mode=True, model_complexity=2, min_detection_confidence=0.5,
        )
        logger.info("Mediapipe Pose fallback loaded")

    def scan_from_image(self, image: np.ndarray | Image.Image) -> dict[str, Any]:
        self._ensure_loaded()
        if isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        if self._use_densepose and self._densepose_predictor:
            return self._scan_densepose(image)
        if self._mediapipe_pose is not None:
            return self._scan_mediapipe(image)
        return {"uv_map": None, "keypoints": [], "measurements": {}, "avatar_obj": None}

    def _scan_densepose(self, image: np.ndarray) -> dict[str, Any]:
        outputs = self._densepose_predictor(image)
        instances = outputs["instances"].to("cpu")
        if not instances.has("pred_densepose") or len(instances) == 0:
            logger.warning("No person detected in image for DensePose")
            return {"uv_map": None, "keypoints": [], "measurements": {}, "avatar_obj": None}

        dp = instances.pred_densepose[0]
        uv_map = np.stack([dp.u.numpy(), dp.v.numpy()], axis=0)
        keypoints = self._extract_keypoints_from_densepose(dp)

        measurements = self._extract_measurements_from_uv(uv_map, image.shape)
        avatar_obj = self._generate_avatar_mesh(uv_map, measurements)

        return {"uv_map": uv_map, "keypoints": keypoints, "measurements": measurements, "avatar_obj": avatar_obj}

    def _scan_mediapipe(self, image: np.ndarray) -> dict[str, Any]:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self._mediapipe_pose.process(rgb)
        if not results.pose_landmarks:
            logger.warning("No pose landmarks detected")
            return {"uv_map": None, "keypoints": [], "measurements": {}, "avatar_obj": None}

        h_px, w_px = image.shape[:2]
        keypoints = [{"x": lm.x * w_px, "y": lm.y * h_px, "z": lm.z, "visibility": lm.visibility} for lm in results.pose_landmarks.landmark]
        measurements = self._estimate_measurements_from_keypoints(keypoints, h_px, w_px)
        return {"uv_map": None, "keypoints": keypoints, "measurements": measurements, "avatar_obj": None}

    @staticmethod
    def _extract_keypoints_from_densepose(dp: Any) -> list[dict]:
        keypoints = []
        if hasattr(dp, "keypoints"):
            kpts = dp.keypoints
            for i in range(kpts.shape[1]):
                keypoints.append({"x": float(kpts[0, i]), "y": float(kpts[1, i]), "confidence": float(kpts[2, i]) if kpts.shape[0] > 2 else 1.0})
        return keypoints

    @staticmethod
    def _extract_measurements_from_uv(uv_map: np.ndarray, image_shape: tuple) -> dict[str, float]:
        h, w = image_shape[:2]
        person_height_px = h * 0.7
        px_per_cm = person_height_px / 170.0 if person_height_px > 0 else 10.0

        u, v = uv_map[0], uv_map[1]
        valid = (u > 0) & (v > 0)
        if not valid.any():
            return {}

        ys, xs = np.where(valid)
        if len(xs) == 0:
            return {}

        top_y, bottom_y = int(ys.min()), int(ys.max())
        height_cm = (bottom_y - top_y) / px_per_cm

        # Separate torso and leg regions by analyzing vertical distribution
        mid_y = top_y + (bottom_y - top_y) * 0.45
        torso_mask = valid & (np.arange(h)[:, None] < mid_y)
        leg_mask = valid & (np.arange(h)[:, None] >= mid_y)

        torso_ys, torso_xs = np.where(torso_mask)
        body_width_px = float(torso_xs.max() - torso_xs.min()) if len(torso_xs) > 0 else float(xs.max() - xs.min())

        shoulder_width_cm = body_width_px * 0.9 / px_per_cm
        # Circumference estimates from projected width using elliptical approximation
        chest_cm = shoulder_width_cm * 2.6
        waist_cm = shoulder_width_cm * 2.2
        hip_cm = shoulder_width_cm * 2.5
        inseam_cm = height_cm * 0.47

        return {
            "height_cm": round(height_cm, 1), "chest_cm": round(chest_cm, 1),
            "waist_cm": round(waist_cm, 1), "hip_cm": round(hip_cm, 1),
            "inseam_cm": round(inseam_cm, 1), "shoulder_cm": round(shoulder_width_cm, 1),
        }

    @staticmethod
    def _estimate_measurements_from_keypoints(keypoints: list[dict], h_px: int, w_px: int) -> dict[str, float]:
        px_per_cm = (h_px * 0.7) / 170.0 if h_px > 0 else 10.0

        def dist(i: int, j: int) -> float:
            p1, p2 = keypoints[i], keypoints[j]
            return ((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2) ** 0.5

        # Mediapipe Pose landmark indices
        LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
        LEFT_HIP, RIGHT_HIP = 23, 24
        LEFT_ANKLE = 27
        NOSE = 0

        shoulder_width_px = dist(LEFT_SHOULDER, RIGHT_SHOULDER)
        hip_width_px = dist(LEFT_HIP, RIGHT_HIP)
        height_px = dist(NOSE, LEFT_ANKLE) if len(keypoints) > LEFT_ANKLE else h_px * 0.7

        shoulder_cm = shoulder_width_px / px_per_cm
        hip_cm = hip_width_px / px_per_cm
        height_cm = height_px / px_per_cm

        return {
            "height_cm": round(height_cm, 1), "chest_cm": round(shoulder_cm * 2.6, 1),
            "waist_cm": round(shoulder_cm * 2.2, 1), "hip_cm": round(hip_cm * 2.8, 1),
            "inseam_cm": round(height_cm * 0.47, 1), "shoulder_cm": round(shoulder_cm, 1),
        }

    @staticmethod
    def _generate_avatar_mesh(uv_map: np.ndarray, measurements: dict | None = None) -> bytes | None:
        """Generate a simplified .obj mesh from UV coordinates.

        Creates a deformable body mesh by sampling the UV coordinate grid
        and connecting vertices into a quad-based surface mesh.
        """
        if uv_map is None:
            return None

        u, v = uv_map[0], uv_map[1]
        valid = (u > 0) & (v > 0)
        if not valid.any():
            return None

        ys, xs = np.where(valid)
        if len(xs) == 0:
            return None

        # Sample grid points for mesh vertices
        step = 8
        sample_ys = np.arange(ys.min(), ys.max(), step)
        sample_xs = np.arange(xs.min(), xs.max(), step)

        vertices = []
        faces = []
        vertex_map = {}
        idx = 1

        for sy in sample_ys:
            for sx in sample_xs:
                if 0 <= sy < uv_map.shape[1] and 0 <= sx < uv_map.shape[2] and valid[sy, sx]:
                    z_val = float(uv_map[1, sy, sx]) * 0.3  # Use V channel as depth hint
                    vertices.append(f"v {sx} {sy} {z_val}")
                    vertex_map[(sy, sx)] = idx
                    idx += 1

        # Connect adjacent vertices into faces
        for i, sy in enumerate(sample_ys[:-1]):
            for j, sx in enumerate(sample_xs[:-1]):
                v1 = vertex_map.get((sy, sx))
                v2 = vertex_map.get((sy, sx + step))
                v3 = vertex_map.get((sy + step, sx + step))
                v4 = vertex_map.get((sy + step, sx))
                if v1 and v2 and v3 and v4:
                    faces.append(f"f {v1} {v2} {v3} {v4}")

        if not vertices:
            return None

        obj_lines = ["# wardrobe-twin-agent body mesh", f"# Vertices: {len(vertices)}, Faces: {len(faces)}"]
        obj_lines.extend(vertices)
        obj_lines.extend(faces)
        return "\n".join(obj_lines).encode("utf-8")


body_scan = BodyScanPipeline()
