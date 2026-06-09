"""Image preprocessing and model caching utilities."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from config.settings import settings

logger = logging.getLogger(__name__)

# Model cache: keep loaded models in memory between calls
_model_cache: dict[str, Any] = {}


def get_cached_model(key: str, loader_fn) -> Any:
    if key not in _model_cache:
        logger.info("Loading model: %s", key)
        _model_cache[key] = loader_fn()
    return _model_cache[key]


def clear_model_cache() -> None:
    _model_cache.clear()


def preprocess_image_for_inference(
    image: Image.Image | np.ndarray,
    target_size: tuple[int, int] = (512, 512),
    normalize: bool = True,
) -> np.ndarray:
    if isinstance(image, Image.Image):
        image = np.array(image.convert("RGB"))

    image = cv2.resize(image, target_size, interpolation=cv2.INTER_LANCZOS4)

    if normalize:
        image = image.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        image = (image - mean) / std

    return image


def compute_cache_key(*args: bytes | str) -> str:
    hasher = hashlib.sha256()
    for arg in args:
        if isinstance(arg, str):
            hasher.update(arg.encode("utf-8"))
        else:
            hasher.update(arg)
    return hasher.hexdigest()


def get_cached_result(cache_key: str) -> bytes | None:
    from backend.db.database import db
    return db.get_cached_result(cache_key)


def set_cached_result(cache_key: str, data: bytes) -> None:
    from backend.db.database import db
    db.set_cached_result(cache_key, data)


def purge_cache() -> int:
    from backend.db.database import db
    return db.purge_expired_cache(settings.RESULT_CACHE_MAX_AGE_HOURS)
