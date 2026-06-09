"""BLIP-2 garment description and attribute extraction pipeline.

Takes a garment image, generates a text caption via BLIP-2,
then extracts structured attributes through VQA prompts.
Includes confidence scoring for fallback decisions.
"""
from __future__ import annotations

import colorsys
import logging
from typing import Any

import numpy as np
from PIL import Image

from config.settings import settings

logger = logging.getLogger(__name__)

VQA_QUESTIONS = [
    ("item_type", "What type of clothing is this?"),
    ("color", "What is the main color of this garment?"),
    ("pattern", "What is the pattern on this garment?"),
    ("style", "What style is this garment?"),
    ("material", "What material is this garment made of?"),
]


class BLIP2Extractor:
    """BLIP-2 based garment attribute extraction with confidence scoring."""

    def __init__(self) -> None:
        self._model = None
        self._processor = None
        self._loaded = False
        self._confidence_scores: dict[str, float] = {}

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            from transformers import Blip2Processor, Blip2ForConditionalGeneration
            import torch
            self._processor = Blip2Processor.from_pretrained(settings.BLIP2_MODEL_ID)
            self._model = Blip2ForConditionalGeneration.from_pretrained(
                settings.BLIP2_MODEL_ID, torch_dtype=torch.float16 if settings.effective_device == "cuda" else torch.float32
            )
            self._model.to(settings.effective_device)
            self._model.eval()
            logger.info("BLIP-2 model loaded on %s", settings.effective_device)
        except Exception as e:
            logger.warning("BLIP-2 model load failed: %s", e)
            self._model = None
            self._processor = None

    @property
    def is_available(self) -> bool:
        self._ensure_loaded()
        return self._model is not None

    def describe(self, image: Image.Image | np.ndarray) -> dict[str, Any]:
        """Generate description and structured attributes for a garment image."""
        self._ensure_loaded()
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image if image.ndim == 3 else image)
        if self._model is not None and self._processor is not None:
            return self._describe_with_model(image)
        return self._describe_from_pixels(image)

    def _describe_with_model(self, image: Image.Image) -> dict[str, Any]:
        """Use BLIP-2 for captioning and VQA-based attribute extraction."""
        import torch
        device = settings.effective_device

        inputs = self._processor(image, return_tensors="pt").to(device)
        with torch.no_grad():
            generated_ids = self._model.generate(**inputs, max_new_tokens=50)
        caption = self._processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()

        attributes = {}
        confidence = {}
        for attr_key, question in VQA_QUESTIONS:
            try:
                vqa_inputs = self._processor(image, question, return_tensors="pt").to(device)
                with torch.no_grad():
                    vqa_ids = self._model.generate(**vqa_inputs, max_new_tokens=20)
                answer = self._processor.batch_decode(vqa_ids, skip_special_tokens=True)[0].strip()
                attributes[attr_key] = answer.lower()
                # Estimate confidence from output token probabilities
                with torch.no_grad():
                    vqa_logits = self._model.generate(**vqa_inputs, max_new_tokens=20, output_scores=True, return_dict_in_generate=True)
                if hasattr(vqa_logits, "sequences_scores") and vqa_logits.sequences_scores is not None:
                    score = float(torch.sigmoid(vqa_logits.sequences_scores[0]))
                    confidence[attr_key] = round(max(0.3, min(1.0, score)), 3)
                else:
                    confidence[attr_key] = 0.8
            except Exception:
                attributes[attr_key] = ""
                confidence[attr_key] = 0.0

        self._confidence_scores = confidence
        tags = [v for v in attributes.values() if v]
        return {"caption": caption, **attributes, "tags": tags, "confidence": confidence}

    def _describe_from_pixels(self, image: Image.Image) -> dict[str, Any]:
        """Pixel-analysis fallback: color histogram + aspect ratio heuristics."""
        arr = np.array(image.convert("RGB"))
        mean_r, mean_g, mean_b = arr.mean(axis=(0, 1))
        color = self._rgb_to_color_name(mean_r, mean_g, mean_b)
        secondary_color = self._detect_secondary_color(arr)

        h, w = arr.shape[:2]
        aspect = h / w if w > 0 else 1.0
        if aspect > 1.8:
            item_type = "dress"
        elif aspect > 1.3:
            item_type = "top"
        elif aspect > 0.9:
            item_type = "jacket"
        else:
            item_type = "bottom"

        pattern = self._detect_pattern(arr)
        material = self._estimate_material(arr)

        return {
            "caption": f"A {color} {item_type}",
            "item_type": item_type, "color": color, "pattern": pattern,
            "style": "casual", "material": material,
            "tags": [color, item_type, pattern, material],
            "confidence": {k: 0.4 for k in ["item_type", "color", "pattern", "style", "material"]},
        }

    @staticmethod
    def _rgb_to_color_name(r: float, g: float, b: float) -> str:
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        if v < 0.15:
            return "black"
        if v > 0.85 and s < 0.1:
            return "white"
        if s < 0.1:
            return "gray"
        if h < 0.05 or h > 0.95:
            return "red" if s > 0.3 and v > 0.3 else "pink"
        if h < 0.1:
            return "orange"
        if h < 0.17:
            return "yellow"
        if h < 0.42:
            return "green"
        if h < 0.55:
            return "teal"
        if h < 0.75:
            return "blue"
        if h < 0.85:
            return "purple"
        return "pink"

    @staticmethod
    def _detect_secondary_color(arr: np.ndarray) -> str:
        try:
            from sklearn.cluster import MiniBatchKMeans
            pixels = arr.reshape(-1, 3).astype(float) / 255.0
            if len(pixels) > 10000:
                indices = np.random.choice(len(pixels), 10000, replace=False)
                pixels = pixels[indices]
            kmeans = MiniBatchKMeans(n_clusters=3, random_state=42, n_init=3)
            kmeans.fit(pixels)
            centers = kmeans.cluster_centers_
            sorted_centers = centers[np.argsort(-np.bincount(kmeans.labels_))]
            r, g, b = sorted_centers[1] * 255 if len(sorted_centers) > 1 else (128, 128, 128)
            return BLIP2Extractor._rgb_to_color_name(r, g, b)
        except ImportError:
            # sklearn not installed - use simple histogram binning fallback
            arr_flat = arr.reshape(-1, 3)
            if len(arr_flat) > 10000:
                arr_flat = arr_flat[np.random.choice(len(arr_flat), 10000, replace=False)]
            r_bin = int(np.median(arr_flat[:, 0]))
            g_bin = int(np.median(arr_flat[:, 1]))
            b_bin = int(np.median(arr_flat[:, 2]))
            return BLIP2Extractor._rgb_to_color_name(r_bin, g_bin, b_bin)

    @staticmethod
    def _detect_pattern(arr: np.ndarray) -> str:
        gray = np.mean(arr, axis=2)
        grad_x = np.abs(np.diff(gray, axis=1))
        grad_y = np.abs(np.diff(gray, axis=0))
        grad_var = float(np.var(grad_x) + np.var(grad_y))
        if grad_var < 100:
            return "solid"
        if grad_var < 500:
            return "subtle"
        if grad_var < 2000:
            return "striped"
        return "patterned"

    @staticmethod
    def _estimate_material(arr: np.ndarray) -> str:
        gray = np.mean(arr, axis=2)
        texture = float(np.std(gray))
        if texture < 20:
            return "smooth"
        if texture < 40:
            return "cotton"
        if texture < 60:
            return "denim"
        return "textured"

    def get_low_confidence_attributes(self) -> list[str]:
        """Return attribute keys where confidence is below the threshold."""
        return [k for k, v in self._confidence_scores.items() if v < settings.BLIP2_CONFIDENCE_THRESHOLD]


blip2_extractor = BLIP2Extractor()
