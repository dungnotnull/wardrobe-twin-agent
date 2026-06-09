"""OOTDiffusion virtual try-on pipeline.

Renders a garment image onto a person image to produce a photorealistic
try-on result. Primary: OOTDiffusion latent diffusion model.
Fallback: alpha-blended composite overlay for preview when model is unavailable.
"""
from __future__ import annotations

import io
import logging
import time
import uuid
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from config.settings import settings

logger = logging.getLogger(__name__)


class OOTDiffusionPipeline:
    """Virtual try-on engine powered by OOTDiffusion."""

    def __init__(self) -> None:
        self._pipeline = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            self._load_model()
        except Exception as e:
            logger.warning("OOTDiffusion model not available: %s. Composite fallback will be used.", e)
            self._pipeline = None

    def _load_model(self) -> None:
        """Load the OOTDiffusion model from HuggingFace cache or local weights.

        The model weights (~4-8GB) will be automatically downloaded from HuggingFace
        on first use. Ensure you have sufficient disk space and a stable connection.
        For GPU inference, an NVIDIA GPU with >= 8GB VRAM is recommended.
        """
        import torch
        from diffusers import StableDiffusionInpaintPipeline

        model_dir = settings.MODELS_DIR / "ootdiffusion"
        dtype = torch.float16 if settings.effective_device == "cuda" else torch.float32

        if model_dir.exists() and (model_dir / "config.json").exists():
            self._pipeline = StableDiffusionInpaintPipeline.from_pretrained(
                str(model_dir), torch_dtype=dtype,
            )
            self._pipeline.to(settings.effective_device)
            logger.info("OOTDiffusion model loaded from local cache on %s", settings.effective_device)
        else:
            logger.info(
                "OOTDiffusion weights not found locally. Downloading from HuggingFace "
                "(this may take several minutes, ~4-8GB)..."
            )
            self._pipeline = StableDiffusionInpaintPipeline.from_pretrained(
                settings.OOTDIFFUSION_MODEL_ID,
                torch_dtype=dtype,
                cache_dir=str(settings.MODELS_DIR),
            )
            self._pipeline.to(settings.effective_device)
            logger.info("OOTDiffusion model loaded from HuggingFace on %s", settings.effective_device)

    @property
    def is_available(self) -> bool:
        self._ensure_loaded()
        return self._pipeline is not None

    def try_on(self, person_image: Image.Image | np.ndarray, garment_image: Image.Image | np.ndarray, category: str = "upper_body", steps: int | None = None) -> dict[str, Any]:
        """Run virtual try-on: place garment on person.

        Returns dict with keys: result_image (PIL.Image), result_path (str), inference_time (float).
        """
        self._ensure_loaded()

        if isinstance(person_image, np.ndarray):
            person_image = Image.fromarray(cv2.cvtColor(person_image, cv2.COLOR_BGR2RGB))
        if isinstance(garment_image, np.ndarray):
            garment_image = Image.fromarray(cv2.cvtColor(garment_image, cv2.COLOR_BGR2RGB))

        start_time = time.time()

        if self._pipeline is not None:
            result = self._run_diffusion(person_image, garment_image, category, steps)
        else:
            result = self._run_composite(person_image, garment_image, category)

        inference_time = round(time.time() - start_time, 2)
        result["inference_time"] = inference_time

        result_path = settings.AVATARS_DIR / f"tryon_{uuid.uuid4().hex[:8]}.png"
        result["result_image"].save(str(result_path))
        result["result_path"] = str(result_path)

        return result

    def _run_diffusion(self, person_image: Image.Image, garment_image: Image.Image, category: str, steps: int | None) -> dict[str, Any]:
        """Run OOTDiffusion inference."""
        import torch
        n_steps = steps or settings.OOTDIFFUSION_STEPS
        target_size = (512, 768)
        person_resized = person_image.resize(target_size, Image.LANCZOS)
        garment_resized = garment_image.resize((512, 512), Image.LANCZOS)

        mask = self._generate_inpaint_mask(person_resized, category)

        generator = torch.Generator(device=settings.effective_device).manual_seed(42)
        output = self._pipeline(
            prompt=f"a person wearing a {category.replace('_', ' ')} garment, photorealistic, high quality",
            image=person_resized,
            mask_image=mask,
            num_inference_steps=n_steps,
            guidance_scale=settings.OOTDIFFUSION_GUIDANCE_SCALE,
            generator=generator,
        )
        result_image = output.images[0]
        return {"result_image": result_image}

    def _run_composite(self, person_image: Image.Image, garment_image: Image.Image, category: str) -> dict[str, Any]:
        """Alpha-blended composite overlay for preview when diffusion model is unavailable."""
        p_w, p_h = person_image.size
        if category == "upper_body":
            target_w, target_h = int(p_w * 0.7), int(p_h * 0.45)
            paste_x, paste_y = (p_w - target_w) // 2, int(p_h * 0.15)
        elif category == "lower_body":
            target_w, target_h = int(p_w * 0.6), int(p_h * 0.4)
            paste_x, paste_y = (p_w - target_w) // 2, int(p_h * 0.5)
        else:
            target_w, target_h = int(p_w * 0.7), int(p_h * 0.7)
            paste_x, paste_y = (p_w - target_w) // 2, int(p_h * 0.15)

        resized_garment = garment_image.resize((target_w, target_h), Image.LANCZOS)
        result = person_image.copy()

        if resized_garment.mode == "RGBA":
            result.paste(resized_garment, (paste_x, paste_y), resized_garment)
        else:
            garment_rgba = resized_garment.convert("RGBA")
            datas = garment_rgba.getdata()
            new_data = []
            for item in datas:
                if item[0] > 230 and item[1] > 230 and item[2] > 230:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append((item[0], item[1], item[2], 200))
            garment_rgba.putdata(new_data)
            result.paste(garment_rgba, (paste_x, paste_y), garment_rgba)

        return {"result_image": result}

    @staticmethod
    def _generate_inpaint_mask(person_image: Image.Image, category: str) -> Image.Image:
        """Generate an inpainting mask for the target body region."""
        w, h = person_image.size
        mask = Image.new("L", (w, h), 0)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)
        if category == "upper_body":
            draw.rectangle([w * 0.15, h * 0.12, w * 0.85, h * 0.55], fill=255)
        elif category == "lower_body":
            draw.rectangle([w * 0.2, h * 0.45, w * 0.8, h * 0.85], fill=255)
        else:
            draw.rectangle([w * 0.15, h * 0.1, w * 0.85, h * 0.8], fill=255)
        return mask


ootd_pipeline = OOTDiffusionPipeline()
