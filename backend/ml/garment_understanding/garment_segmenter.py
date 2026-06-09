"""Garment segmentation pipeline using SAM (Segment Anything Model).

Extracts clean garment images from photos by removing backgrounds.
"""
from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np
from PIL import Image

from config.settings import settings

logger = logging.getLogger(__name__)


class GarmentSegmenter:
    """Background removal for garment images using SAM or GrabCut fallback."""

    def __init__(self) -> None:
        self._sam_model = None
        self._sam_predictor = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            self._load_sam()
        except Exception as e:
            logger.info("SAM not available (%s), using GrabCut fallback", e)
            self._sam_model = None

    def _load_sam(self) -> None:
        try:
            from segment_anything import sam_model_registry, SamAutomaticMaskGenerator
            import torch
        except ImportError:
            raise ImportError("SAM not installed. Install with: pip install segment-anything (or pip install -e \".[ml-heavy]\")")
        sam_checkpoint = settings.MODELS_DIR / "sam" / "sam_vit_h.pth"
        if not sam_checkpoint.exists():
            logger.info("SAM checkpoint not found at %s. Download from https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth", sam_checkpoint)
            raise FileNotFoundError(f"SAM checkpoint not found at {sam_checkpoint}. Download and place it there.")
        model_type = "vit_h"
        self._sam_model = sam_model_registry[model_type](checkpoint=str(sam_checkpoint))
        self._sam_model.to(settings.effective_device)
        self._sam_predictor = SamAutomaticMaskGenerator(self._sam_model)
        logger.info("SAM model loaded on %s", settings.effective_device)

    @property
    def is_available(self) -> bool:
        self._ensure_loaded()
        return self._sam_model is not None

    def remove_background(self, image: Image.Image | np.ndarray) -> Image.Image:
        """Remove background from garment image, returning RGBA with transparent background."""
        self._ensure_loaded()
        if isinstance(image, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        if self._sam_predictor is not None:
            return self._segment_sam(image)
        return self._segment_grabcut(image)

    def _segment_sam(self, image: Image.Image) -> Image.Image:
        """Use SAM for automatic mask generation and garment extraction."""
        arr = np.array(image)
        masks = self._sam_predictor.generate(arr)
        if not masks:
            logger.warning("SAM produced no masks, falling back to GrabCut")
            return self._segment_grabcut(image)

        # Select the largest mask that likely covers the garment
        best_mask = max(masks, key=lambda m: m["area"])
        mask_arr = best_mask["segmentation"]

        result = image.convert("RGBA")
        result_arr = np.array(result)
        result_arr[:, :, 3] = (mask_arr * 255).astype(np.uint8)
        return Image.fromarray(result_arr)

    def _segment_grabcut(self, image: Image.Image) -> Image.Image:
        """GrabCut-based background removal fallback."""
        arr = np.array(image.convert("RGB"))
        arr_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        h, w = arr_bgr.shape[:2]
        mask = np.zeros((h, w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        rect = (int(w * 0.05), int(h * 0.05), int(w * 0.9), int(h * 0.9))
        cv2.grabCut(arr_bgr, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        binary_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

        kernel = np.ones((5, 5), np.uint8)
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        result = image.convert("RGBA")
        result_arr = np.array(result)
        result_arr[:, :, 3] = binary_mask
        return Image.fromarray(result_arr)


garment_segmenter = GarmentSegmenter()
